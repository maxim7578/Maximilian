"""Feste Adressen der BMW CarData API und Einlesen der Konfiguration."""

from __future__ import annotations

import os
import re
from collections.abc import Mapping
from pathlib import Path

DEVICE_CODE_URL = "https://customer.bmwgroup.com/gcdm/oauth/device/code"
TOKEN_URL = "https://customer.bmwgroup.com/gcdm/oauth/token"
API_BASE_URL = "https://api-cardata.bmwgroup.com"
API_VERSION = "v1"

# Lesender API-Zugriff und der Datenstrom (MQTT); ohne Stream-Freigabe im Portal: API_ONLY_SCOPE.
STREAMING_SCOPE = "cardata:streaming:read"
API_ONLY_SCOPE = "authenticate_user openid cardata:api:read"
DEFAULT_SCOPE = f"{API_ONLY_SCOPE} {STREAMING_SCOPE}"

CLIENT_ID_ENV = "BMW_CARDATA_CLIENT_ID"
STATE_PATH_ENV = "BMW_CARDATA_STATE"
DEFAULT_STATE_PATH = "~/.config/bmw-cardata/state.json"

# Verlauf: Aufbewahrungsfrist in Tagen (0 = unbegrenzt) und Position nicht speichern.
HISTORY_DAYS_ENV = "BMW_CARDATA_HISTORY_DAYS"
NO_LOCATION_ENV = "BMW_CARDATA_NO_LOCATION"
DEFAULT_HISTORY_DAYS = 365
MAX_HISTORY_DAYS = 3650
_YES = frozenset({"1", "ja", "j", "true", "yes", "y", "on"})

HTTP_TIMEOUT_SECONDS = 30.0

_CLIENT_ID_PATTERN = re.compile(r"^[A-Za-z0-9-]{8,64}$")
_VIN_PATTERN = re.compile(r"^[A-HJ-NPR-Z0-9]{17}$")


class ConfigError(Exception):
    """Fehlende oder ungültige Konfiguration."""


def validate_client_id(raw: str | None) -> str:
    """Prüft eine Client-ID aus dem BMW-Portal und gibt sie bereinigt zurück."""
    client_id = (raw or "").strip()
    if not client_id:
        raise ConfigError(
            f"Keine Client-ID angegeben. Setze {CLIENT_ID_ENV} oder nutze --client-id."
        )
    if not _CLIENT_ID_PATTERN.fullmatch(client_id):
        raise ConfigError("Die Client-ID hat ein ungültiges Format.")
    return client_id


def client_id_from_env(env: Mapping[str, str] | None = None) -> str:
    source = os.environ if env is None else env
    return validate_client_id(source.get(CLIENT_ID_ENV))


def validate_vin(raw: str) -> str:
    """Prüft eine Fahrgestellnummer (17 Zeichen, ohne I, O und Q)."""
    vin = raw.strip().upper()
    if not _VIN_PATTERN.fullmatch(vin):
        raise ConfigError(f"Ungültige Fahrgestellnummer: {raw!r}")
    return vin


def state_path(explicit: str | None = None, env: Mapping[str, str] | None = None) -> Path:
    source = os.environ if env is None else env
    raw = explicit or source.get(STATE_PATH_ENV) or DEFAULT_STATE_PATH
    return Path(raw).expanduser()


def parse_history_days(raw: str) -> int:
    """Prüft eine Aufbewahrungsfrist in Tagen: ganze Zahl von 0 (unbegrenzt) bis 3650."""
    text = raw.strip()
    days = int(text) if text.isascii() and text.isdigit() and len(text) <= 4 else -1
    if not 0 <= days <= MAX_HISTORY_DAYS:
        raise ConfigError(
            f"Die Aufbewahrungsfrist muss eine ganze Zahl von 0 (unbegrenzt) bis {MAX_HISTORY_DAYS} Tage sein."
        )
    return days


def history_days(explicit: int | None = None, env: Mapping[str, str] | None = None) -> int:
    """Frist für den Verlauf: Option vor Umgebungsvariable vor Standard (365 Tage)."""
    if explicit is not None:
        return explicit
    source = os.environ if env is None else env
    raw = source.get(HISTORY_DAYS_ENV)
    if raw is None:
        return DEFAULT_HISTORY_DAYS
    try:
        return parse_history_days(raw)
    except ConfigError as error:
        raise ConfigError(f"{HISTORY_DAYS_ENV}: {error}") from None


def location_disabled(explicit: bool = False, env: Mapping[str, str] | None = None) -> bool:
    """True, wenn die Position nicht im Verlauf landen soll (Option oder Umgebungsvariable)."""
    source = os.environ if env is None else env
    return explicit or source.get(NO_LOCATION_ENV, "").strip().lower() in _YES
