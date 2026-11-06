"""Verbindungspruefung zur Headunit (ueber ENET/Ethernet).

Prueft zuerst, ob der Host auf TCP-Ebene erreichbar ist (ENET-Kabel,
IP-Einstellung), dann ob die SSH-Anmeldung klappt.
"""

from __future__ import annotations

import socket
from dataclasses import dataclass

from .ssh_client import HeadunitClient, SSHVerbindungsError, Verbindungsdaten


@dataclass(frozen=True)
class Verbindungsstatus:
    """Ergebnis einer Verbindungspruefung."""

    verbunden: bool
    erreichbar: bool
    meldung: str


def ist_erreichbar(host: str, port: int = 22, zeitlimit: float = 3.0) -> bool:
    """True, wenn eine TCP-Verbindung zu host:port moeglich ist."""
    if not host:
        return False
    try:
        with socket.create_connection((host, port), timeout=zeitlimit):
            return True
    except OSError:
        return False


def teste_verbindung(daten: Verbindungsdaten) -> Verbindungsstatus:
    """Prueft Erreichbarkeit (ENET) und SSH-Anmeldung."""
    if not ist_erreichbar(daten.host, daten.port, daten.zeitlimit):
        return Verbindungsstatus(
            verbunden=False,
            erreichbar=False,
            meldung=(
                f"{daten.host}:{daten.port} nicht erreichbar. "
                "ENET-Kabel, IP-Adresse und Netzwerkeinstellung pruefen."
            ),
        )
    try:
        with HeadunitClient(daten) as client:
            ergebnis = client.ausfuehren("hostname")
        name = ergebnis.ausgabe.strip() or daten.host
        return Verbindungsstatus(
            verbunden=True,
            erreichbar=True,
            meldung=f"Verbunden mit {name}.",
        )
    except SSHVerbindungsError as fehler:
        return Verbindungsstatus(
            verbunden=False,
            erreichbar=True,
            meldung=f"Erreichbar, aber SSH/Anmeldung fehlgeschlagen: {fehler}",
        )
