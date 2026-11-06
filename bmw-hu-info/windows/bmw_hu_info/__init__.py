"""BMW HU Info - lesender Diagnose-Client fuer BMW-Headunits."""

from .catalog import Befehl, Katalog, Kategorie, lade_katalog
from .safety import UnsichererBefehlError, ist_lesebefehl, pruefe_befehl
from .ssh_client import (
    BefehlsErgebnis,
    HeadunitClient,
    SSHVerbindungsError,
    Verbindungsdaten,
)

__all__ = [
    "Befehl",
    "Katalog",
    "Kategorie",
    "lade_katalog",
    "UnsichererBefehlError",
    "ist_lesebefehl",
    "pruefe_befehl",
    "BefehlsErgebnis",
    "HeadunitClient",
    "SSHVerbindungsError",
    "Verbindungsdaten",
]

__version__ = "0.1.0"
