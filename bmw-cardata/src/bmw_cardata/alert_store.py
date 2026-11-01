"""Einstellungen der Warnungen (warnungen.json) und welche zuletzt galten (warnungen-zustand.json)."""

from __future__ import annotations

import json
import secrets
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .alerts import Alert, AlertSettings
from .files import write_private

SETTINGS_FILE = "warnungen.json"
STATE_FILE = "warnungen-zustand.json"
_KEYS = {  # Feld der Einstellungen -> Schlüssel in der Datei
    "ntfy_topic": "ntfy_thema",
    "ntfy_server": "ntfy_server",
    "min_soc": "ladestand_min",
    "min_12v": "batterie_12v_min",
    "tire_tolerance_bar": "reifendruck_toleranz_bar",
    "locked_values": "verriegelt",
}


def settings_path(state_file: Path) -> Path:
    return state_file.with_name(SETTINGS_FILE)


def state_path_for(state_file: Path) -> Path:
    return state_file.with_name(STATE_FILE)


def new_topic() -> str:
    """Ein schwer zu erratendes Thema: Wer es kennt, kann die Pushes mitlesen."""
    return f"bmw-{secrets.token_urlsafe(16)}"


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _parse_settings(raw: Any) -> AlertSettings | None:
    """Einstellungen aus dem Dateiinhalt; None, wenn er nicht gültig ist."""
    if not isinstance(raw, dict):
        return None
    values = {field: raw[key] for field, key in _KEYS.items() if key in raw}
    if "locked_values" in values:
        locked = values["locked_values"]
        if not isinstance(locked, list) or not all(isinstance(v, str) for v in locked):
            return None
        values["locked_values"] = tuple(locked)
    try:
        return AlertSettings(**values)
    except (TypeError, ValueError):
        return None


def load_settings(path: Path) -> AlertSettings:
    """Die Einstellungen; fehlt die Datei oder ist sie beschädigt, gelten die Standardwerte."""
    return _parse_settings(_load_json(path)) or AlertSettings()


def settings_problem(path: Path) -> str | None:
    """Ein Hinweis, falls warnungen.json existiert, aber nicht gültig ist."""
    if not path.exists() or _parse_settings(_load_json(path)) is not None:
        return None
    return f"{path} ist beschädigt; es gelten die Standardwerte, Pushes sind aus. Datei reparieren oder löschen."


def _as_file(settings: AlertSettings) -> dict[str, Any]:
    raw = asdict(settings)
    return {key: (list(raw[f]) if f == "locked_values" else raw[f]) for f, key in _KEYS.items()}


def save_settings(path: Path, settings: AlertSettings) -> None:
    write_private(path, json.dumps(_as_file(settings), ensure_ascii=False, indent=2))


def settings_lines(settings: AlertSettings) -> list[str]:
    push = f"{settings.ntfy_server.rstrip('/')}/{settings.ntfy_topic}" if settings.ntfy_topic else "aus"
    return [
        f"Push über ntfy: {push}",
        f"Warnen bei: Ladestand unter {settings.min_soc:g} %, 12-V-Batterie unter {settings.min_12v:g} %, "
        f"Reifendruck {settings.tire_tolerance_bar:g} bar unter Soll",
        f"Als verriegelt gilt: {', '.join(settings.locked_values)}",
    ]


@dataclass(frozen=True)
class _Snapshot:
    aktiv: list[str]
    ladestatus: str | None


def load_alert_state(path: Path, vin: str) -> dict[str, Any]:
    """Der letzte Stand eines Fahrzeugs; ein beschädigter Eintrag zählt wie keiner."""
    raw = _load_json(path)
    entry = raw.get(vin) if isinstance(raw, dict) else None
    if not isinstance(entry, dict):
        return {}
    active, status = entry.get("aktiv", []), entry.get("ladestatus")
    if not isinstance(active, list) or not all(isinstance(k, str) for k in active):
        return {}
    if status is not None and not isinstance(status, str):
        return {}
    return {"aktiv": active, "ladestatus": status}


def save_alert_state(path: Path, vin: str, active: tuple[Alert, ...], status: str | None) -> None:
    """Merkt sich die geltenden Warnungen; fehlt der Ladestatus, bleibt der letzte bekannte."""
    raw = _load_json(path)
    vehicles = raw if isinstance(raw, dict) else {}
    previous = vehicles.get(vin) if isinstance(vehicles.get(vin), dict) else {}
    snapshot = _Snapshot([a.key for a in active], status or previous.get("ladestatus"))
    try:
        write_private(path, json.dumps({**vehicles, vin: asdict(snapshot)}, ensure_ascii=False))
    except OSError:
        pass  # dann meldet sich eine Warnung eben noch einmal
