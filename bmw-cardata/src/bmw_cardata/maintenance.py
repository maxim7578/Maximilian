"""Wartungsdaten (nächster Service, Hauptuntersuchung) aus einem eigenen Container.

Sie werden höchstens einmal am Tag je Fahrzeug abgerufen und in wartung.json
(Rechte 600) zwischengespeichert. Ein Fehler kostet nur diese Werte und wird
erst am nächsten Tag erneut versucht; das Tageslimit wird bei Bedarf gleich
beim nächsten Aufruf wieder probiert.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

from .api import ApiError, CarDataApi, RateLimitError
from .containers import SERVICE_CONTAINER, container_gone, provide_container
from .files import write_private

MAINTENANCE_FILE = "wartung.json"
MAX_AGE_SECONDS = 24 * 60 * 60

Values = dict[str, dict[str, Any]]


def maintenance_path(state_file: Path) -> Path:
    return state_file.with_name(MAINTENANCE_FILE)


def _load(path: Path) -> dict[str, Any]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return raw if isinstance(raw, dict) else {}


def _vehicle(cache: dict[str, Any], vin: str) -> dict[str, Any]:
    vehicles = cache.get("fahrzeuge")
    entry = vehicles.get(vin) if isinstance(vehicles, dict) else None
    return entry if isinstance(entry, dict) else {}


def _values(entry: dict[str, Any]) -> Values:
    raw = entry.get("werte")
    return {k: v for k, v in raw.items() if isinstance(v, dict)} if isinstance(raw, dict) else {}


def _text(value: Any) -> str | None:
    return value if isinstance(value, str) else None


def _save(path: Path, cache: dict[str, Any], vin: str, entry: dict[str, Any], container: dict[str, Any]) -> None:
    vehicles = cache.get("fahrzeuge") if isinstance(cache.get("fahrzeuge"), dict) else {}
    updated = {**cache, **container, "fahrzeuge": {**vehicles, vin: entry}}
    try:
        write_private(path, json.dumps(updated, ensure_ascii=False))
    except OSError:
        pass  # nur ein Zwischenspeicher: dann wird morgen eben erneut abgerufen


def maintenance_values(
    api: CarDataApi, vin: str, path: Path, now: float, today: str | None = None
) -> tuple[Values, list[str]]:
    """Wartungswerte für ein Fahrzeug und etwaige Hinweise; wirft nie wegen BMW-Fehlern."""
    cache = _load(path)
    entry = _vehicle(cache, vin)
    attempted = entry.get("versucht")
    if isinstance(attempted, (int, float)) and now - attempted < MAX_AGE_SECONDS:
        return _values(entry), []
    stored_id, stored_signature = _text(cache.get("container_id")), _text(cache.get("signatur"))
    try:
        choice = provide_container(api, SERVICE_CONTAINER, stored_id, stored_signature, today or date.today().isoformat())
        values = api.telematic_data(vin, choice.container_id)
    except RateLimitError:
        return _values(entry), ["Wartungsdaten: Tageslimit erreicht, es gelten die zuletzt gespeicherten."]
    except ApiError as err:
        container = {"container_id": None, "signatur": None} if container_gone(err) else {}
        _save(path, cache, vin, {**entry, "versucht": now}, container)
        return _values(entry), [f"Wartungsdaten konnten nicht abgerufen werden ({err}); nächster Versuch morgen."]
    _save(path, cache, vin, {"versucht": now, "werte": values},
          {"container_id": choice.container_id, "signatur": choice.signature})
    return values, [choice.note] if choice.note else []
