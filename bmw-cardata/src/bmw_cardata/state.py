"""Speichert Client-ID, Tokens, Container-ID und Fahrgestellnummer lokal (Dateirechte 600)."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, replace
from pathlib import Path

from .auth import Tokens
from .config import ConfigError, validate_vin
from .files import write_private


class StateError(Exception):
    """Gespeicherter Zustand fehlt oder ist beschädigt."""


@dataclass(frozen=True)
class State:
    client_id: str
    tokens: Tokens
    container_id: str | None = None
    vin: str | None = None  # gemerkt, solange das Konto genau ein Fahrzeug hat
    container_signature: str | None = None  # Datenpunkte, mit denen der Container angelegt wurde  # gemerkt, solange das Konto genau ein Fahrzeug hat

    def with_tokens(self, tokens: Tokens) -> State:
        return replace(self, tokens=tokens)

    def with_container(self, container_id: str | None, signature: str | None = None) -> State:
        return replace(self, container_id=container_id, container_signature=signature)

    def with_vin(self, vin: str | None) -> State:
        return replace(self, vin=vin)


def _optional_vin(raw: object) -> str | None:
    if raw is None:
        return None
    if not isinstance(raw, str):
        raise TypeError("vin")
    return validate_vin(raw)


def _optional_text(raw: object) -> str | None:
    if raw is not None and not isinstance(raw, str):
        raise TypeError("container_id")
    return raw


def load_state(path: Path) -> State:
    if not path.exists():
        raise StateError("Nicht angemeldet. Bitte zuerst 'bmw-cardata anmelden' ausführen.")
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        return State(
            client_id=str(raw["client_id"]),
            tokens=Tokens(**raw["tokens"]),
            container_id=_optional_text(raw.get("container_id")),
            vin=_optional_vin(raw.get("vin")),
            container_signature=_optional_text(raw.get("container_signature")),
        )
    except (OSError, ValueError, KeyError, TypeError, ConfigError) as err:
        raise StateError(f"Gespeicherte Anmeldung in {path} ist beschädigt.") from err


def save_state(path: Path, state: State) -> None:
    """Schreibt atomar und nur für den eigenen Benutzer lesbar."""
    write_private(path, json.dumps(asdict(state), indent=2))


def delete_state(path: Path) -> bool:
    if path.exists():
        path.unlink()
        return True
    return False
