"""Gemeinsame Datentypen für PC- und Handy-Version."""

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

try:
    ZEITZONE = ZoneInfo("Europe/Berlin")
except ZoneInfoNotFoundError:
    # Ohne Zeitzonen-Datenbank (z. B. Termux ohne Paket tzdata): Uhrzeit des Geräts nehmen
    ZEITZONE = None


def jetzt() -> datetime:
    return datetime.now(ZEITZONE).astimezone() if ZEITZONE is None else datetime.now(ZEITZONE)


@dataclass
class Anruf:
    ziel: str
    nummer: str
    auftrag: str
    spielraum: str
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    kanal_id: str = ""
    verbunden: asyncio.Event = field(default_factory=asyncio.Event)
