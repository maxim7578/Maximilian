"""Abläufe über mehrere API-Aufrufe: gültige Tokens und eigener Container."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import httpx

from .api import ApiError, CarDataApi
from .auth import refresh_tokens
from .descriptors import CONTAINER_NAME, CONTAINER_PURPOSE, all_descriptors
from .state import State, save_state


@dataclass(frozen=True)
class Session:
    api: CarDataApi
    state: State


def open_session(http: httpx.Client, state: State, path: Path, now: float) -> Session:
    """Erneuert abgelaufene Tokens und speichert sie, bevor die API genutzt wird."""
    current = state
    if state.tokens.is_expired(now):
        current = state.with_tokens(refresh_tokens(http, state.client_id, state.tokens, now))
        save_state(path, current)
    return Session(CarDataApi(http, current.tokens.access_token), current)


def _matches(container: dict[str, object], wanted: tuple[str, ...]) -> bool:
    descriptors = container.get("technicalDescriptors")
    same_set = not isinstance(descriptors, list) or set(descriptors) == set(wanted)
    return (
        container.get("name") == CONTAINER_NAME
        and container.get("purpose") == CONTAINER_PURPOSE
        and same_set
        and isinstance(container.get("containerId"), str)
    )


def ensure_container(session: Session, path: Path) -> Session:
    """Nutzt die gespeicherte Container-ID oder sucht bzw. legt den Container an."""
    if session.state.container_id:
        return session
    wanted = all_descriptors()
    existing = next((c for c in session.api.containers() if _matches(c, wanted)), None)
    container_id = (
        str(existing["containerId"])
        if existing
        else session.api.create_container(CONTAINER_NAME, CONTAINER_PURPOSE, wanted)
    )
    state = session.state.with_container(container_id)
    save_state(path, state)
    return Session(session.api, state)


def fetch_status(session: Session, vin: str, path: Path) -> dict[str, dict[str, object]]:
    """Holt Telematikdaten; ist der Container bei BMW verschwunden, einmal neu anlegen."""
    ready = ensure_container(session, path)
    try:
        return ready.api.telematic_data(vin, str(ready.state.container_id))
    except ApiError as err:
        if err.status not in (400, 404):
            raise
    fresh = ensure_container(Session(ready.api, ready.state.with_container(None)), path)
    return fresh.api.telematic_data(vin, str(fresh.state.container_id))


def resolve_vin(session: Session, vin: str | None, choose: Callable[[list[str]], str]) -> str:
    if vin:
        return vin
    vins = session.api.vehicles()
    if not vins:
        raise ApiError("Unter diesem Konto ist kein Fahrzeug als Hauptnutzer eingetragen.", 404)
    return choose(vins)
