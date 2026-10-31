package com.bmwhuinfo.ssh

import com.bmwhuinfo.data.Safety
import com.jcraft.jsch.ChannelExec
import com.jcraft.jsch.JSch
import com.jcraft.jsch.JSchException
import com.jcraft.jsch.Session
import java.io.ByteArrayOutputStream

/** Zugangsdaten fuer die Headunit. */
data class Verbindungsdaten(
    val host: String,
    val port: Int = 22,
    val benutzer: String = "root",
    val passwort: String? = null,
    val privaterSchluessel: String? = null,
    val zeitlimitMs: Int = 10_000,
)

/** Ergebnis eines ausgefuehrten Befehls. */
data class BefehlsErgebnis(
    val command: String,
    val ausgabe: String,
    val fehlerausgabe: String,
    val exitCode: Int,
) {
    val erfolgreich: Boolean get() = exitCode == 0
}

class SSHVerbindungException(meldung: String, ursache: Throwable? = null) :
    RuntimeException(meldung, ursache)

/** Duenner, lesender SSH-Client fuer BMW-Headunits. */
class HeadunitClient(private val daten: Verbindungsdaten) : AutoCloseable {

    private var session: Session? = null

    fun verbinden() {
        val jsch = JSch()
        daten.privaterSchluessel?.let { schluessel ->
            jsch.addIdentity(
                "headunit",
                schluessel.toByteArray(),
                null,
                daten.passwort?.toByteArray(),
            )
        }
        try {
            val sitzung = jsch.getSession(daten.benutzer, daten.host, daten.port)
            if (daten.privaterSchluessel == null && daten.passwort != null) {
                sitzung.setPassword(daten.passwort)
            }
            sitzung.setConfig("StrictHostKeyChecking", "no")
            sitzung.connect(daten.zeitlimitMs)
            session = sitzung
        } catch (fehler: JSchException) {
            throw SSHVerbindungException(
                "Verbindung zu ${daten.host}:${daten.port} fehlgeschlagen: ${fehler.message}",
                fehler,
            )
        }
    }

    /** Fuehrt einen Lesebefehl aus. Schreibbefehle werden abgelehnt. */
    fun ausfuehren(befehl: String): BefehlsErgebnis {
        val sitzung = session ?: throw SSHVerbindungException("Nicht verbunden. Zuerst verbinden().")
        val geprueft = Safety.pruefeBefehl(befehl)
        val kanal = sitzung.openChannel("exec") as ChannelExec
        val ausgabe = ByteArrayOutputStream()
        val fehler = ByteArrayOutputStream()
        return try {
            kanal.setCommand(geprueft)
            kanal.setErrStream(fehler)
            val eingang = kanal.inputStream
            kanal.connect(daten.zeitlimitMs)
            eingang.copyTo(ausgabe)
            while (!kanal.isClosed) {
                Thread.sleep(20)
            }
            BefehlsErgebnis(
                command = geprueft,
                ausgabe = ausgabe.toString("UTF-8"),
                fehlerausgabe = fehler.toString("UTF-8"),
                exitCode = kanal.exitStatus,
            )
        } catch (fehlerJsch: JSchException) {
            throw SSHVerbindungException("Befehl fehlgeschlagen: ${fehlerJsch.message}", fehlerJsch)
        } finally {
            kanal.disconnect()
        }
    }

    override fun close() {
        session?.disconnect()
        session = null
    }
}
