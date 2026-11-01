"""Lokaler Verlauf gespeicherter Statusabrufe (eine JSON-Zeile pro Abruf, Rechte 600)."""

from __future__ import annotations

import csv
import errno
import io
import json
from dataclasses import dataclass
from datetime import datetime, timezone, tzinfo
from pathlib import Path
from typing import Any

from .descriptors import STATUS_FIELDS, Field
from .files import append_private, locked, write_private
from .report import field_entry, format_value

HISTORY_FILE = "verlauf.jsonl"
HISTORY_LABELS = ("Kilometerstand", "Ladestand Hochvoltbatterie", "Elektrische Reichweite", "Tankfüllstand")
_MILEAGE = next(field for field in STATUS_FIELDS if field.label == "Kilometerstand")
_FORMULA_START = ("=", "+", "-", "@", "\t", "\r")
# Alles aus der Navigation (aktuelle Position, Ziel) zählt als Standort.
LOCATION_PREFIX = "vehicle.cabin.infotainment.navigation."
_SECONDS_PER_DAY = 86_400


@dataclass(frozen=True)
class Entry:
    time: str  # ISO 8601 in UTC, z. B. 2026-10-31T10:00:00Z
    vin: str
    data: dict[str, dict[str, Any]]


def history_path(state_file: Path) -> Path:
    return state_file.with_name(HISTORY_FILE)


def append_entry(path: Path, entry: Entry) -> None:
    line = json.dumps({"zeit": entry.time, "fahrgestellnummer": entry.vin, "werte": entry.data}, ensure_ascii=False)
    with locked(path):  # sonst könnte ein gleichzeitiges Aufräumen die Zeile überschreiben
        append_private(path, line)


def _lines(text: str) -> list[str]:
    """Zeilen nur an \\n trennen: splitlines() würde auch an U+2028 u. Ä. in Textwerten trennen."""
    return text.split("\n")[:-1] if text.endswith("\n") else text.split("\n")


def without_location(data: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Die Werte ohne Breiten-/Längengrad und andere Navigationsdaten (neues Dict)."""
    return {key: value for key, value in data.items() if not key.startswith(LOCATION_PREFIX)}


def _stamp(line: str) -> datetime | None:
    """Zeitpunkt einer Verlaufszeile; None, wenn die Zeile keinen lesbaren hat."""
    try:
        raw = json.loads(line)
        moment = datetime.fromisoformat(raw["zeit"].replace("Z", "+00:00"))
    except (ValueError, KeyError, TypeError, AttributeError):
        return None
    return moment if moment.tzinfo else moment.replace(tzinfo=timezone.utc)


def prune_entries(path: Path, keep_days: int, now: float) -> int:
    """Entfernt Einträge, die älter als keep_days Tage sind (0 = unbegrenzt); gibt deren Zahl zurück.

    Jüngere und unlesbare Zeilen (auch solche ohne lesbaren Zeitstempel) bleiben Zeichen für
    Zeichen erhalten. Geschrieben wird nur, wenn etwas wegfällt, und dann atomar über eine
    Zwischendatei mit Rechten 600. Lesen und Ersetzen geschehen unter der Verlaufssperre, damit
    weder ein gleichzeitig angehängter Eintrag verloren geht noch ein gelöschter Verlauf zurückkehrt.
    """
    if keep_days <= 0 or not (path.exists() or path.is_symlink()):
        return 0
    with locked(path):
        if path.is_symlink():  # wie beim Anhängen: keinem Link folgen
            raise OSError(errno.ELOOP, "Der Verlauf ist ein symbolischer Link", str(path))
        if not path.exists():  # inzwischen gelöscht
            return 0
        cutoff = datetime.fromtimestamp(now - keep_days * _SECONDS_PER_DAY, timezone.utc)
        lines = _lines(path.read_text(encoding="utf-8", errors="surrogateescape"))
        kept = [line for line in lines if (stamp := _stamp(line)) is None or stamp >= cutoff]
        removed = len(lines) - len(kept)
        if removed:
            write_private(path, "".join(f"{line}\n" for line in kept), errors="surrogateescape")
        return removed


def delete_history(path: Path) -> bool:
    """Löscht den Verlauf samt liegengebliebener Zwischendateien; True, wenn es ihn gab.

    Unter der Verlaufssperre, damit ein gleichzeitiges Aufräumen ihn nicht wiederherstellt;
    die Sperrdatei verschwindet danach ebenfalls.
    """
    if not path.parent.is_dir():
        return False
    with locked(path):
        for leftover in path.parent.glob(f".{path.name}.*.tmp"):
            leftover.unlink(missing_ok=True)
        if path.exists() or path.is_symlink():
            path.unlink()
            return True
        return False


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
    lines = _lines(path.read_text(encoding="utf-8", errors="replace"))
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
    header = [f"{field.label} ({field.raw_unit})" if field.raw_unit else field.label for field in STATUS_FIELDS]
    writer.writerow(["zeit", "fahrgestellnummer", *header])
    for entry in entries:
        writer.writerow([entry.time, entry.vin, *(_cell(entry, field) for field in STATUS_FIELDS)])
    return out.getvalue()
