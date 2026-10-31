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
    """Zertifikat und Rechnername werden geprüft. TLS 1.2 wie in der Home-Assistant-Integration."""
    context = ssl.create_default_context()
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.maximum_version = ssl.TLSVersion.TLSv1_2
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

    def __init__(self, topic: str, handle: DataHandler, notify: Callable[[str], None]) -> None:
        self.topic = topic
        self.handle = handle
        self.notify = notify
        self.connected = False
        self.refused: str | None = None

    def on_connect(self, client: Any, userdata: Any, flags: Any, reason_code: Any, properties: Any = None) -> None:
        if getattr(reason_code, "is_failure", False):
            self.connected = False
            if str(reason_code) in _AUTH_REFUSALS:
                self.refused = str(reason_code)
            return
        self.connected = True
        self.refused = None
        client.subscribe(self.topic)
        self.notify("Verbunden. Warte auf Daten vom Auto … (Strg+C beendet)")

    def on_message(self, client: Any, userdata: Any, message: Any) -> None:
        parsed = parse_message(bytes(message.payload))
        if parsed is not None:
            self.handle(*parsed)

    def on_disconnect(self, client: Any, userdata: Any, flags: Any, reason_code: Any, properties: Any = None) -> None:
        self.connected = False


def _refusal_error(reason: str) -> StreamError:
    return StreamError(
        f"BMW lehnt den Datenstrom ab ({reason}). Häufige Ursachen: Eine andere Verbindung nutzt den "
        "Stream schon (BMW erlaubt nur eine, z. B. Home Assistant), 'CarData Stream' ist im Portal "
        "nicht angefordert, oder die Anmeldung stammt von vor der Freigabe (dann neu anmelden)."
    )


def _reconnect(client: Any) -> None:
    try:
        client.reconnect()
    except OSError:
        pass  # der nächste loop()-Durchlauf meldet die fehlende Verbindung erneut


def run_stream(
    client: Any,
    credentials: Callable[[bool], Credentials],
    handle: DataHandler,
    notify: Callable[[str], None],
    *,
    clock: Callable[[], float] = time.time,
    sleep: Callable[[float], None] = time.sleep,
    stop: Callable[[], bool] = lambda: False,
) -> None:
    """Hält die Verbindung, erneuert den Zugang rechtzeitig und verbindet nach Abbrüchen neu.

    credentials(True) muss die Tokens erneuern; credentials(False) darf gespeicherte liefern.
    """
    creds = credentials(False)
    state = _Connection(topic_for(creds.gcid), handle, notify)
    client.on_connect, client.on_message, client.on_disconnect = state.on_connect, state.on_message, state.on_disconnect
    client.username_pw_set(creds.gcid, creds.id_token)
    try:
        try:
            client.connect(STREAM_HOST, STREAM_PORT, KEEPALIVE_SECONDS)
        except OSError:
            notify("Keine Verbindung zu BMW.")
        _serve(client, state, creds, credentials, clock, sleep, stop)
    finally:
        client.disconnect()


def _fresh(credentials: Callable[[bool], Credentials], now: float) -> Credentials:
    creds = credentials(True)
    if creds.expires_at - REFRESH_MARGIN_SECONDS <= now:
        raise StreamError("BMW hat den Zugang nicht verlängert. Bitte neu anmelden ('bmw-cardata anmelden').")
    return creds


def _serve(
    client: Any,
    state: _Connection,
    creds: Credentials,
    credentials: Callable[[bool], Credentials],
    clock: Callable[[], float],
    sleep: Callable[[float], None],
    stop: Callable[[], bool],
) -> None:
    retried = False
    failures = 0
    while not stop():
        rc = client.loop(LOOP_TIMEOUT_SECONDS)
        if state.refused:
            if retried:
                raise _refusal_error(state.refused)
            retried, state.refused = True, None
            creds = _fresh(credentials, clock())
            client.username_pw_set(creds.gcid, creds.id_token)
            _reconnect(client)
            continue
        if state.connected:
            retried, failures = False, 0
        if clock() >= creds.expires_at - REFRESH_MARGIN_SECONDS:
            creds = _fresh(credentials, clock())
            client.username_pw_set(creds.gcid, creds.id_token)
            client.disconnect()
            _reconnect(client)
        elif rc != 0 and not state.connected:
            delay = RECONNECT_DELAYS[min(failures, len(RECONNECT_DELAYS) - 1)]
            failures += 1
            state.notify(f"Verbindung getrennt, neuer Versuch in {delay} s.")
            sleep(delay)
            _reconnect(client)
