"""Bereitet API-Antworten als deutschen Text auf."""

from __future__ import annotations

from typing import Any

from .descriptors import STATUS_FIELDS

_BOOLEANS = {True: "ja", False: "nein", "true": "ja", "false": "nein"}


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
    return f"{text} {unit}" if unit else text


def _first_present(data: dict[str, dict[str, Any]], descriptors: tuple[str, ...]) -> dict[str, Any] | None:
    for descriptor in descriptors:
        entry = data.get(descriptor)
        if entry is not None and format_value(entry) is not None:
            return entry
    return None


def status_lines(data: dict[str, dict[str, Any]]) -> list[str]:
    """Eine Zeile pro Feld, für das BMW einen Wert geliefert hat."""
    lines = []
    for field in STATUS_FIELDS:
        entry = _first_present(data, field.descriptors)
        if entry is None:
            continue
        stamp = entry.get("timestamp")
        suffix = f"  (Stand: {stamp})" if stamp else ""
        lines.append(f"{field.label}: {format_value(entry)}{suffix}")
    if not lines:
        return [
            "BMW hat noch keine Werte geliefert. Öffne kurz die My-BMW-App oder "
            "fahre ein Stück, damit das Auto Daten sendet."
        ]
    return lines


def basic_data_lines(data: dict[str, Any]) -> list[str]:
    lines = [f"{key}: {value}" for key, value in sorted(data.items()) if value not in (None, "", [], {})]
    return lines or ["Keine Basisdaten vorhanden."]
