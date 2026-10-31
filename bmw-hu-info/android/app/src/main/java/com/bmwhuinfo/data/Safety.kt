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

    private val VERBOTENE_OPERATORZEICHEN = setOf('>', '<', '&', ';', '`', '(', ')')

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
        for (segment in inSegmente(befehl)) {
            pruefeSegment(segment.trim())
        }
        return befehl
    }

    /**
     * Teilt den Befehl an Pipes '|' - aber nur ausserhalb von
     * Anfuehrungszeichen. Verbotene Operatorzeichen ausserhalb von
     * Anfuehrungszeichen loesen einen Fehler aus.
     */
    private fun inSegmente(befehl: String): List<String> {
        val segmente = mutableListOf<String>()
        val aktuell = StringBuilder()
        var inSingle = false
        var inDouble = false
        var i = 0
        while (i < befehl.length) {
            val zeichen = befehl[i]
            when {
                zeichen == '\'' && !inDouble -> { inSingle = !inSingle; aktuell.append(zeichen) }
                zeichen == '"' && !inSingle -> { inDouble = !inDouble; aktuell.append(zeichen) }
                inSingle || inDouble -> aktuell.append(zeichen)
                zeichen == '|' -> { segmente.add(aktuell.toString()); aktuell.clear() }
                zeichen == '$' && i + 1 < befehl.length && (befehl[i + 1] == '(' || befehl[i + 1] == '{') ->
                    throw UnsichererBefehlException(
                        "Kommandosubstitution (\$(...) / \${...}) ist nicht erlaubt.",
                    )
                zeichen in VERBOTENE_OPERATORZEICHEN ->
                    throw UnsichererBefehlException("Operator '$zeichen' ist nicht erlaubt (Nur-Lesen).")
                else -> aktuell.append(zeichen)
            }
            i++
        }
        if (inSingle || inDouble) {
            throw UnsichererBefehlException("Unbalancierte Anfuehrungszeichen.")
        }
        segmente.add(aktuell.toString())
        return segmente
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
