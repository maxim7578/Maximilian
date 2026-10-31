"""Abläufe über mehrere API-Aufrufe: gültige Tokens, eigener Container, gemerktes Fahrzeug."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import httpx

from .api import ApiError, CarDataApi
from .auth import refresh_tokens
from .config import ConfigError, validate_vin
from .containers import STATUS_CONTAINER, container_gone, provide_container
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


def _today() -> str:
    return date.today().isoformat()


def ensure_container(session: Session, path: Path, today: str | None = None) -> tuple[Session, str | None]:
    """Der Status-Container für die abgefragten Datenpunkte, samt Hinweis, falls BMW ablehnt."""
    state = session.state
    choice = provide_container(
        session.api, STATUS_CONTAINER, state.container_id, state.container_signature, today or _today()
    )
    if (choice.container_id, choice.signature) == (state.container_id, state.container_signature):
        return session, choice.note
    return _with_state(session, state.with_container(choice.container_id, choice.signature), path), choice.note


@dataclass(frozen=True)
class Fetched:
    data: dict[str, dict[str, object]]
    notes: tuple[str, ...] = ()


def fetch_status(session: Session, vin: str, path: Path, recreate_container: bool = True) -> Fetched:
    """Holt Telematikdaten; ist der Container bei BMW verschwunden, einmal neu anlegen.

    Andere Fehler (etwa HTTP 400) legen keinen neuen Container an: Das würde bei jedem
    Aufruf Abrufe kosten, ohne die Ursache zu beheben.
    """
    ready, note = ensure_container(session, path)
    notes = (note,) if note else ()
    try:
        return Fetched(ready.api.telematic_data(vin, str(ready.state.container_id)), notes)
    except ApiError as err:
        if not container_gone(err) or not recreate_container:
            raise
    fresh, note = ensure_container(Session(ready.api, ready.state.with_container(None)), path)
    return Fetched(fresh.api.telematic_data(vin, str(fresh.state.container_id)), (*notes, *((note,) if note else ())))


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


@dataclass(frozen=True)
class StatusResult:
    vin: str
    data: dict[str, dict[str, object]]
    notes: tuple[str, ...] = ()


def _result(vin: str, fetched: Fetched) -> StatusResult:
    return StatusResult(vin, fetched.data, fetched.notes)


def fetch_vehicle_status(
    session: Session, vin: str | None, choose: Callable[[list[str]], str], path: Path
) -> StatusResult:
    """Status des angegebenen, gemerkten oder einzigen Fahrzeugs.

    Scheitert der Abruf mit einer gemerkten Fahrgestellnummer (z. B. Fahrzeug verkauft),
    wird sie vergessen und einmal über die aktuelle Fahrzeugliste neu bestimmt; erst
    dann wird ein verschwundener Container neu angelegt.
    """
    remembered = vin is None and session.state.vin is not None
    session, chosen = resolve_vin(session, vin, choose, path)
    if not remembered:
        return _result(chosen, fetch_status(session, chosen, path))
    try:
        return _result(chosen, fetch_status(session, chosen, path, recreate_container=False))
    except ApiError as err:
        if err.status not in _STALE_VEHICLE:
            raise
    # Neu laden: ensure_container kann inzwischen eine Container-ID gespeichert haben.
    forgotten = _with_state(session, load_state(path).with_vin(None), path)
    fresh, chosen = resolve_vin(forgotten, None, choose, path)
    return _result(chosen, fetch_status(fresh, chosen, path))
