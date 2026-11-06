package com.bmwhuinfo.ui

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.bmwhuinfo.data.Befehl
import com.bmwhuinfo.data.Katalog
import com.bmwhuinfo.ssh.BefehlsErgebnis
import com.bmwhuinfo.ssh.HeadunitClient
import com.bmwhuinfo.ssh.SSHVerbindungException
import com.bmwhuinfo.ssh.Verbindungsdaten
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

data class DiagnoseZustand(
    val host: String = "169.254.199.99",
    val port: String = "22",
    val benutzer: String = "root",
    val passwort: String = "",
    val privaterSchluessel: String = "",
    val headunit: String = "NBTEVO",
    val laeuft: Boolean = false,
    val ausgabe: String = "",
    val verbunden: Boolean = false,
    val status: String = "Nicht verbunden",
) {
    companion object {
        val HEADUNITS = listOf("NBT", "NBTEVO", "ENAVEVO", "MGU")
    }
}

class DiagnoseViewModel(app: Application) : AndroidViewModel(app) {

    private val vollerKatalog: Katalog = Katalog.ausAssets(app)
    private val _zustand = MutableStateFlow(DiagnoseZustand())
    val zustand: StateFlow<DiagnoseZustand> = _zustand.asStateFlow()

    val katalog: Katalog
        get() = vollerKatalog.fuerHeadunit(_zustand.value.headunit)

    fun setHost(wert: String) = _zustand.update { it.copy(host = wert) }
    fun setPort(wert: String) = _zustand.update { it.copy(port = wert) }
    fun setBenutzer(wert: String) = _zustand.update { it.copy(benutzer = wert) }
    fun setPasswort(wert: String) = _zustand.update { it.copy(passwort = wert) }
    fun setSchluessel(wert: String) = _zustand.update { it.copy(privaterSchluessel = wert) }
    fun setHeadunit(wert: String) = _zustand.update { it.copy(headunit = wert) }
    fun ausgabeLeeren() = _zustand.update { it.copy(ausgabe = "") }

    fun testeVerbindung() {
        val z = _zustand.value
        if (z.host.isBlank() || z.laeuft) return
        val daten = verbindungsdaten(z)
        viewModelScope.launch {
            _zustand.update { it.copy(laeuft = true, status = "Verbinde ...") }
            val (ok, meldung) = withContext(Dispatchers.IO) { pruefe(daten) }
            _zustand.update {
                it.copy(laeuft = false, verbunden = ok, status = meldung)
            }
        }
    }

    private fun pruefe(daten: Verbindungsdaten): Pair<Boolean, String> {
        try {
            java.net.Socket().use { sock ->
                sock.connect(
                    java.net.InetSocketAddress(daten.host, daten.port),
                    daten.zeitlimitMs,
                )
            }
        } catch (_: Exception) {
            return false to
                "${daten.host}:${daten.port} nicht erreichbar (ENET-Kabel/IP pruefen)."
        }
        return try {
            HeadunitClient(daten).use { client ->
                client.verbinden()
                val name = client.ausfuehren("hostname").ausgabe.trim()
                true to "Verbunden mit ${name.ifEmpty { daten.host }}."
            }
        } catch (fehler: SSHVerbindungException) {
            false to "Erreichbar, aber SSH/Anmeldung fehlgeschlagen: ${fehler.message}"
        }
    }

    private fun verbindungsdaten(z: DiagnoseZustand) = Verbindungsdaten(
        host = z.host.trim(),
        port = z.port.toIntOrNull() ?: 22,
        benutzer = z.benutzer.ifBlank { "root" },
        passwort = z.passwort.ifBlank { null },
        privaterSchluessel = z.privaterSchluessel.ifBlank { null },
    )

    fun fuehreAus(befehle: List<Befehl>) {
        val z = _zustand.value
        if (z.host.isBlank() || z.laeuft) return
        val daten = verbindungsdaten(z)
        viewModelScope.launch {
            _zustand.update { it.copy(laeuft = true) }
            val (text, ok) = withContext(Dispatchers.IO) { arbeit(daten, befehle) }
            _zustand.update {
                it.copy(
                    laeuft = false,
                    ausgabe = it.ausgabe + text,
                    verbunden = ok,
                    status = if (ok) "Verbunden mit ${daten.host}." else "Nicht verbunden",
                )
            }
        }
    }

    private fun arbeit(
        daten: Verbindungsdaten,
        befehle: List<Befehl>,
    ): Pair<String, Boolean> {
        val puffer = StringBuilder()
        var ok = false
        try {
            HeadunitClient(daten).use { client ->
                client.verbinden()
                ok = true
                puffer.appendLine("\n>>> Verbunden mit ${daten.host}\n")
                for (befehl in befehle) {
                    if (befehl.hatPlatzhalter) {
                        puffer.appendLine("# ${befehl.titel}: uebersprungen (Platzhalter)")
                        continue
                    }
                    puffer.appendLine("# ${befehl.titel}  ($ ${befehl.command})")
                    val ergebnis: BefehlsErgebnis = client.ausfuehren(befehl.command)
                    puffer.appendLine(ergebnis.ausgabe.trimEnd().ifEmpty { "(keine Ausgabe)" })
                    if (ergebnis.fehlerausgabe.isNotBlank()) {
                        puffer.appendLine("[stderr] ${ergebnis.fehlerausgabe.trimEnd()}")
                    }
                }
            }
        } catch (fehler: SSHVerbindungException) {
            puffer.appendLine("[FEHLER] ${fehler.message}")
        } catch (fehler: Exception) {
            puffer.appendLine("[UNERWARTETER FEHLER] ${fehler.message}")
        }
        return puffer.toString() to ok
    }
}
