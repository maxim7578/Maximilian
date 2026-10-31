"""Kommandozeile: bmw-cardata anmelden | fahrzeuge | basisdaten | status | abmelden."""

from __future__ import annotations

import argparse
import sys
import time
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import TextIO

import httpx

from .api import ApiError
from .auth import AuthError, create_pkce_pair, poll_for_tokens, request_device_code
from .config import HTTP_TIMEOUT_SECONDS, ConfigError, client_id_from_env, state_path, validate_client_id, validate_vin
from .report import basic_data_lines, status_lines
from .service import Session, fetch_status, open_session, resolve_vin
from .state import State, StateError, delete_state, load_state, save_state

HttpFactory = Callable[[], httpx.Client]


def _default_http() -> httpx.Client:
    return httpx.Client(timeout=HTTP_TIMEOUT_SECONDS)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="bmw-cardata", description="Liest Fahrzeugdaten über die offizielle BMW CarData API."
    )
    parser.add_argument("--state", help="Pfad der Anmeldedatei (Standard: ~/.config/bmw-cardata/state.json)")
    commands = parser.add_subparsers(dest="command", required=True)
    login = commands.add_parser("anmelden", help="Per Gerätecode bei BMW anmelden")
    login.add_argument("--client-id", help="Client-ID aus dem BMW-CarData-Portal")
    commands.add_parser("fahrzeuge", help="Fahrgestellnummern deiner Fahrzeuge anzeigen")
    basic = commands.add_parser("basisdaten", help="Basisdaten eines Fahrzeugs anzeigen")
    basic.add_argument("vin", help="Fahrgestellnummer")
    status = commands.add_parser("status", help="Aktuellen Fahrzeugstatus anzeigen")
    status.add_argument("vin", nargs="?", help="Fahrgestellnummer (ohne Angabe: dein einziges Fahrzeug)")
    commands.add_parser("abmelden", help="Gespeicherte Anmeldung löschen")
    return parser


def _login(args: argparse.Namespace, path: Path, http: httpx.Client, out: TextIO) -> None:
    client_id = validate_client_id(args.client_id) if args.client_id else client_id_from_env()
    verifier, challenge = create_pkce_pair()
    device = request_device_code(http, client_id, challenge)
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


def _run_with_session(args: argparse.Namespace, path: Path, http: httpx.Client, out: TextIO) -> None:
    session: Session = open_session(http, load_state(path), path, time.time())
    if args.command == "fahrzeuge":
        vins = session.api.vehicles()
        lines = vins or ["Keine Fahrzeuge gefunden."]
    elif args.command == "basisdaten":
        lines = basic_data_lines(session.api.basic_data(validate_vin(args.vin)))
    else:
        vin = resolve_vin(session, validate_vin(args.vin) if args.vin else None, _only_vehicle)
        lines = [f"Fahrzeug {vin}", *status_lines(fetch_status(session, vin, path))]
    print("\n".join(lines), file=out)


def run(
    argv: Sequence[str] | None = None,
    out: TextIO = sys.stdout,
    err: TextIO = sys.stderr,
    http_factory: HttpFactory = _default_http,
) -> int:
    args = build_parser().parse_args(argv)
    path = state_path(args.state)
    try:
        if args.command == "abmelden":
            removed = delete_state(path)
            print("Abgemeldet." if removed else "Es war keine Anmeldung gespeichert.", file=out)
            return 0
        with http_factory() as http:
            if args.command == "anmelden":
                _login(args, path, http, out)
            else:
                _run_with_session(args, path, http, out)
        return 0
    except (ConfigError, AuthError, ApiError, StateError) as error:
        print(f"Fehler: {error}", file=err)
    except httpx.HTTPError as error:
        print(f"Netzwerkfehler: {type(error).__name__}", file=err)
    except KeyboardInterrupt:
        print("Abgebrochen.", file=err)
    return 1


def main() -> None:
    sys.exit(run())
