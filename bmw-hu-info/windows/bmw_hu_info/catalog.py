"""Laden und Validieren des gemeinsamen Befehlskatalogs."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Befehl:
    """Ein einzelner Diagnosebefehl aus dem Katalog."""

    id: str
    titel: str
    command: str
    headunits: tuple[str, ...]
    hinweis: str = ""

    @property
    def hat_platzhalter(self) -> bool:
        return "<" in self.command and ">" in self.command


@dataclass(frozen=True)
class Kategorie:
    """Eine Gruppe von Befehlen."""

    id: str
    titel: str
    befehle: tuple[Befehl, ...]


@dataclass(frozen=True)
class Katalog:
    """Der gesamte Befehlskatalog."""

    version: int
    beschreibung: str
    kategorien: tuple[Kategorie, ...]

    def fuer_headunit(self, headunit: str) -> "Katalog":
        """Neuer Katalog, gefiltert auf eine Headunit (immutabel)."""
        gefiltert = tuple(
            Kategorie(
                id=kat.id,
                titel=kat.titel,
                befehle=tuple(
                    b for b in kat.befehle if headunit in b.headunits
                ),
            )
            for kat in self.kategorien
        )
        nicht_leer = tuple(k for k in gefiltert if k.befehle)
        return Katalog(self.version, self.beschreibung, nicht_leer)


def _standardpfad() -> Path:
    return Path(__file__).resolve().parents[2] / "shared" / "commands.json"


def lade_katalog(pfad: Path | None = None) -> Katalog:
    """Laedt den Katalog aus JSON und validiert die Struktur."""
    ziel = pfad or _standardpfad()
    try:
        rohdaten = json.loads(ziel.read_text(encoding="utf-8"))
    except FileNotFoundError as fehler:
        raise FileNotFoundError(
            f"Befehlskatalog nicht gefunden: {ziel}"
        ) from fehler
    except json.JSONDecodeError as fehler:
        raise ValueError(
            f"Befehlskatalog ist kein gueltiges JSON: {fehler}"
        ) from fehler

    return _aus_dict(rohdaten)


def _aus_dict(rohdaten: dict) -> Katalog:
    try:
        kategorien = tuple(
            Kategorie(
                id=kat["id"],
                titel=kat["titel"],
                befehle=tuple(
                    Befehl(
                        id=b["id"],
                        titel=b["titel"],
                        command=b["command"],
                        headunits=tuple(b.get("headunits", ())),
                        hinweis=b.get("hinweis", ""),
                    )
                    for b in kat["befehle"]
                ),
            )
            for kat in rohdaten["kategorien"]
        )
    except (KeyError, TypeError) as fehler:
        raise ValueError(
            f"Befehlskatalog hat ein unerwartetes Format: {fehler}"
        ) from fehler

    return Katalog(
        version=int(rohdaten.get("version", 1)),
        beschreibung=rohdaten.get("beschreibung", ""),
        kategorien=kategorien,
    )
