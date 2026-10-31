"""Bereitet API-Antworten als deutschen Text auf."""

from __future__ import annotations

import json
import unicodedata
from typing import Any

from .descriptors import LATITUDE, LONGITUDE, STATUS_FIELDS, Field, all_descriptors

_BOOLEANS = {True: "ja", False: "nein", "true": "ja", "false": "nein"}


def printable(text: str) -> str:
    """Entfernt Steuer- und Formatzeichen (z. B. ANSI-Escapes, Richtungswechsel) aus Netzdaten,
    damit sie das Terminal nicht verändern können."""
    return "".join(ch for ch in text if not unicodedata.category(ch).startswith("C"))


def format_value(entry: dict[str, Any]) -> str | None:
    value = entry.get("value")
    if value is None or value == "":
        return None
    key = value.lower() if isinstance(value, str) else value
    if isinstance(key, (bool, str)) and key in _BOOLEANS:
        text = _BOOLEANS[key]
    else:
        text = str(value)
    unit = entry.get("unit")
    shown = f"{text} {unit}" if unit else text
    return printable(shown)


def field_entry(data: dict[str, dict[str, Any]], field: Field) -> dict[str, Any] | None:
    """Der erste Datenpunkt eines Feldes, für den BMW einen Wert geliefert hat."""
    for descriptor in field.descriptors:
        entry = data.get(descriptor)
        if entry is not None and format_value(entry) is not None:
            return entry
    return None


def status_lines(data: dict[str, dict[str, Any]]) -> list[str]:
    """Eine Zeile pro Feld, für das BMW einen Wert geliefert hat."""
    lines = []
    for field in STATUS_FIELDS:
        entry = field_entry(data, field)
        if entry is None:
            continue
        stamp = entry.get("timestamp")
        suffix = f"  (Stand: {stamp})" if stamp else ""
        lines.append(f"{field.label}: {format_value(entry)}{suffix}")
    link = map_link(data)
    if link:
        lines.append(f"Karte: {link}")
    if not lines:
        return [
            "BMW hat noch keine Werte geliefert. Öffne kurz die My-BMW-App oder "
            "fahre ein Stück, damit das Auto Daten sendet."
        ]
    return lines


def basic_data_lines(data: dict[str, Any]) -> list[str]:
    lines = [f"{key}: {value}" for key, value in sorted(data.items()) if value not in (None, "", [], {})]
    return lines or ["Keine Basisdaten vorhanden."]


def _coordinate(data: dict[str, dict[str, Any]], descriptor: str, limit: float) -> float | None:
    value = (data.get(descriptor) or {}).get("value")
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if -limit <= number <= limit else None


def map_link(data: dict[str, dict[str, Any]]) -> str | None:
    """OpenStreetMap-Link zur letzten Position, falls BMW eine gültige geliefert hat."""
    lat = _coordinate(data, LATITUDE, 90.0)
    lon = _coordinate(data, LONGITUDE, 180.0)
    if lat is None or lon is None:
        return None
    return f"https://www.openstreetmap.org/?mlat={lat}&mlon={lon}#map=17/{lat}/{lon}"


def status_json(vin: str, data: dict[str, dict[str, Any]], fetched_at: str) -> str:
    """Maschinenlesbarer Status: nur die abgefragten Datenpunkte, unverändert von BMW."""
    wanted = set(all_descriptors())
    values = {key: entry for key, entry in sorted(data.items()) if key in wanted}
    payload = {"fahrgestellnummer": vin, "abgerufen": fetched_at, "werte": values}
    return json.dumps(payload, indent=2)  # maskiert Steuerzeichen aus dem Netz
