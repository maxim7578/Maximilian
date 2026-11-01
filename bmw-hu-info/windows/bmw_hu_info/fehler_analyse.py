"""Auswertung von Fehlerspeicher-/Log-Ausgaben.

Fasst rohe Ausgaben von dmesg/journalctl zusammen: zaehlt Fehler und
Warnungen und findet die haeufigsten (normalisierten) Meldungen. Rein
lesende Analyse, veraendert nichts.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass

SCHLUESSEL_FEHLER = ("error", "fail", "fatal", "panic", "segfault", "exception", "critical")
SCHLUESSEL_WARN = ("warn", "warning", "deprecat")

# Zeitstempel/Praefixe und Zahlen, die gleiche Meldungen unterscheiden.
_ZEITSTEMPEL = re.compile(r"^\s*\[\s*\d+\.\d+\]\s*")
_SYSLOG_PRAEFIX = re.compile(
    r"^[A-Z][a-z]{2}\s+\d+\s+\d{2}:\d{2}:\d{2}\s+\S+\s+"
)
_ZAHLEN = re.compile(r"\d+")


@dataclass(frozen=True)
class FehlerBericht:
    """Zusammenfassung einer Log-Auswertung."""

    gesamt_zeilen: int
    fehler: int
    warnungen: int
    haeufigste: tuple[tuple[str, int], ...]

    def als_text(self) -> str:
        zeilen = [
            "Fehlerspeicher-Auswertung:",
            f"  Zeilen gesamt: {self.gesamt_zeilen}",
            f"  Fehler:        {self.fehler}",
            f"  Warnungen:     {self.warnungen}",
        ]
        if self.haeufigste:
            zeilen.append("  Haeufigste Meldungen:")
            for meldung, anzahl in self.haeufigste:
                zeilen.append(f"    {anzahl}x  {meldung}")
        return "\n".join(zeilen)


def _normalisiere(zeile: str) -> str:
    ohne = _ZEITSTEMPEL.sub("", zeile)
    ohne = _SYSLOG_PRAEFIX.sub("", ohne)
    ohne = _ZAHLEN.sub("#", ohne)
    return ohne.strip()


def _enthaelt(zeile: str, schluessel: tuple[str, ...]) -> bool:
    klein = zeile.lower()
    return any(wort in klein for wort in schluessel)


def analysiere(text: str, top: int = 5) -> FehlerBericht:
    """Wertet Log-Text aus und liefert eine Zusammenfassung."""
    zeilen = [z for z in text.splitlines() if z.strip()]
    fehler_zeilen = [z for z in zeilen if _enthaelt(z, SCHLUESSEL_FEHLER)]
    warn_zeilen = [z for z in zeilen if _enthaelt(z, SCHLUESSEL_WARN)]

    zaehler: Counter[str] = Counter(
        _normalisiere(z) for z in fehler_zeilen + warn_zeilen
    )
    haeufigste = tuple(zaehler.most_common(top))

    return FehlerBericht(
        gesamt_zeilen=len(zeilen),
        fehler=len(fehler_zeilen),
        warnungen=len(warn_zeilen),
        haeufigste=haeufigste,
    )
