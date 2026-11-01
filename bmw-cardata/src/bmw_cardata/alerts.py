"""Warnregeln: was am Fahrzeugzustand auffällt, und welche Warnungen neu sind.

Bewertet werden nur Werte, deren Bedeutung belegt ist (Öffnungen: CLOSED, INTERMEDIATE,
OPEN; Ja/Nein; Zahlen). Beim Türschloss ist kein Wertebereich dokumentiert: Als
verriegelt gelten die eingestellten Werte (Standard LOCKED, SECURED), die Warnung nennt
den Originalwert, damit ein Fehlalarm sofort erkennbar ist.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Any

import httpx

from .descriptors import STATUS_FIELDS, TIRES
from .report import field_entry, format_value

# Laut Home-Assistant-Integration (soc_prediction.py) Werte für aktives Laden.
CHARGING_ACTIVE = frozenset({"CHARGINGACTIVE", "CHARGING_ACTIVE", "CHARGING", "CHARGING_IN_PROGRESS"})
_OPEN_WORDS = frozenset({"OPEN", "INTERMEDIATE", "TRUE"})
_CLOSED_WORDS = frozenset({"CLOSED", "FALSE"})
_NO_VALUE = frozenset({"", "INVALID", "UNKNOWN"})  # wie "kein Wert": weder Alarm noch Entwarnung
_TOPIC = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
_BY_LABEL = {field.label: field for field in STATUS_FIELDS}

_OPENINGS = (
    "Fahrertür offen", "Beifahrertür offen", "Tür hinten Fahrerseite offen", "Tür hinten Beifahrerseite offen",
    "Fenster Fahrer", "Fenster Beifahrer", "Fenster hinten Fahrerseite", "Fenster hinten Beifahrerseite",
    "Heckklappe offen", "Motorhaube offen", "Schiebedach",
)


@dataclass(frozen=True)
class Alert:
    key: str  # bleibt gleich, solange derselbe Zustand besteht
    text: str


@dataclass(frozen=True)
class AlertSettings:
    ntfy_topic: str | None = None
    ntfy_server: str = "https://ntfy.sh"
    min_soc: float = 20.0
    min_12v: float = 50.0
    tire_tolerance_bar: float = 0.2
    locked_values: tuple[str, ...] = ("LOCKED", "SECURED")

    def __post_init__(self) -> None:
        if not _valid_server(self.ntfy_server):
            raise ValueError("Der ntfy-Server muss eine gültige Adresse mit https:// sein.")
        if self.ntfy_topic is not None and not _TOPIC.fullmatch(self.ntfy_topic):
            raise ValueError("Das ntfy-Thema darf nur Buchstaben, Ziffern, - und _ enthalten (höchstens 64).")
        for name, value in (("Ladestand", self.min_soc), ("12-V-Grenze", self.min_12v)):
            if not 0 <= value <= 100:
                raise ValueError(f"{name} muss zwischen 0 und 100 % liegen.")
        if not 0 <= self.tire_tolerance_bar <= 2:
            raise ValueError("Die Reifendruck-Toleranz muss zwischen 0 und 2 bar liegen.")


def _valid_server(address: str) -> bool:
    try:
        url = httpx.URL(address)
    except (httpx.InvalidURL, TypeError, ValueError):
        return False
    return url.scheme == "https" and bool(url.host) and " " not in address


def _number(entry: dict[str, Any] | None) -> float | None:
    value = entry.get("value") if entry else None
    if isinstance(value, bool):
        return None
    try:
        number = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _entry(data: dict[str, dict[str, Any]], label: str) -> dict[str, Any] | None:
    return field_entry(data, _BY_LABEL[label])


def _opening(entry: dict[str, Any] | None) -> bool | None:
    """True offen, False geschlossen, None ohne verwertbaren Wert (fehlt, INVALID, unbekannt)."""
    value = entry.get("value") if entry else None
    if isinstance(value, bool):
        return value
    word = value.strip().upper() if isinstance(value, str) else None
    return True if word in _OPEN_WORDS else False if word in _CLOSED_WORDS else None


def _lock_value(entry: dict[str, Any] | None) -> str | None:
    value = entry.get("value") if entry else None
    word = value.strip().upper() if isinstance(value, str) else ""
    return None if word in _NO_VALUE else word


def _openings(data: dict[str, dict[str, Any]]) -> list[Alert]:
    found = []
    for label in _OPENINGS:
        entry = _entry(data, label)
        if entry is None or _opening(entry) is not True:
            continue
        is_boolean = label.endswith(" offen")
        text = label if is_boolean else f"{label}: {format_value(entry)}"
        found.append(Alert(f"offen:{label}", text))
    return found


def _lock(data: dict[str, dict[str, Any]], settings: AlertSettings) -> list[Alert]:
    entry = _entry(data, "Türschloss")
    value = _lock_value(entry)
    if value is None or value in {v.upper() for v in settings.locked_values}:
        return []
    return [Alert("nicht_verriegelt", f"Nicht verriegelt (Türschloss meldet {format_value(entry or {})})")]


def _below(data: dict[str, dict[str, Any]], label: str, limit: float, key: str, text: str) -> list[Alert]:
    value = _number(_entry(data, label))
    if value is None or value >= limit:
        return []
    return [Alert(key, f"{text}: {value:g} % (Grenze {limit:g} %)")]


def _kpa(entry: dict[str, Any] | None) -> float | None:
    return _number(entry) if entry and entry.get("unit") == "kPa" else None


def _tires(data: dict[str, dict[str, Any]], settings: AlertSettings) -> list[Alert]:
    found = []
    for position, _axle, _side in TIRES:
        pressure = _kpa(_entry(data, f"Reifendruck {position}"))
        target = _kpa(_entry(data, f"Solldruck {position}"))
        if pressure is None or target is None or pressure > target - settings.tire_tolerance_bar * 100 + 1e-9:
            continue
        text = f"Reifendruck {position}: {pressure / 100:.2f} bar, Soll {target / 100:.2f} bar"
        found.append(Alert(f"reifendruck:{position}", text))
    return found


def evaluate(data: dict[str, dict[str, Any]], settings: AlertSettings) -> tuple[Alert, ...]:
    """Alle Warnungen, die der Zustand gerade erfüllt (ohne Ereignisse wie "Laden beendet")."""
    return (
        *_openings(data),
        *_lock(data, settings),
        *_below(data, "Ladestand Hochvoltbatterie", settings.min_soc, "ladestand_niedrig", "Ladestand niedrig"),
        *_below(data, "12-V-Batterie", settings.min_12v, "batterie_12v_niedrig", "12-V-Batterie schwach"),
        *_tires(data, settings),
    )


def charging_status(data: dict[str, dict[str, Any]]) -> str | None:
    """Der Ladestatus; INVALID, UNKNOWN oder leer zählen als "kein Wert"."""
    return _lock_value(_entry(data, "Ladestatus"))


def is_charging(status: str | None) -> bool:
    return status in CHARGING_ACTIVE


def new_alerts(current: tuple[Alert, ...], previous: dict[str, Any], status: str | None) -> list[Alert]:
    """Was seit dem letzten Mal neu ist; "Laden beendet" beim Wechsel von Laden zu nicht Laden."""
    before = set(previous.get("aktiv") or [])
    fresh = [alert for alert in current if alert.key not in before]
    was_charging = is_charging(previous.get("ladestatus"))
    paused = status is not None and "PAUSE" in status  # eine Pause ist kein Ende
    if was_charging and status is not None and not is_charging(status) and not paused:
        fresh = [*fresh, Alert("laden_beendet", f"Laden beendet ({status})")]
    return fresh


def _evaluable(key: str, data: dict[str, dict[str, Any]]) -> bool | None:
    """Ob die Daten die Regel einer Warnung beurteilen können; None für unbekannte Schlüssel."""
    kind, _, detail = key.partition(":")
    if kind == "offen":
        return _opening(_entry(data, detail)) is not None if detail in _BY_LABEL else None
    if kind == "reifendruck":
        if f"Reifendruck {detail}" not in _BY_LABEL:
            return None
        return None not in (_kpa(_entry(data, f"Reifendruck {detail}")), _kpa(_entry(data, f"Solldruck {detail}")))
    checks = {
        "nicht_verriegelt": lambda: _lock_value(_entry(data, "Türschloss")) is not None,
        "ladestand_niedrig": lambda: _number(_entry(data, "Ladestand Hochvoltbatterie")) is not None,
        "batterie_12v_niedrig": lambda: _number(_entry(data, "12-V-Batterie")) is not None,
    }
    return checks[kind]() if kind in checks else None


def carried_over(previous_keys: list[str], data: dict[str, dict[str, Any]]) -> list[str]:
    """Bisher aktive Warnungen, die die Daten nicht beurteilen können (z. B. eine Live-Nachricht
    nur mit dem Reifendruck, ohne Solldruck): Sie bleiben aktiv, damit sie sich nicht erneut melden.
    Unbekannte Schlüssel (etwa aus älteren Versionen) fallen weg."""
    return [key for key in previous_keys if _evaluable(key, data) is False]
