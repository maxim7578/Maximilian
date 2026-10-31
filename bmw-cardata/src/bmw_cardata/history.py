"""Lokaler Verlauf gespeicherter Statusabrufe (eine JSON-Zeile pro Abruf, Rechte 600)."""

from __future__ import annotations

import csv
import io
import json
from dataclasses import dataclass
from datetime import datetime, tzinfo
from pathlib import Path
from typing import Any

from .descriptors import STATUS_FIELDS, Field
from .files import append_private
from .report import field_entry, format_value

HISTORY_FILE = "verlauf.jsonl"
HISTORY_LABELS = ("Kilometerstand", "Ladestand Hochvoltbatterie", "Elektrische Reichweite", "Tankfüllstand")
_MILEAGE = next(field for field in STATUS_FIELDS if field.label == "Kilometerstand")
_FORMULA_START = ("=", "+", "-", "@", "\t", "\r")


@dataclass(frozen=True)
class Entry:
    time: str  # ISO 8601 in UTC, z. B. 2026-10-31T10:00:00Z
    vin: str
    data: dict[str, dict[str, Any]]


def history_path(state_file: Path) -> Path:
    return state_file.with_name(HISTORY_FILE)


def append_entry(path: Path, entry: Entry) -> None:
    line = json.dumps({"zeit": entry.time, "fahrgestellnummer": entry.vin, "werte": entry.data}, ensure_ascii=False)
    append_private(path, line)


def _parse(line: str) -> Entry | None:
    try:
        raw = json.loads(line)
        time, vin, data = raw["zeit"], raw["fahrgestellnummer"], raw["werte"]
    except (ValueError, KeyError, TypeError):
        return None
    if not (isinstance(time, str) and isinstance(vin, str) and isinstance(data, dict)):
        return None
    return Entry(time, vin, {k: v for k, v in data.items() if isinstance(v, dict)})


def load_entries(path: Path) -> list[Entry]:
    """Alle lesbaren Einträge in gespeicherter Reihenfolge; kaputte Zeilen werden übersprungen."""
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()
    return [entry for entry in (_parse(line) for line in lines if line.strip()) if entry is not None]


def _local_time(stamp: str, tz: tzinfo | None) -> str:
    try:
        moment = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
    except ValueError:
        return stamp
    return moment.astimezone(tz).strftime("%d.%m.%Y %H:%M")


def _mileage(entry: Entry) -> float | None:
    found = field_entry(entry.data, _MILEAGE)
    try:
        return float(found["value"]) if found else None
    except (TypeError, ValueError):
        return None


def _values_text(entry: Entry) -> str:
    fields = [field for field in STATUS_FIELDS if field.label in HISTORY_LABELS]
    found = [(field.label, field_entry(entry.data, field)) for field in fields]
    parts = [f"{label}: {format_value(item)}" for label, item in found if item is not None]
    return ", ".join(parts) or "keine Werte"


def _driven(previous: Entry | None, entry: Entry) -> str:
    before = _mileage(previous) if previous else None
    now = _mileage(entry)
    if before is None or now is None:
        return ""
    diff = now - before
    text = f"{int(diff):+d}" if diff == int(diff) else f"{diff:+.1f}"
    return f"  ({text} km)"


def history_lines(entries: list[Entry], limit: int, tz: tzinfo | None = None) -> list[str]:
    """Die letzten Einträge, mit gefahrenen Kilometern seit dem Eintrag davor (gleiches Fahrzeug)."""
    if not entries:
        return ["Noch kein Verlauf gespeichert. Nutze 'bmw-cardata status --speichern'."]
    several = len({entry.vin for entry in entries}) > 1
    last_by_vin: dict[str, Entry] = {}
    lines = []
    for entry in entries:
        vin = f"{entry.vin}  " if several else ""
        driven = _driven(last_by_vin.get(entry.vin), entry)
        lines.append(f"{_local_time(entry.time, tz)}  {vin}{_values_text(entry)}{driven}")
        last_by_vin = {**last_by_vin, entry.vin: entry}
    return lines[-limit:]


def _cell(entry: Entry, field: Field) -> Any:
    found = field_entry(entry.data, field)
    value = found.get("value") if found else ""
    if isinstance(value, str) and value.startswith(_FORMULA_START):
        return "'" + value  # verhindert, dass Tabellenprogramme Text als Formel ausführen
    return value


def history_csv(entries: list[Entry]) -> str:
    """Alle Einträge als CSV mit Semikolon (öffnet in deutschem Excel direkt in Spalten)."""
    out = io.StringIO()
    writer = csv.writer(out, delimiter=";", lineterminator="\n")
    writer.writerow(["zeit", "fahrgestellnummer", *(field.label for field in STATUS_FIELDS)])
    for entry in entries:
        writer.writerow([entry.time, entry.vin, *(_cell(entry, field) for field in STATUS_FIELDS)])
    return out.getvalue()
