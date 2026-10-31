"""Live-Daten über den BMW-CarData-Datenstrom (MQTT).

Das Auto schickt Nachrichten, sobald sich etwas ändert; das zählt nicht gegen das
Tageslimit der REST-API. Anmeldung: GCID als Benutzername, id_token als Passwort,
Topic "<gcid>/+" für alle Fahrzeuge des Kontos. BMW erlaubt pro Konto nur eine
Stream-Verbindung gleichzeitig.
"""

from __future__ import annotations

import json
import ssl
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import httpx

from .auth import Tokens
from .config import STREAMING_SCOPE, ConfigError, validate_vin
from .descriptors import STATUS_FIELDS
from .report import format_value, printable

STREAM_HOST = "customer.streaming-cardata.bmwgroup.com"
STREAM_PORT = 9000
KEEPALIVE_SECONDS = 30
LOOP_TIMEOUT_SECONDS = 1.0
REFRESH_MARGIN_SECONDS = 300.0  # Zugang so lange vor dem Ablauf erneuern
RECONNECT_DELAYS = (5, 10, 30, 60)
# BMW hält eine alte Sitzung kurz fest: nach neuen Zugangsdaten und nach einer Ablehnung
# kurz warten (wie die Home-Assistant-Integration), erst die dritte Ablehnung in Folge ist endgültig.
CREDENTIAL_PAUSE_SECONDS = 2.0
REFUSAL_PAUSE_SECONDS = 3.0
MAX_REFUSALS = 3
STABLE_SECONDS = 60.0  # so lange verbunden (oder eine Nachricht erhalten) gilt als stabil
MAX_SHORT_DROPS = 3  # so oft kurz nach dem Aufbau getrennt: vermutlich eine zweite Verbindung
_TRANSIENT_RENEWAL = (httpx.HTTPError, OSError)
_AUTH_REFUSALS = frozenset({"Bad user name or password", "Not authorized"})
_LABELS = {descriptor: field.label for field in STATUS_FIELDS for descriptor in field.descriptors}

DataHandler = Callable[[str, dict[str, dict[str, Any]]], None]


class StreamError(Exception):
    """Der Datenstrom ist mit den vorhandenen Zugangsdaten nicht erreichbar."""


@dataclass(frozen=True)
class Credentials:
    gcid: str
    id_token: str
    expires_at: float


def topic_for(gcid: str) -> str:
    return f"{gcid}/+"


def stream_credentials(tokens: Tokens) -> Credentials:
    granted = tokens.scope.split()
    if not tokens.gcid or not tokens.id_token or (granted and STREAMING_SCOPE not in granted):
        raise StreamError(
            "Für Live-Daten bitte neu anmelden ('bmw-cardata anmelden'), damit BMW die Berechtigung "
            f"{STREAMING_SCOPE} erteilt. Vorher im Portal 'Zugriff auf CarData Stream' anfordern."
        )
    return Credentials(tokens.gcid, tokens.id_token, tokens.expires_at)


def parse_message(payload: bytes) -> tuple[str, dict[str, dict[str, Any]]] | None:
    """Liest eine Nachricht {"vin": ..., "data": {Datenpunkt: {...}}}; alles andere wird ignoriert."""
    try:
        raw = json.loads(payload.decode("utf-8"))
        vin, data = raw["vin"], raw["data"]
        if not isinstance(vin, str) or not isinstance(data, dict):
            return None
        return validate_vin(vin), {k: v for k, v in data.items() if isinstance(v, dict)}
    except (ValueError, KeyError, TypeError, ConfigError):
        return None


def message_lines(data: dict[str, dict[str, Any]], received: datetime) -> list[str]:
    """Eine Zeile pro Datenpunkt mit Wert; bekannte Datenpunkte mit deutschem Namen."""
    stamp = received.strftime("%H:%M:%S")
    lines = []
    for descriptor, entry in data.items():
        shown = format_value(entry)
        if shown is not None:
            lines.append(f"{stamp}  {printable(_LABELS.get(descriptor, descriptor))}: {shown}")
    return lines


def tls_context() -> ssl.SSLContext:
    """Zertifikat und Rechnername werden geprüft. BMWs Server verlangt TLS 1.3."""
    context = ssl.create_default_context()
    context.minimum_version = ssl.TLSVersion.TLSv1_3
    return context


def create_client(gcid: str) -> Any:
    import paho.mqtt.client as mqtt

    client = mqtt.Client(
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        client_id=gcid,
        protocol=mqtt.MQTTv311,
    )
    client.tls_set_context(tls_context())
    return client


class _Connection:
    """Zustand einer Verbindung, gesetzt von den paho-Rückrufen."""

    def __init__(
        self, topic: str, handle: DataHandler, notify: Callable[[str], None], clock: Callable[[], float]
    ) -> None:
        self.topic, self.handle, self.notify, self.clock = topic, handle, notify, clock
        self.connected = False
        self.connected_at = 0.0
        self.got_message = False
        self.refused: str | None = None
        self.subscribe_refused = False
        self.short_drops = 0

    def stable(self) -> bool:
        return self.connected and (self.got_message or self.clock() - self.connected_at >= STABLE_SECONDS)

    def on_connect(self, client: Any, userdata: Any, flags: Any, reason_code: Any, properties: Any = None) -> None:
        if getattr(reason_code, "is_failure", False):
            self.connected = False
            if str(reason_code) in _AUTH_REFUSALS:
                self.refused = str(reason_code)
            return
        self.connected, self.connected_at, self.got_message, self.refused = True, self.clock(), False, None
        client.subscribe(self.topic)
        self.notify("Verbunden. Warte auf Daten vom Auto … (Strg+C beendet)")

    def on_subscribe(self, client: Any, userdata: Any, mid: Any, reason_codes: Any, properties: Any = None) -> None:
        if any(getattr(code, "is_failure", False) for code in reason_codes):
            self.subscribe_refused = True

    def on_message(self, client: Any, userdata: Any, message: Any) -> None:
        parsed = parse_message(bytes(message.payload))
        if parsed is not None:
            self.got_message = True
            self.handle(*parsed)

    def on_disconnect(self, client: Any, userdata: Any, flags: Any, reason_code: Any, properties: Any = None) -> None:
        if self.connected and not self.stable():
            self.short_drops += 1
        self.connected = False


def _refusal_error(reason: str) -> StreamError:
    return StreamError(
        f"BMW lehnt den Datenstrom ab ({reason}). Häufige Ursachen: Eine andere Verbindung nutzt den "
        "Stream schon (BMW erlaubt nur eine, z. B. Home Assistant), 'CarData Stream' ist im Portal "
        "nicht angefordert, oder die Anmeldung stammt von vor der Freigabe (dann neu anmelden)."
    )


_SUBSCRIBE_REFUSED = StreamError(
    "BMW hat das Abonnement des Datenstroms abgelehnt. Ist der Datenstrom im Portal konfiguriert "
    "(unter CARDATA STREAMING Datenpunkte angehakt)?"
)
_KICKED_OUT = StreamError(
    "Die Verbindung wird immer wieder kurz nach dem Aufbau getrennt. Vermutlich nutzt ein anderes "
    "Programm (z. B. Home Assistant) den Datenstrom; BMW erlaubt nur eine Verbindung pro Konto."
)


def _open(action: Callable[[], Any], notify: Callable[[str], None]) -> None:
    """Verbindet; Netzfehler werden gemeldet und später wiederholt, TLS-Fehler sind endgültig."""
    try:
        action()
    except ssl.SSLCertVerificationError as err:
        raise StreamError(
            "Das Zertifikat des BMW-Servers ist ungültig; Verbindung abgebrochen. Liegt ein Proxy "
            "dazwischen, der TLS aufbricht?"
        ) from err
    except ssl.SSLError as err:
        raise StreamError(
            f"TLS-Fehler beim Verbinden ({type(err).__name__}). BMWs Server verlangt TLS 1.3; "
            "dafür ist OpenSSL 1.1.1 oder neuer nötig."
        ) from err
    except OSError as err:
        notify(f"Keine Verbindung zu BMW ({type(err).__name__}).")


def _renew(credentials: Callable[[bool], Credentials], previous: Credentials, now: float) -> Credentials:
    creds = credentials(True)
    if creds.expires_at - REFRESH_MARGIN_SECONDS <= now or creds.id_token == previous.id_token:
        raise StreamError("BMW hat den Zugang nicht verlängert. Bitte neu anmelden ('bmw-cardata anmelden').")
    return creds


def run_stream(
    client: Any,
    credentials: Callable[[bool], Credentials],
    handle: DataHandler,
    notify: Callable[[str], None],
    *,
    clock: Callable[[], float] = time.time,
    sleep: Callable[[float], None] | None = None,
    stop: Callable[[], bool] = lambda: False,
) -> None:
    """Hält die Verbindung, erneuert den Zugang rechtzeitig und verbindet nach Abbrüchen neu.

    credentials(True) muss die Tokens erneuern; credentials(False) darf gespeicherte liefern.
    """
    creds = credentials(False)
    conn = _Connection(topic_for(creds.gcid), handle, notify, clock)
    client.on_connect, client.on_subscribe = conn.on_connect, conn.on_subscribe
    client.on_message, client.on_disconnect = conn.on_message, conn.on_disconnect
    client.username_pw_set(creds.gcid, creds.id_token)
    try:
        _open(lambda: client.connect(STREAM_HOST, STREAM_PORT, KEEPALIVE_SECONDS), notify)
        _Loop(client, conn, creds, credentials, sleep or time.sleep).run(stop)
    finally:
        client.disconnect()


class _Loop:
    """Die Schleife um client.loop(): Ablehnungen, Erneuerung des Zugangs, Wiederverbinden."""

    def __init__(
        self,
        client: Any,
        conn: _Connection,
        creds: Credentials,
        credentials: Callable[[bool], Credentials],
        sleep: Callable[[float], None],
    ) -> None:
        self.client, self.conn, self.creds, self.credentials, self.sleep = client, conn, creds, credentials, sleep
        self.refusals = 0
        self.failures = 0

    def run(self, stop: Callable[[], bool]) -> None:
        while not stop():
            rc = self.client.loop(LOOP_TIMEOUT_SECONDS)
            self._check()
            if self.conn.refused:
                self._refused()
            elif self.conn.clock() >= self.creds.expires_at - REFRESH_MARGIN_SECONDS:
                self._renew_and_reconnect()
            elif rc != 0 and not self.conn.connected:
                self._back_off(f"Verbindung getrennt, neuer Versuch in {self._next_delay()} s.")
                self._reconnect()

    def _check(self) -> None:
        if self.conn.subscribe_refused:
            raise _SUBSCRIBE_REFUSED
        if self.conn.short_drops >= MAX_SHORT_DROPS:
            raise _KICKED_OUT
        if self.conn.connected:
            self.refusals = 0
        if self.conn.stable():
            self.failures, self.conn.short_drops = 0, 0

    def _next_delay(self) -> int:
        return RECONNECT_DELAYS[min(self.failures, len(RECONNECT_DELAYS) - 1)]

    def _back_off(self, message: str) -> None:
        delay = self._next_delay()
        self.failures += 1
        self.conn.notify(message)
        self.sleep(delay)

    def _reconnect(self) -> None:
        _open(self.client.reconnect, self.conn.notify)

    def _use(self, creds: Credentials) -> None:
        self.creds = creds
        self.client.username_pw_set(creds.gcid, creds.id_token)

    def _try_renew(self) -> bool:
        """Erneuert den Zugang; bei Netzproblemen später erneut (False), sonst endgültig."""
        try:
            self._use(_renew(self.credentials, self.creds, self.conn.clock()))
            return True
        except _TRANSIENT_RENEWAL as err:
            self._back_off(f"Zugang konnte nicht erneuert werden ({type(err).__name__}), "
                           f"neuer Versuch in {self._next_delay()} s.")
            return False

    def _refused(self) -> None:
        reason, self.conn.refused = self.conn.refused or "", None
        self.refusals += 1
        if self.refusals >= MAX_REFUSALS:
            raise _refusal_error(reason)
        if self.refusals == 2 and not self._try_renew():
            return
        self.sleep(REFUSAL_PAUSE_SECONDS)
        self._reconnect()

    def _renew_and_reconnect(self) -> None:
        if not self._try_renew():
            return
        self.client.disconnect()
        self.sleep(CREDENTIAL_PAUSE_SECONDS)
        self._reconnect()
