"""Lesender Zugriff auf die REST-Endpunkte der BMW CarData API."""

from __future__ import annotations

from typing import Any

import httpx

from .config import API_BASE_URL, API_VERSION, validate_vin


class ApiError(Exception):
    def __init__(self, message: str, status: int) -> None:
        super().__init__(message)
        self.status = status


class RateLimitError(ApiError):
    """BMW erlaubt nur eine begrenzte Zahl von Abrufen pro Tag."""


def _items(payload: Any, *keys: str) -> list[dict[str, Any]]:
    if isinstance(payload, dict):
        payload = next((payload[k] for k in keys if isinstance(payload.get(k), list)), [])
    if not isinstance(payload, list):
        return []
    return [item for item in payload if isinstance(item, dict)]


class CarDataApi:
    def __init__(self, http: httpx.Client, access_token: str) -> None:
        self._http = http
        self._headers = {
            "Authorization": f"Bearer {access_token}",
            "x-version": API_VERSION,
            "Accept": "application/json",
        }

    def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        response = self._http.request(method, f"{API_BASE_URL}{path}", headers=self._headers, **kwargs)
        status = response.status_code
        if status == 429:
            raise RateLimitError(
                "Tageslimit der BMW CarData API erreicht (50 Abrufe pro Tag). Bitte später erneut versuchen.",
                status,
            )
        if status in (401, 403):
            raise ApiError(
                f"Zugriff verweigert (HTTP {status}). Ist der CarData-API-Zugriff im BMW-Portal freigeschaltet?",
                status,
            )
        if status >= 400:
            raise ApiError(f"BMW CarData API meldet HTTP {status} für {path.split('/')[2]}.", status)
        if not response.content:
            return None
        try:
            return response.json()
        except ValueError as err:
            raise ApiError("Antwort der BMW CarData API ist kein gültiges JSON.", status) from err

    def vehicles(self) -> list[str]:
        """Fahrgestellnummern der Fahrzeuge, bei denen du Hauptnutzer bist."""
        payload = self._request("GET", "/customers/vehicles/mappings")
        vins = []
        for mapping in _items(payload, "mappings", "vehicles"):
            mapping_type = mapping.get("mappingType")
            vin = mapping.get("vin")
            if isinstance(vin, str) and str(mapping_type or "PRIMARY").upper() == "PRIMARY":
                vins.append(vin)
        return vins

    def basic_data(self, vin: str) -> dict[str, Any]:
        payload = self._request("GET", f"/customers/vehicles/{validate_vin(vin)}/basicData")
        return payload if isinstance(payload, dict) else {}

    def containers(self) -> list[dict[str, Any]]:
        return _items(self._request("GET", "/customers/containers"), "containers", "items")

    def create_container(self, name: str, purpose: str, descriptors: tuple[str, ...]) -> str:
        payload = self._request(
            "POST",
            "/customers/containers",
            json={"name": name, "purpose": purpose, "technicalDescriptors": list(descriptors)},
        )
        container_id = payload.get("containerId") if isinstance(payload, dict) else None
        if not isinstance(container_id, str) or not container_id:
            raise ApiError("BMW hat keine Container-ID zurückgegeben.", 200)
        return container_id

    def telematic_data(self, vin: str, container_id: str) -> dict[str, dict[str, Any]]:
        payload = self._request(
            "GET",
            f"/customers/vehicles/{validate_vin(vin)}/telematicData",
            params={"containerId": container_id},
        )
        data = payload.get("telematicData") if isinstance(payload, dict) else None
        if not isinstance(data, dict):
            return {}
        return {key: value for key, value in data.items() if isinstance(value, dict)}
