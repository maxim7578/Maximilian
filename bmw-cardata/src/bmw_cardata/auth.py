"""Anmeldung per OAuth 2.0 Gerätecode (RFC 8628) mit PKCE bei BMW."""

from __future__ import annotations

import base64
import hashlib
import secrets
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import httpx

from .config import DEFAULT_SCOPE, DEVICE_CODE_URL, TOKEN_URL

DEVICE_GRANT = "urn:ietf:params:oauth:grant-type:device_code"
_SECRET_KEYS = frozenset({"access_token", "refresh_token", "id_token"})


class AuthError(Exception):
    """BMW hat eine Anmeldeanfrage abgelehnt."""


@dataclass(frozen=True)
class Tokens:
    access_token: str
    refresh_token: str
    expires_at: float
    scope: str = ""

    def is_expired(self, now: float, margin: float = 60.0) -> bool:
        return now >= self.expires_at - margin

    @classmethod
    def from_response(cls, data: dict[str, Any], now: float, fallback_refresh: str = "") -> Tokens:
        access = data.get("access_token")
        refresh = data.get("refresh_token") or fallback_refresh
        if not isinstance(access, str) or not access or not isinstance(refresh, str) or not refresh:
            raise AuthError("Die Token-Antwort von BMW ist unvollständig.")
        expires_in = data.get("expires_in")
        lifetime = float(expires_in) if isinstance(expires_in, (int, float)) else 3600.0
        return cls(access, refresh, now + lifetime, str(data.get("scope") or ""))


@dataclass(frozen=True)
class DeviceCode:
    device_code: str
    user_code: str
    verification_uri: str
    verification_uri_complete: str
    expires_in: int
    interval: int


def create_pkce_pair() -> tuple[str, str]:
    """Erzeugt Verifier und S256-Challenge für PKCE."""
    verifier = secrets.token_urlsafe(64)
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return verifier, challenge


def _safe_json(response: httpx.Response) -> dict[str, Any]:
    try:
        data = response.json()
    except ValueError:
        return {}
    return data if isinstance(data, dict) else {}


def _redacted(data: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in data.items() if key not in _SECRET_KEYS}


def request_device_code(
    http: httpx.Client, client_id: str, code_challenge: str, scope: str = DEFAULT_SCOPE
) -> DeviceCode:
    response = http.post(
        DEVICE_CODE_URL,
        data={
            "client_id": client_id,
            "scope": scope,
            "response_type": "device_code",
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        },
    )
    data = _safe_json(response)
    if response.status_code != 200:
        raise AuthError(f"Gerätecode abgelehnt (HTTP {response.status_code}): {_redacted(data)}")
    try:
        return DeviceCode(
            device_code=str(data["device_code"]),
            user_code=str(data["user_code"]),
            verification_uri=str(data["verification_uri"]),
            verification_uri_complete=str(data.get("verification_uri_complete") or ""),
            expires_in=int(data.get("expires_in") or 900),
            interval=int(data.get("interval") or 5),
        )
    except (KeyError, TypeError, ValueError) as err:
        raise AuthError("Die Gerätecode-Antwort von BMW ist unvollständig.") from err


def poll_for_tokens(
    http: httpx.Client,
    client_id: str,
    device: DeviceCode,
    code_verifier: str,
    sleep: Callable[[float], None] = time.sleep,
    clock: Callable[[], float] = time.monotonic,
    wall_clock: Callable[[], float] = time.time,
) -> Tokens:
    """Fragt BMW ab, bis die Anmeldung im Browser bestätigt wurde."""
    payload = {
        "client_id": client_id,
        "grant_type": DEVICE_GRANT,
        "device_code": device.device_code,
        "code_verifier": code_verifier,
    }
    deadline = clock() + device.expires_in
    interval = device.interval
    while clock() < deadline:
        response = http.post(TOKEN_URL, data=payload)
        data = _safe_json(response)
        if response.status_code == 200:
            return Tokens.from_response(data, wall_clock())
        error = data.get("error")
        if error == "slow_down":
            interval += 5
        elif error != "authorization_pending":
            raise AuthError(f"Anmeldung fehlgeschlagen (HTTP {response.status_code}): {_redacted(data)}")
        sleep(interval)
    raise AuthError("Zeit abgelaufen: Die Anmeldung wurde nicht rechtzeitig bestätigt.")


def refresh_tokens(
    http: httpx.Client, client_id: str, tokens: Tokens, now: float
) -> Tokens:
    response = http.post(
        TOKEN_URL,
        data={
            "client_id": client_id,
            "grant_type": "refresh_token",
            "refresh_token": tokens.refresh_token,
        },
    )
    data = _safe_json(response)
    if response.status_code != 200:
        raise AuthError(
            f"Token-Erneuerung fehlgeschlagen (HTTP {response.status_code}). "
            "Bitte erneut mit 'bmw-cardata anmelden' anmelden."
        )
    return Tokens.from_response(data, now, fallback_refresh=tokens.refresh_token)
