"""Datencontainer bei BMW: anlegen, wiederverwenden und den eigenen alten aufräumen.

Grundsätze, damit ein Update nie einen funktionierenden Zustand zerstört:
- Erst wird der neue Container angelegt, dann der alte gelöscht.
- Gelöscht wird nur der Container, den diese Installation selbst gespeichert hat; Container
  anderer Installationen (gleicher Name, anderer Rechner) bleiben unberührt.
- Lehnt BMW den neuen Container ab, bleibt der alte bis zum nächsten Tag in Gebrauch.
"""

from __future__ import annotations

from dataclasses import dataclass

from .api import CONTAINER_GONE, ApiError, CarDataApi, RateLimitError
from .descriptors import (
    CONTAINER_NAME,
    CONTAINER_PURPOSE,
    SERVICE_CONTAINER_NAME,
    SERVICE_CONTAINER_PURPOSE,
    SERVICE_DESCRIPTORS,
    descriptor_signature,
    polled_descriptors,
)


@dataclass(frozen=True)
class ContainerSpec:
    name: str
    purpose: str
    descriptors: tuple[str, ...]


@dataclass(frozen=True)
class ContainerChoice:
    container_id: str
    signature: str  # zu speichern; "aufgeschoben:…" nach einer Ablehnung durch BMW
    note: str | None = None


STATUS_CONTAINER = ContainerSpec(CONTAINER_NAME, CONTAINER_PURPOSE, polled_descriptors())
SERVICE_CONTAINER = ContainerSpec(SERVICE_CONTAINER_NAME, SERVICE_CONTAINER_PURPOSE, SERVICE_DESCRIPTORS)


def container_gone(err: ApiError) -> bool:
    """BMW kennt den Container nicht mehr (gelöscht oder entkoppelt)."""
    return err.status == 404 or err.code == CONTAINER_GONE


def _deferred(signature: str, today: str) -> str:
    return f"aufgeschoben:{signature}:{today}"


def _reusable(api: CarDataApi, spec: ContainerSpec) -> str | None:
    """Ein vorhandener Container mit genau diesem Namen, Zweck und diesen Datenpunkten."""
    for container in api.containers():
        descriptors = container.get("technicalDescriptors")
        container_id = container.get("containerId")
        if (
            container.get("name") == spec.name
            and container.get("purpose") == spec.purpose
            and isinstance(descriptors, list)
            and set(descriptors) == set(spec.descriptors)
            and isinstance(container_id, str)
        ):
            return container_id
    return None


def _delete_quietly(api: CarDataApi, container_id: str) -> None:
    """Aufräumen ist Nebensache: scheitert es (auch am Tageslimit), bleibt der Container liegen."""
    try:
        api.delete_container(container_id)
    except ApiError:
        pass


def provide_container(
    api: CarDataApi, spec: ContainerSpec, stored_id: str | None, stored_signature: str | None, today: str
) -> ContainerChoice:
    signature = descriptor_signature(spec.descriptors)
    if stored_id and stored_signature in (signature, _deferred(signature, today)):
        return ContainerChoice(stored_id, str(stored_signature))
    new_id = _reusable(api, spec)
    if new_id is None:
        try:
            new_id = api.create_container(spec.name, spec.purpose, spec.descriptors)
        except RateLimitError:
            raise
        except ApiError:
            if not stored_id:
                raise
            note = "BMW hat den Container mit den neuen Datenpunkten abgelehnt; bis morgen gilt der bisherige."
            return ContainerChoice(stored_id, _deferred(signature, today), note)
    if stored_id and stored_id != new_id:
        _delete_quietly(api, stored_id)
    return ContainerChoice(new_id, signature)
