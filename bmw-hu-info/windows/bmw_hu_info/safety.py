"""Sicherheitsschicht: beschraenkt ausfuehrbare Befehle auf Nur-Lesen.

Der Diagnose-Client darf am Fahrzeug nichts veraendern. Diese Schicht
prueft jeden Befehl, bevor er ueber SSH gesendet wird, und laesst nur
eine feste Liste lesender Programme zu. Schreib-, Umleitungs- und
Kettungsoperatoren werden abgewiesen.
"""

from __future__ import annotations

# Nur diese Programme sind erlaubt. Alle lesen ausschliesslich.
ERLAUBTE_PROGRAMME = frozenset(
    {
        "cat", "head", "tail", "ls", "stat", "file", "wc",
        "grep", "egrep", "fgrep", "cut", "awk", "sort", "uniq", "tr",
        "uname", "hostname", "uptime", "date", "id", "whoami",
        "df", "free", "mount", "lsblk", "lscpu", "lsusb", "lsmod",
        "ip", "ifconfig", "route", "netstat", "ss",
        "dmesg", "journalctl", "ps", "top", "env", "printenv",
        "echo", "find", "readlink", "basename", "dirname", "md5sum", "sha256sum",
    }
)

# Operatorzeichen, die ausserhalb von Anfuehrungszeichen verboten sind
# (Umleitung, Verkettung, Subshell). Nur die Pipe '|' ist als Trenner
# zwischen Lesebefehlen erlaubt.
VERBOTENE_OPERATORZEICHEN = (">", "<", "&", ";", "`", "(", ")")

# Gefaehrliche Optionen je Programm. Nur fuer das jeweilige Programm
# verboten, damit harmlose gleichnamige Optionen (z. B. "grep -i")
# erlaubt bleiben.
VERBOTENE_OPTIONEN_JE_PROGRAMM = {
    "sed": ("-i", "--in-place"),
    "find": ("-exec", "-execdir", "-delete", "-fprint", "-fprintf", "-ok", "-okdir"),
    "awk": ("-i", "--in-place"),
}
# Token, die in keinem Programm vorkommen duerfen (Dateischreiben/Ausfuehren).
GLOBAL_VERBOTENE_FRAGMENTE = ("system(", "print >", ">>")


class UnsichererBefehlError(ValueError):
    """Wird ausgeloest, wenn ein Befehl nicht als Nur-Lesen gilt."""


def _in_segmente(befehl: str) -> list[str]:
    """Teilt den Befehl an Pipes '|' - aber nur ausserhalb von
    Anfuehrungszeichen. Verbotene Operatorzeichen ausserhalb von
    Anfuehrungszeichen loesen einen Fehler aus. So bleiben Pipes innerhalb
    von Argumenten (z. B. grep 'a|b') erhalten.
    """
    segmente: list[str] = []
    aktuell: list[str] = []
    in_single = False
    in_double = False
    i = 0
    while i < len(befehl):
        zeichen = befehl[i]
        if zeichen == "'" and not in_double:
            in_single = not in_single
            aktuell.append(zeichen)
        elif zeichen == '"' and not in_single:
            in_double = not in_double
            aktuell.append(zeichen)
        elif in_single or in_double:
            aktuell.append(zeichen)
        elif zeichen == "|":
            segmente.append("".join(aktuell))
            aktuell = []
        elif zeichen == "$" and i + 1 < len(befehl) and befehl[i + 1] in "({":
            raise UnsichererBefehlError(
                "Kommandosubstitution ($(...) / ${...}) ist nicht erlaubt."
            )
        elif zeichen in VERBOTENE_OPERATORZEICHEN:
            raise UnsichererBefehlError(
                f"Operator '{zeichen}' ist nicht erlaubt (Nur-Lesen)."
            )
        else:
            aktuell.append(zeichen)
        i += 1
    if in_single or in_double:
        raise UnsichererBefehlError("Unbalancierte Anfuehrungszeichen.")
    segmente.append("".join(aktuell))
    return segmente


def _pruefe_segment(segment: str) -> None:
    teile = segment.split()
    if not teile:
        raise UnsichererBefehlError("Leerer Befehl.")
    programm = teile[0].split("/")[-1]
    if programm not in ERLAUBTE_PROGRAMME:
        raise UnsichererBefehlError(
            f"Programm '{programm}' ist nicht in der Lese-Positivliste."
        )
    for fragment in GLOBAL_VERBOTENE_FRAGMENTE:
        if fragment in segment:
            raise UnsichererBefehlError(
                f"'{fragment}' ist nicht erlaubt (koennte schreiben)."
            )
    for option in VERBOTENE_OPTIONEN_JE_PROGRAMM.get(programm, ()):
        if option in teile[1:]:
            raise UnsichererBefehlError(
                f"Option '{option}' ist bei '{programm}' nicht erlaubt "
                "(koennte schreiben)."
            )


def ist_lesebefehl(befehl: str) -> bool:
    """True, wenn der Befehl als reiner Lesebefehl gilt."""
    try:
        pruefe_befehl(befehl)
        return True
    except UnsichererBefehlError:
        return False


def pruefe_befehl(befehl: str) -> str:
    """Prueft einen Befehl und gibt ihn unveraendert zurueck.

    Pipes (|) sind erlaubt, jedes Segment wird einzeln geprueft.
    Alle anderen Ketten-/Umleitungsoperatoren sind verboten.
    """
    if befehl is None or not befehl.strip():
        raise UnsichererBefehlError("Kein Befehl angegeben.")
    if "<" in befehl or ">" in befehl:
        # Platzhalter wie <PFAD_...> muessen vor dem Ausfuehren ersetzt
        # werden; Umleitungen sind generell verboten.
        raise UnsichererBefehlError(
            "Platzhalter oder Umleitung gefunden. Bitte <...> durch einen "
            "echten Pfad ersetzen; Umleitungen (>, <) sind nicht erlaubt."
        )
    for segment in _in_segmente(befehl):
        _pruefe_segment(segment.strip())
    return befehl
