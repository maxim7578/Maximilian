"""SSH-Verbindung zur Headunit. Fuehrt nur gepruefte Lesebefehle aus."""

from __future__ import annotations

from dataclasses import dataclass

import paramiko

from .safety import pruefe_befehl


@dataclass(frozen=True)
class Verbindungsdaten:
    """Zugangsdaten fuer die Headunit."""

    host: str
    port: int = 22
    benutzer: str = "root"
    passwort: str | None = None
    schluesseldatei: str | None = None
    zeitlimit: float = 10.0


@dataclass(frozen=True)
class BefehlsErgebnis:
    """Ergebnis eines ausgefuehrten Befehls."""

    command: str
    ausgabe: str
    fehlerausgabe: str
    exit_code: int

    @property
    def erfolgreich(self) -> bool:
        return self.exit_code == 0


class SSHVerbindungsError(RuntimeError):
    """Fehler beim Aufbau oder Betrieb der SSH-Verbindung."""


class HeadunitClient:
    """Duenner, lesender SSH-Client fuer BMW-Headunits."""

    def __init__(self, daten: Verbindungsdaten) -> None:
        self._daten = daten
        self._client: paramiko.SSHClient | None = None

    def verbinden(self) -> None:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            client.connect(
                hostname=self._daten.host,
                port=self._daten.port,
                username=self._daten.benutzer,
                password=self._daten.passwort,
                key_filename=self._daten.schluesseldatei,
                timeout=self._daten.zeitlimit,
                allow_agent=False,
                look_for_keys=self._daten.schluesseldatei is not None,
            )
        except paramiko.AuthenticationException as fehler:
            raise SSHVerbindungsError(
                "Anmeldung fehlgeschlagen: Benutzer, Passwort oder "
                "Schluessel pruefen."
            ) from fehler
        except (paramiko.SSHException, OSError) as fehler:
            raise SSHVerbindungsError(
                f"Verbindung zu {self._daten.host}:{self._daten.port} "
                f"fehlgeschlagen: {fehler}"
            ) from fehler
        self._client = client

    def ausfuehren(self, befehl: str) -> BefehlsErgebnis:
        """Fuehrt einen Lesebefehl aus. Schreibbefehle werden abgelehnt."""
        if self._client is None:
            raise SSHVerbindungsError("Nicht verbunden. Zuerst verbinden().")
        geprueft = pruefe_befehl(befehl)
        try:
            _, stdout, stderr = self._client.exec_command(
                geprueft, timeout=self._daten.zeitlimit
            )
            ausgabe = stdout.read().decode("utf-8", errors="replace")
            fehler = stderr.read().decode("utf-8", errors="replace")
            code = stdout.channel.recv_exit_status()
        except paramiko.SSHException as ausnahme:
            raise SSHVerbindungsError(
                f"Befehl konnte nicht ausgefuehrt werden: {ausnahme}"
            ) from ausnahme
        return BefehlsErgebnis(geprueft, ausgabe, fehler, code)

    def schliessen(self) -> None:
        if self._client is not None:
            self._client.close()
            self._client = None

    def __enter__(self) -> "HeadunitClient":
        self.verbinden()
        return self

    def __exit__(self, *_: object) -> None:
        self.schliessen()
