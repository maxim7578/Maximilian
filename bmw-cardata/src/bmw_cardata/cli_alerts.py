"""Befehle rund um Warnungen: bmw-cardata warnungen pruefen | einstellen | test."""

from __future__ import annotations

import argparse
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path
from typing import Any

import httpx

from .alert_store import load_settings, new_topic, save_settings, settings_lines, settings_path, state_path_for
from .alert_watch import AlertWatcher
from .alerts import AlertSettings, evaluate
from .config import ConfigError
from .ntfy import send_push


def add_alert_parser(commands: Any) -> None:
    alerts = commands.add_parser("warnungen", help="Warnungen prüfen, einstellen oder einen Test-Push senden")
    actions = alerts.add_subparsers(dest="aktion", required=True)
    check = actions.add_parser("pruefen", help="Status abrufen (1 Abruf) und neue Warnungen melden und pushen")
    check.add_argument("vin", nargs="?", help="Fahrgestellnummer (ohne Angabe: dein einziges Fahrzeug)")
    check.add_argument("--alle", action="store_true", help="Alle geltenden Warnungen zeigen, nicht nur neue")
    settings = actions.add_parser("einstellen", help="Push und Grenzwerte einstellen (ohne Angabe: anzeigen)")
    settings.add_argument("--ntfy-thema", help="Thema für Pushes; 'neu' erzeugt ein zufälliges, 'aus' schaltet ab")
    settings.add_argument("--ntfy-server", help="Eigener ntfy-Server (https://…), Standard https://ntfy.sh")
    settings.add_argument("--ladestand", type=float, help="Warnen unter diesem Ladestand in %% (Standard 20)")
    settings.add_argument("--batterie-12v", type=float, help="Warnen unter diesem 12-V-Ladestand in %% (Standard 50)")
    settings.add_argument("--reifendruck-toleranz", type=float,
                          help="Warnen, wenn ein Reifen so viele bar unter dem Solldruck liegt (Standard 0.2)")
    settings.add_argument("--verriegelt", help="Werte des Türschlosses, die als verriegelt gelten (kommagetrennt)")
    actions.add_parser("test", help="Einen Test-Push senden")


def current_alert_lines(data: dict[str, dict[str, Any]], path: Path) -> list[str]:
    """Für 'status': alle gerade geltenden Warnungen (ohne Push, ohne Zustand zu ändern)."""
    alerts = evaluate(data, load_settings(settings_path(path)))
    return ["Warnungen", *(f"  {alert.text}" for alert in alerts)] if alerts else []


def _changes(args: argparse.Namespace) -> tuple[dict[str, Any], bool]:
    changes: dict[str, Any] = {}
    created = False
    if args.ntfy_thema is not None:
        topic = args.ntfy_thema.strip()
        created = topic.lower() == "neu"
        changes["ntfy_topic"] = new_topic() if created else (None if topic.lower() == "aus" else topic)
    if args.ntfy_server is not None:
        changes["ntfy_server"] = args.ntfy_server.strip()
    for option, field in (("ladestand", "min_soc"), ("batterie_12v", "min_12v"),
                          ("reifendruck_toleranz", "tire_tolerance_bar")):
        if getattr(args, option) is not None:
            changes[field] = getattr(args, option)
    if args.verriegelt is not None:
        values = tuple(v.strip().upper() for v in args.verriegelt.split(",") if v.strip())
        if not values:
            raise ConfigError("Bitte mindestens einen Wert für --verriegelt angeben.")
        changes["locked_values"] = values
    return changes, created


def configure(args: argparse.Namespace, path: Path) -> list[str]:
    file = settings_path(path)
    changes, created = _changes(args)
    try:
        settings = replace(load_settings(file), **changes)
    except ValueError as error:
        raise ConfigError(str(error)) from error
    if changes:
        save_settings(file, settings)
    lines = settings_lines(settings)
    if created:
        lines += [
            f"Neues Thema: {settings.ntfy_topic}",
            "In der ntfy-App (Android/iOS) dieses Thema abonnieren. Wer das Thema kennt, kann die "
            "Pushes mitlesen: nicht weitergeben.",
        ]
    return lines


def _push_for(http: httpx.Client, settings: AlertSettings) -> Callable[[str, list[str]], None] | None:
    if not settings.ntfy_topic:
        return None
    return lambda title, lines: send_push(http, settings, title, lines)


def make_watcher(path: Path, http: httpx.Client, report: Callable[[str], None]) -> AlertWatcher:
    settings = load_settings(settings_path(path))
    return AlertWatcher(settings, state_path_for(path), _push_for(http, settings), report)


def send_test(path: Path, http: httpx.Client) -> list[str]:
    settings = load_settings(settings_path(path))
    send_push(http, settings, "BMW CarData: Test", ["Wenn du das liest, kommen die Warnungen an."])
    return [f"Test-Push gesendet an {settings.ntfy_server.rstrip('/')}/{settings.ntfy_topic}."]


def check(vin: str, data: dict[str, dict[str, Any]], path: Path, http: httpx.Client, show_all: bool) -> list[str]:
    """Meldet neue Warnungen (und pusht sie); mit show_all zusätzlich alle, die gerade gelten."""
    reported: list[str] = []
    make_watcher(path, http, reported.append).check(vin, data)
    if not show_all:
        return [f"Fahrzeug {vin}", *(reported or ["Keine neuen Warnungen."])]
    current = [f"Warnung: {a.text}" for a in evaluate(data, load_settings(settings_path(path)))]
    extra = [line for line in reported if line not in current]  # z. B. "Laden beendet", Push-Hinweise
    return [f"Fahrzeug {vin}", *(current or ([] if extra else ["Keine Warnungen."])), *extra]
