package com.bmwhuinfo.data

/**
 * Sicherheitsschicht: beschraenkt Befehle auf Nur-Lesen.
 *
 * Spiegelt die Logik der Windows-Software. Nur Programme aus der
 * Positivliste duerfen ausgefuehrt werden; Umleitungen, Verkettungen und
 * schreibende Optionen werden abgewiesen.
 */
object Safety {

    private val ERLAUBTE_PROGRAMME = setOf(
        "cat", "head", "tail", "ls", "stat", "file", "wc",
        "grep", "egrep", "fgrep", "cut", "awk", "sort", "uniq", "tr",
        "uname", "hostname", "uptime", "date", "id", "whoami",
        "df", "free", "mount", "lsblk", "lscpu", "lsusb", "lsmod",
        "ip", "ifconfig", "route", "netstat", "ss",
        "dmesg", "journalctl", "ps", "top", "env", "printenv",
        "echo", "find", "readlink", "basename", "dirname", "md5sum", "sha256sum",
    )

    private val VERBOTENE_TOKEN = listOf(">", ">>", "<", "&", ";", "`", "\$(", "\${")

    private val VERBOTENE_OPTIONEN_JE_PROGRAMM = mapOf(
        "sed" to listOf("-i", "--in-place"),
        "find" to listOf("-exec", "-execdir", "-delete", "-fprint", "-fprintf", "-ok", "-okdir"),
        "awk" to listOf("-i", "--in-place"),
    )

    private val GLOBAL_VERBOTENE_FRAGMENTE = listOf("system(", "print >", ">>")

    class UnsichererBefehlException(meldung: String) : IllegalArgumentException(meldung)

    fun istLesebefehl(befehl: String): Boolean = try {
        pruefeBefehl(befehl)
        true
    } catch (_: UnsichererBefehlException) {
        false
    }

    /** Prueft einen Befehl und gibt ihn unveraendert zurueck. */
    fun pruefeBefehl(befehl: String): String {
        if (befehl.isBlank()) {
            throw UnsichererBefehlException("Kein Befehl angegeben.")
        }
        if (befehl.contains("<") || befehl.contains(">")) {
            throw UnsichererBefehlException(
                "Platzhalter oder Umleitung gefunden. Bitte <...> durch einen " +
                    "echten Pfad ersetzen; Umleitungen sind nicht erlaubt.",
            )
        }
        for (token in VERBOTENE_TOKEN) {
            if (befehl.contains(token)) {
                throw UnsichererBefehlException("Operator '$token' ist nicht erlaubt (Nur-Lesen).")
            }
        }
        for (segment in befehl.split("|")) {
            pruefeSegment(segment.trim())
        }
        return befehl
    }

    private fun pruefeSegment(segment: String) {
        val teile = segment.split(Regex("\\s+")).filter { it.isNotEmpty() }
        if (teile.isEmpty()) {
            throw UnsichererBefehlException("Leerer Befehl.")
        }
        val programm = teile.first().substringAfterLast("/")
        if (programm !in ERLAUBTE_PROGRAMME) {
            throw UnsichererBefehlException(
                "Programm '$programm' ist nicht in der Lese-Positivliste.",
            )
        }
        for (fragment in GLOBAL_VERBOTENE_FRAGMENTE) {
            if (segment.contains(fragment)) {
                throw UnsichererBefehlException("'$fragment' ist nicht erlaubt (koennte schreiben).")
            }
        }
        val argumente = teile.drop(1)
        VERBOTENE_OPTIONEN_JE_PROGRAMM[programm]?.forEach { option ->
            if (option in argumente) {
                throw UnsichererBefehlException(
                    "Option '$option' ist bei '$programm' nicht erlaubt (koennte schreiben).",
                )
            }
        }
    }
}
