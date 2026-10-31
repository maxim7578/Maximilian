"""Abläufe über mehrere API-Aufrufe: gültige Tokens, eigener Container, gemerktes Fahrzeug."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import httpx

from .api import ApiError, CarDataApi, RateLimitError
from .auth import refresh_tokens
from .config import ConfigError, validate_vin
from .descriptors import CONTAINER_NAME, CONTAINER_PURPOSE, all_descriptors, descriptor_signature
from .state import State, load_state, save_state

# Antworten, nach denen ein gemerktes Fahrzeug nicht mehr abrufbar sein könnte.
_STALE_VEHICLE = (400, 403, 404)


@dataclass(frozen=True)
class Session:
    api: CarDataApi
    state: State


def open_session(
    http: httpx.Client,
    state: State,
    path: Path,
    now: float,
    on_request: Callable[[], None] | None = None,
) -> Session:
    """Erneuert abgelaufene Tokens und speichert sie, bevor die API genutzt wird."""
    current = state
    if state.tokens.is_expired(now):
        current = state.with_tokens(refresh_tokens(http, state.client_id, state.tokens, now))
        save_state(path, current)
    return Session(CarDataApi(http, current.tokens.access_token, on_request), current)


def _ours(container: dict[str, object]) -> bool:
    return (
        container.get("name") == CONTAINER_NAME
        and container.get("purpose") == CONTAINER_PURPOSE
        and isinstance(container.get("containerId"), str)
    )


def _same_descriptors(container: dict[str, object], wanted: tuple[str, ...]) -> bool:
    descriptors = container.get("technicalDescriptors")
    return isinstance(descriptors, list) and set(descriptors) == set(wanted)


def _delete_quietly(session: Session, container_id: str) -> None:
    """Räumt einen veralteten eigenen Container auf; scheitert das, bleibt er eben liegen."""
    try:
        session.api.delete_container(container_id)
    except RateLimitError:
        raise
    except ApiError:
        pass


def ensure_container(session: Session, path: Path) -> Session:
    """Nutzt den gespeicherten Container, solange er zu den abgefragten Datenpunkten passt.

    Sonst wird ein eigener Container mit genau diesen Datenpunkten wiederverwendet oder
    neu angelegt; eigene Container mit anderen (oder unbekannten) Datenpunkten werden
    gelöscht, damit bei BMW keine veralteten liegen bleiben.
    """
    signature = descriptor_signature()
    if session.state.container_id and session.state.container_signature == signature:
        return session
    wanted = all_descriptors()
    ours = [c for c in session.api.containers() if _ours(c)]
    reusable = next((c for c in ours if _same_descriptors(c, wanted)), None)
    for container in ours:
        if container is not reusable:
            _delete_quietly(session, str(container["containerId"]))
    container_id = (
        str(reusable["containerId"])
        if reusable
        else session.api.create_container(CONTAINER_NAME, CONTAINER_PURPOSE, wanted)
    )
    return _with_state(session, session.state.with_container(container_id, signature), path)


def fetch_status(
    session: Session, vin: str, path: Path, recreate_container: bool = True
) -> dict[str, dict[str, object]]:
    """Holt Telematikdaten; ist der Container bei BMW verschwunden, einmal neu anlegen."""
    ready = ensure_container(session, path)
    try:
        return ready.api.telematic_data(vin, str(ready.state.container_id))
    except ApiError as err:
        if err.status not in (400, 404) or not recreate_container:
            raise
    fresh = ensure_container(Session(ready.api, ready.state.with_container(None)), path)
    return fresh.api.telematic_data(vin, str(fresh.state.container_id))


def _with_state(session: Session, state: State, path: Path) -> Session:
    save_state(path, state)
    return Session(session.api, state)


def resolve_vin(
    session: Session, vin: str | None, choose: Callable[[list[str]], str], path: Path
) -> tuple[Session, str]:
    """Angegebene, sonst gemerkte Fahrgestellnummer; erst danach die Fahrzeugliste (1 Abruf)."""
    if vin:
        return session, vin
    if session.state.vin:
        return session, session.state.vin
    vins = session.api.vehicles()
    if not vins:
        raise ApiError("Unter diesem Konto ist kein Fahrzeug als Hauptnutzer eingetragen.", 404)
    chosen = validate_vin(choose(vins))
    return _with_state(session, session.state.with_vin(chosen), path), chosen


def remember_vehicles(session: Session, vins: list[str], path: Path) -> Session:
    """Merkt sich das Fahrzeug, wenn das Konto genau eines hat; sonst nichts."""
    try:
        wanted = validate_vin(vins[0]) if len(vins) == 1 else None
    except ConfigError:
        wanted = None
    if wanted == session.state.vin:
        return session
    return _with_state(session, session.state.with_vin(wanted), path)


def fetch_vehicle_status(
    session: Session, vin: str | None, choose: Callable[[list[str]], str], path: Path
) -> tuple[str, dict[str, dict[str, object]]]:
    """Status des angegebenen, gemerkten oder einzigen Fahrzeugs.

    Scheitert der Abruf mit einer gemerkten Fahrgestellnummer (z. B. Fahrzeug verkauft),
    wird sie vergessen und einmal über die aktuelle Fahrzeugliste neu bestimmt; erst
    dann wird ein verschwundener Container neu angelegt.
    """
    remembered = vin is None and session.state.vin is not None
    session, chosen = resolve_vin(session, vin, choose, path)
    if not remembered:
        return chosen, fetch_status(session, chosen, path)
    try:
        return chosen, fetch_status(session, chosen, path, recreate_container=False)
    except ApiError as err:
        if err.status not in _STALE_VEHICLE:
            raise
    # Neu laden: ensure_container kann inzwischen eine Container-ID gespeichert haben.
    forgotten = _with_state(session, load_state(path).with_vin(None), path)
    fresh, chosen = resolve_vin(forgotten, None, choose, path)
    return chosen, fetch_status(fresh, chosen, path)
