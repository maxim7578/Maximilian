"""Kommandozeile: anmelden | fahrzeuge | basisdaten | status | live | verlauf | kontingent | abmelden."""

from __future__ import annotations

import argparse
import json
import sys
import time
from collections.abc import Callable, Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import TextIO

import httpx

from .api import ApiError
from .auth import AuthError, create_pkce_pair, poll_for_tokens, refresh_tokens, request_device_code
from .config import (
    API_ONLY_SCOPE,
    DEFAULT_SCOPE,
    HTTP_TIMEOUT_SECONDS,
    ConfigError,
    client_id_from_env,
    state_path,
    validate_client_id,
    validate_vin,
)
from .history import Entry, append_entry, history_csv, history_lines, history_path, load_entries
from .report import basic_data_lines, status_json, status_lines
from .service import Session, fetch_vehicle_status, open_session, remember_vehicles
from .state import State, StateError, delete_state, load_state, save_state
from .stream import REFRESH_MARGIN_SECONDS, Credentials, StreamError, message_lines, run_stream, stream_credentials
from .stream import create_client as create_stream_client
from .usage import DAILY_LIMIT, load_usage, record_call, usage_path

HttpFactory = Callable[[], httpx.Client]
MAX_HISTORY_LINES = 1000


def _default_http() -> httpx.Client:
    return httpx.Client(timeout=HTTP_TIMEOUT_SECONDS)


def _line_count(raw: str) -> int:
    try:
        count = int(raw)
    except ValueError as err:
        raise argparse.ArgumentTypeError("muss eine ganze Zahl sein") from err
    if not 1 <= count <= MAX_HISTORY_LINES:
        raise argparse.ArgumentTypeError(f"muss zwischen 1 und {MAX_HISTORY_LINES} liegen")
    return count


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="bmw-cardata", description="Liest Fahrzeugdaten über die offizielle BMW CarData API."
    )
    parser.add_argument("--state", help="Pfad der Anmeldedatei (Standard: ~/.config/bmw-cardata/state.json)")
    commands = parser.add_subparsers(dest="command", required=True)
    login = commands.add_parser("anmelden", help="Per Gerätecode bei BMW anmelden")
    login.add_argument("--client-id", help="Client-ID aus dem BMW-CarData-Portal")
    login.add_argument("--nur-api", action="store_true", help="Ohne Datenstrom anmelden (kein 'live')")
    commands.add_parser("fahrzeuge", help="Fahrgestellnummern deiner Fahrzeuge anzeigen")
    basic = commands.add_parser("basisdaten", help="Basisdaten eines Fahrzeugs anzeigen")
    basic.add_argument("vin", help="Fahrgestellnummer")
    status = commands.add_parser("status", help="Aktuellen Fahrzeugstatus anzeigen")
    status.add_argument("vin", nargs="?", help="Fahrgestellnummer (ohne Angabe: dein einziges Fahrzeug)")
    status.add_argument("--json", action="store_true", help="Ausgabe als JSON")
    status.add_argument("--speichern", action="store_true", help="Abruf im lokalen Verlauf ablegen")
    live = commands.add_parser("live", help="Live-Daten vom Auto empfangen, bis Strg+C (ohne Tageslimit)")
    live.add_argument("vin", nargs="?", help="Nur dieses Fahrzeug (ohne Angabe: alle des Kontos)")
    live.add_argument("--json", action="store_true", help="Eine JSON-Zeile pro Nachricht")
    live.add_argument("--speichern", action="store_true", help="Nachrichten im lokalen Verlauf ablegen")
    history = commands.add_parser("verlauf", help="Gespeicherte Abrufe anzeigen (ohne Abruf bei BMW)")
    history.add_argument("--anzahl", type=_line_count, default=10, help="Wie viele Einträge (Standard: 10)")
    history.add_argument("--csv", action="store_true", help="Alle Einträge als CSV ausgeben")
    commands.add_parser("kontingent", help="Eigene Abrufe der letzten 24 Stunden anzeigen")
    commands.add_parser("abmelden", help="Gespeicherte Anmeldung löschen")
    return parser


def _login(args: argparse.Namespace, path: Path, http: httpx.Client, out: TextIO) -> None:
    client_id = validate_client_id(args.client_id) if args.client_id else client_id_from_env()
    verifier, challenge = create_pkce_pair()
    device = request_device_code(http, client_id, challenge, API_ONLY_SCOPE if args.nur_api else DEFAULT_SCOPE)
    link = device.verification_uri_complete or device.verification_uri
    print(f"Öffne {link} und bestätige mit dem Code {device.user_code}.", file=out)
    print("Warte auf die Bestätigung …", file=out, flush=True)
    tokens = poll_for_tokens(http, client_id, device, verifier)
    save_state(path, State(client_id=client_id, tokens=tokens))
    print(f"Angemeldet. Zugangsdaten gespeichert in {path}.", file=out)


def _only_vehicle(vins: list[str]) -> str:
    if len(vins) > 1:
        raise ConfigError("Mehrere Fahrzeuge gefunden, bitte Fahrgestellnummer angeben: " + ", ".join(vins))
    return vins[0]


def _utc_stamp(now: float) -> str:
    return datetime.fromtimestamp(now, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _status(args: argparse.Namespace, session: Session, path: Path) -> list[str]:
    explicit = validate_vin(args.vin) if args.vin else None
    vin, data = fetch_vehicle_status(session, explicit, _only_vehicle, path)
    stamp = _utc_stamp(time.time())
    problem = _save_history(path, Entry(stamp, vin, data)) if args.speichern else None
    if args.json:
        return [status_json(vin, data, stamp)]
    saved = [problem or "Im Verlauf gespeichert."] if args.speichern else []
    return [f"Fahrzeug {vin}", *status_lines(data), *saved]


def _save_history(path: Path, entry: Entry) -> str | None:
    """Speichert einen Eintrag; ein Dateifehler kostet nur den Eintrag. Gibt die Warnung zurück."""
    try:
        append_entry(history_path(path), entry)
    except OSError as error:
        return f"Verlauf konnte nicht gespeichert werden: {error.strerror or error}"
    return None


def _vehicles(session: Session, path: Path) -> list[str]:
    vins = session.api.vehicles()
    remember_vehicles(session, vins, path)
    return vins or ["Keine Fahrzeuge gefunden."]


def _run_with_session(args: argparse.Namespace, path: Path, http: httpx.Client, out: TextIO) -> None:
    counter = usage_path(path)
    session = open_session(http, load_state(path), path, time.time(), lambda: record_call(counter, time.time()))
    if args.command == "fahrzeuge":
        lines = _vehicles(session, path)
    elif args.command == "basisdaten":
        lines = basic_data_lines(session.api.basic_data(validate_vin(args.vin)))
    else:
        lines = _status(args, session, path)
    print("\n".join(lines), file=out)


class _LivePrinter:
    """Gibt Nachrichten aus; nennt das Fahrzeug nur, wenn es wechselt."""

    def __init__(self, args: argparse.Namespace, path: Path, out: TextIO, err: TextIO) -> None:
        self.only = validate_vin(args.vin) if args.vin else None
        self.as_json, self.save = args.json, args.speichern
        self.path, self.out, self.err = path, out, err
        self.last_vin: str | None = None

    def __call__(self, vin: str, data: dict[str, dict[str, object]]) -> None:
        if self.only and vin != self.only:
            return
        stamp = _utc_stamp(time.time())
        problem = _save_history(self.path, Entry(stamp, vin, data)) if self.save else None
        if problem:
            print(problem, file=self.err)
        if self.as_json:
            line = {"fahrgestellnummer": vin, "empfangen": stamp, "werte": data}
            print(json.dumps(line, ensure_ascii=False), file=self.out, flush=True)
            return
        lines = message_lines(data, datetime.now().astimezone())
        if lines and vin != self.last_vin:
            lines = [f"Fahrzeug {vin}", *lines]
            self.last_vin = vin
        if lines:
            print("\n".join(lines), file=self.out, flush=True)


def _stream_login(http: httpx.Client, path: Path) -> Callable[[bool], Credentials]:
    """Zugangsdaten für den Datenstrom; erneuert die Tokens, wenn nötig oder verlangt."""

    def provide(force: bool) -> Credentials:
        state = load_state(path)
        now = time.time()
        if force or state.tokens.is_expired(now, margin=REFRESH_MARGIN_SECONDS):
            state = state.with_tokens(refresh_tokens(http, state.client_id, state.tokens, now))
            save_state(path, state)
        return stream_credentials(state.tokens)

    return provide


def _live(args: argparse.Namespace, path: Path, http: httpx.Client, out: TextIO, err: TextIO) -> None:
    login = _stream_login(http, path)
    client = create_stream_client(login(False).gcid)
    notify = lambda text: print(text, file=err, flush=True)  # noqa: E731
    try:
        run_stream(client, login, _LivePrinter(args, path, out, err), notify)
    except KeyboardInterrupt:
        notify("Live-Ansicht beendet.")


def _quota_lines(path: Path, now: float) -> list[str]:
    usage = load_usage(usage_path(path))
    lines = [
        f"Abrufe in den letzten 24 Stunden: {len(usage.recent(now))} von {DAILY_LIMIT}",
        f"Noch frei: {usage.remaining(now)}",
    ]
    free_at = usage.next_free_at(now)
    if free_at is not None:
        lines.append(f"Nächster Abruf frei ab: {datetime.fromtimestamp(free_at).astimezone():%d.%m.%Y %H:%M}")
    return [*lines, "Gezählt werden nur Abrufe dieses Programms auf diesem Rechner."]


def _history_output(args: argparse.Namespace, path: Path) -> str:
    entries = load_entries(history_path(path))
    if args.csv:
        return history_csv(entries).rstrip("\n")
    return "\n".join(history_lines(entries, args.anzahl))


def _offline(args: argparse.Namespace, path: Path, out: TextIO) -> bool:
    """Befehle ohne Abruf bei BMW; True, wenn einer davon ausgeführt wurde."""
    if args.command == "abmelden":
        print("Abgemeldet." if delete_state(path) else "Es war keine Anmeldung gespeichert.", file=out)
        if history_path(path).exists():
            print(f"Der Verlauf {history_path(path)} bleibt erhalten; zum Löschen die Datei entfernen.", file=out)
    elif args.command == "kontingent":
        print("\n".join(_quota_lines(path, time.time())), file=out)
    elif args.command == "verlauf":
        print(_history_output(args, path), file=out)
    else:
        return False
    return True


def run(
    argv: Sequence[str] | None = None,
    out: TextIO = sys.stdout,
    err: TextIO = sys.stderr,
    http_factory: HttpFactory = _default_http,
) -> int:
    args = build_parser().parse_args(argv)
    path = state_path(args.state)
    try:
        if _offline(args, path, out):
            return 0
        with http_factory() as http:
            if args.command == "anmelden":
                _login(args, path, http, out)
            elif args.command == "live":
                _live(args, path, http, out, err)
            else:
                _run_with_session(args, path, http, out)
        return 0
    except (ConfigError, AuthError, ApiError, StateError, StreamError) as error:
        print(f"Fehler: {error}", file=err)
    except httpx.HTTPError as error:
        print(f"Netzwerkfehler: {type(error).__name__}", file=err)
    except OSError as error:
        print(f"Dateifehler: {error.strerror or error} ({error.filename or 'unbekannte Datei'})", file=err)
    except KeyboardInterrupt:
        print("Abgebrochen.", file=err)
    return 1


def main() -> None:
    sys.exit(run())
