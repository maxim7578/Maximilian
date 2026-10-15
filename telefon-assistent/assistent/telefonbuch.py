"""Telefonnummern finden, prüfen und für die FRITZ!Box aufbereiten."""

import json
import re
from dataclasses import dataclass
from pathlib import Path

import httpx

# Notrufe, Sonderrufnummern und teure Nummern wählt der Assistent nie.
_GESPERRT = (
    r"^11[0-9]$",  # 110, 112, 115, 116 ...
    r"^116\d+",  # 116 116 usw.
    r"^118\d+",  # Auskunftsdienste
    r"^0?900",  # Mehrwertdienste
    r"^0?137",  # Televoting
    r"^0?138",
    r"^0?180",  # Service-Nummern
    r"^0?700",  # persönliche Rufnummern
    r"^0?1212",
    r"^0?199",  # netzinterne Dienste
    r"^00",  # Auslandsgespräche (nicht in der Flatrate)
)


class NummernFehler(Exception):
    pass


def normalisieren(nummer: str) -> str:
    """Macht aus "+49 (30) 123-456" eine wählbare Nummer wie "030123456"."""
    roh = nummer.strip()
    ziffern = re.sub(r"[^\d+]", "", roh)
    if ziffern.startswith("+49"):
        ziffern = "0" + ziffern[3:]
    elif ziffern.startswith("0049"):
        ziffern = "0" + ziffern[4:]
    elif ziffern.startswith("+"):
        ziffern = "00" + ziffern[1:]
    ziffern = ziffern.replace("+", "")
    if not ziffern.isdigit() or not 3 <= len(ziffern) <= 16:
        raise NummernFehler(f"„{nummer}“ ist keine gültige Telefonnummer.")
    return ziffern


def pruefen(nummer: str) -> str:
    """Normalisiert und lehnt gesperrte Nummern ab."""
    n = normalisieren(nummer)
    for muster in _GESPERRT:
        if re.match(muster, n):
            raise NummernFehler(
                f"Die Nummer {n} wird aus Sicherheitsgründen nicht gewählt "
                "(Notruf, Sonder-, Service- oder Auslandsnummer)."
            )
    if not n.startswith("0") and len(n) < 6:
        raise NummernFehler(f"Die Nummer {n} ist zu kurz.")
    return n


@dataclass
class Treffer:
    name: str
    nummer: str
    adresse: str
    quelle: str


class Kontakte:
    """Selbst gespeicherte Nummern in daten/kontakte.json."""

    def __init__(self, datei: Path):
        self.datei = datei

    def _laden(self) -> dict[str, str]:
        if not self.datei.exists():
            return {}
        return json.loads(self.datei.read_text(encoding="utf-8"))

    def speichern(self, name: str, nummer: str) -> str:
        n = pruefen(nummer)
        daten = self._laden()
        daten[name.strip()] = n
        self.datei.parent.mkdir(parents=True, exist_ok=True)
        self.datei.write_text(json.dumps(daten, ensure_ascii=False, indent=2), encoding="utf-8")
        return n

    def suchen(self, name: str) -> Treffer | None:
        gesucht = name.strip().lower()
        for eintrag, nummer in self._laden().items():
            if eintrag.lower() == gesucht or gesucht in eintrag.lower():
                return Treffer(eintrag, nummer, "", "deine Kontakte")
        return None


async def openstreetmap_suchen(ziel: str, ort: str) -> list[Treffer]:
    """Sucht Nummern über OpenStreetMap (Nominatim, kostenlos)."""
    anfrage = f"{ziel} {ort}".strip()
    async with httpx.AsyncClient(
        timeout=15,
        headers={"User-Agent": "telefon-assistent/0.1 (privates Projekt)"},
    ) as client:
        antwort = await client.get(
            "https://nominatim.openstreetmap.org/search",
            params={
                "q": anfrage,
                "format": "jsonv2",
                "extratags": 1,
                "limit": 5,
                "countrycodes": "de",
            },
        )
        antwort.raise_for_status()
    treffer = []
    for ort_daten in antwort.json():
        tags = ort_daten.get("extratags") or {}
        roh = tags.get("phone") or tags.get("contact:phone")
        if not roh:
            continue
        # Mehrere Nummern sind mit ";" getrennt – die erste nehmen.
        roh = roh.split(";")[0]
        try:
            nummer = pruefen(roh)
        except NummernFehler:
            continue
        treffer.append(
            Treffer(
                name=ort_daten.get("name") or ziel,
                nummer=nummer,
                adresse=ort_daten.get("display_name", ""),
                quelle="OpenStreetMap",
            )
        )
    return treffer
