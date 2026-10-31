"""Simulierte BMW-Headunit als kleiner SSH-Server (nur zum Testen).

Startet einen echten SSH-Server, der sich wie eine Headunit verhaelt und
auf die Diagnosebefehle Beispielantworten liefert. So laesst sich der
gesamte Weg (Verbindung, Authentifizierung, Befehlsausfuehrung) ohne
Fahrzeug testen - mit der Windows-Software oder der Android-App.

Achtung: Der Server akzeptiert jede Anmeldung (oder ein gesetztes
Passwort) und ist ausschliesslich zum Testen gedacht, nicht fuer den
Produktivbetrieb.
"""

from __future__ import annotations

import socket
import threading

import paramiko

from .mock_data import antwort_fuer
from .safety import ist_lesebefehl


class _Serverlogik(paramiko.ServerInterface):
    """Beantwortet Anmeldung und exec-Anfragen."""

    def __init__(self, passwort: str | None) -> None:
        self._passwort = passwort

    def check_channel_request(self, kind: str, chanid: int) -> int:
        if kind == "session":
            return paramiko.OPEN_SUCCEEDED
        return paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED

    def get_allowed_auths(self, username: str) -> str:
        return "password,publickey"

    def check_auth_password(self, username: str, password: str) -> int:
        if self._passwort is None or password == self._passwort:
            return paramiko.AUTH_SUCCESSFUL
        return paramiko.AUTH_FAILED

    def check_auth_publickey(self, username: str, key: paramiko.PKey) -> int:
        return paramiko.AUTH_SUCCESSFUL

    def check_channel_exec_request(self, channel, command) -> bool:
        befehl = command.decode("utf-8") if isinstance(command, bytes) else command
        threading.Thread(
            target=self._bediene, args=(channel, befehl), daemon=True
        ).start()
        return True

    def _bediene(self, channel, befehl: str) -> None:
        try:
            if not ist_lesebefehl(befehl):
                channel.sendall_stderr(
                    b"Verweigert: nur Lesebefehle erlaubt (Simulation)\n"
                )
                channel.send_exit_status(1)
                return
            stdout, code = antwort_fuer(befehl)
            if stdout:
                channel.sendall(stdout.encode("utf-8"))
            else:
                channel.sendall_stderr(
                    f"(Simulation hat fuer '{befehl}' keine Beispieldaten)\n".encode()
                )
            channel.send_exit_status(code)
        finally:
            # EOF senden, aber den Kanal nicht hart schliessen, bevor der
            # Client alle Daten gelesen hat (vermeidet "Channel closed").
            try:
                channel.shutdown_write()
            except Exception:  # noqa: BLE001 - Kanal evtl. schon zu
                pass


class MockHeadunit:
    """Startbarer Test-SSH-Server, der eine Headunit simuliert."""

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 0,
        passwort: str | None = None,
    ) -> None:
        self.host = host
        self.port = port
        self._passwort = passwort
        self._host_key = paramiko.RSAKey.generate(2048)
        self._sock: socket.socket | None = None
        self._thread: threading.Thread | None = None
        self._laeuft = False
        self._transports: list[paramiko.Transport] = []

    def start(self) -> "MockHeadunit":
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._sock.bind((self.host, self.port))
        self._sock.listen(5)
        self.port = self._sock.getsockname()[1]
        self._laeuft = True
        self._thread = threading.Thread(target=self._akzeptiere, daemon=True)
        self._thread.start()
        return self

    def _akzeptiere(self) -> None:
        while self._laeuft:
            try:
                client, _ = self._sock.accept()  # type: ignore[union-attr]
            except OSError:
                break
            transport = paramiko.Transport(client)
            transport.add_server_key(self._host_key)
            try:
                transport.start_server(server=_Serverlogik(self._passwort))
                self._transports.append(transport)
            except paramiko.SSHException:
                transport.close()

    def stop(self) -> None:
        self._laeuft = False
        if self._sock is not None:
            self._sock.close()
            self._sock = None
        for transport in self._transports:
            transport.close()
        self._transports.clear()

    def __enter__(self) -> "MockHeadunit":
        return self.start()

    def __exit__(self, *_: object) -> None:
        self.stop()
