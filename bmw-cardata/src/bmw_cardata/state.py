"""Speichert Client-ID, Tokens und Container-ID lokal (Dateirechte 600)."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, replace
from pathlib import Path

from .auth import Tokens


class StateError(Exception):
    """Gespeicherter Zustand fehlt oder ist beschädigt."""


@dataclass(frozen=True)
class State:
    client_id: str
    tokens: Tokens
    container_id: str | None = None

    def with_tokens(self, tokens: Tokens) -> State:
        return replace(self, tokens=tokens)

    def with_container(self, container_id: str | None) -> State:
        return replace(self, container_id=container_id)


def load_state(path: Path) -> State:
    if not path.exists():
        raise StateError("Nicht angemeldet. Bitte zuerst 'bmw-cardata anmelden' ausführen.")
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        return State(
            client_id=str(raw["client_id"]),
            tokens=Tokens(**raw["tokens"]),
            container_id=raw.get("container_id"),
        )
    except (OSError, ValueError, KeyError, TypeError) as err:
        raise StateError(f"Gespeicherte Anmeldung in {path} ist beschädigt.") from err


def save_state(path: Path, state: State) -> None:
    """Schreibt atomar und nur für den eigenen Benutzer lesbar."""
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    tmp = path.with_name(path.name + ".tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        json.dump(asdict(state), handle, indent=2)
    os.replace(tmp, path)


def delete_state(path: Path) -> bool:
    if path.exists():
        path.unlink()
        return True
    return False
