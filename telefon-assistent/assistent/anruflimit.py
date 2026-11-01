"""Mengenlimit für eingehende KI-Gespräche (PC- und Handy-Version).

Höchstens `pro_nummer_tag` Gespräche je Anrufernummer in 24 Stunden und höchstens
`pro_stunde` Gespräche insgesamt in einer Stunde. Ein Wert von 0 schaltet die jeweilige
Grenze ab. Abgelehnte Anrufe zählen nicht mit.
"""

import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass

STUNDE = 3600.0
TAG = 24 * STUNDE
_UNTERDRUECKT = "unterdrückt"


@dataclass(frozen=True)
class Entscheidung:
    erlaubt: bool
    meldung: str = ""  # Text für Telegram; leer, wenn nichts (mehr) zu melden ist


class Anruflimit:
    def __init__(self, pro_nummer_tag: int, pro_stunde: int, uhr: Callable[[], float] = time.monotonic):
        if pro_nummer_tag < 0 or pro_stunde < 0:
            raise ValueError("Die Grenzen für eingehende Anrufe dürfen nicht negativ sein.")
        self.pro_nummer_tag = pro_nummer_tag
        self.pro_stunde = pro_stunde
        self._uhr = uhr
        self._alle: deque[float] = deque()  # Zeitpunkte aller angenommenen Gespräche (1 Stunde)
        self._je_nummer: dict[str, deque[float]] = {}  # ... je Nummer (24 Stunden)
        self._gemeldet: dict[str, float] = {}  # letzte Telegram-Meldung je Grund

    def _aufraeumen(self, jetzt: float) -> None:
        while self._alle and jetzt - self._alle[0] >= STUNDE:
            self._alle.popleft()
        for nummer in list(self._je_nummer):
            zeiten = self._je_nummer[nummer]
            while zeiten and jetzt - zeiten[0] >= TAG:
                zeiten.popleft()
            if not zeiten:
                del self._je_nummer[nummer]
        self._gemeldet = {grund: zeit for grund, zeit in self._gemeldet.items() if jetzt - zeit < STUNDE}

    def _ablehnen(self, grund: str, text: str, jetzt: float) -> Entscheidung:
        if grund in self._gemeldet:
            return Entscheidung(False)
        self._gemeldet[grund] = jetzt
        return Entscheidung(False, text)

    def pruefen(self, nummer: str) -> Entscheidung:
        """Entscheidet über einen neuen Anruf und zählt ihn mit, wenn er angenommen wird."""
        jetzt = self._uhr()
        self._aufraeumen(jetzt)
        schluessel = nummer.strip() or _UNTERDRUECKT
        zeiten = self._je_nummer.get(schluessel, deque())
        if self.pro_nummer_tag and len(zeiten) >= self.pro_nummer_tag:
            return self._ablehnen(
                f"nummer:{schluessel}",
                f"🚫 Anruf von {schluessel} nicht angenommen: Diese Nummer hat in den letzten 24 Stunden schon "
                f"{len(zeiten)}× mit dem Assistenten gesprochen (Grenze: {self.pro_nummer_tag} pro Tag).",
                jetzt,
            )
        if self.pro_stunde and len(self._alle) >= self.pro_stunde:
            return self._ablehnen(
                "stunde",
                f"🚫 Anruf von {schluessel} nicht angenommen: In der letzten Stunde gab es schon "
                f"{len(self._alle)} Gespräche (Grenze: {self.pro_stunde} pro Stunde).",
                jetzt,
            )
        self._alle.append(jetzt)
        self._je_nummer[schluessel] = deque([*zeiten, jetzt])
        return Entscheidung(True)
