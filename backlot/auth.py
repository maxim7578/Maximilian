"""Zugriffsschutz für den Backlot-Server (Befund N12).

Der Server lauscht nur auf 127.0.0.1, aber andere Benutzer desselben Rechners
erreichen ihn trotzdem. Deshalb braucht jede Anfrage ein zufälliges Token:

- ``?token=…`` in der URL (aus ``python -m backlot open``) setzt ein Cookie
  (HttpOnly, SameSite=Strict) und leitet auf dieselbe URL ohne Token um, damit
  das Token nicht in Verlauf, Lesezeichen oder Referer landet;
- danach reicht das Cookie – auch für SSE, ``<img>``/``<video>`` und Range-Anfragen;
- Skripte schicken ``Authorization: Bearer …`` oder ``X-Backlot-Token: …``.

Nur ``/api/health`` antwortet ohne Token (ohne Projektdaten), damit Skripte
prüfen können, ob der Server läuft.
"""

from __future__ import annotations

import os
import re
import secrets
from http.cookies import SimpleCookie
from pathlib import Path
from typing import Iterable, Optional
from urllib.parse import unquote

TOKEN_ENV = "BACKLOT_TOKEN"
TOKEN_HEADER = "X-Backlot-Token"
TOKEN_QUERY = "token"
MIN_TOKEN_LENGTH = 16
COOKIE_MAX_AGE = 30 * 24 * 3600
PUBLIC_PATHS = frozenset({"/api/health"})
_TOKEN_PATTERN = re.compile(rf"[A-Za-z0-9._~-]{{{MIN_TOKEN_LENGTH},}}")

# Token-Dateien (eine pro Port, Modus 0600), damit ``backlot open`` und Skripte
# das Token eines schon laufenden Servers finden. ``.backlot/`` ist gitignored.
TOKEN_DIR = Path(__file__).resolve().parent.parent / ".backlot" / "auth"

UNAUTHORIZED_MESSAGE = (
    "Backlot: token required. Open the board with `python -m backlot open` "
    "and use the printed URL (it contains ?token=...).\n"
)


def new_token() -> str:
    return secrets.token_urlsafe(32)


def validate_token(token: str) -> str:
    # Nur URL- und Cookie-sichere Zeichen (wie secrets.token_urlsafe), mindestens 16.
    if not isinstance(token, str) or not _TOKEN_PATTERN.fullmatch(token):
        raise ValueError(
            f"Backlot token must be at least {MIN_TOKEN_LENGTH} characters of A-Z a-z 0-9 . _ ~ -"
        )
    return token


def cookie_name(port: Optional[int]) -> str:
    # Cookies trennen nicht nach Port: Ohne Port im Namen würden sich zwei
    # Backlot-Server auf 127.0.0.1 gegenseitig das Cookie überschreiben.
    return f"backlot_token_{port}" if port else "backlot_token"


def auth_headers(token: str) -> dict[str, str]:
    return {TOKEN_HEADER: token}


def url_with_token(url: str, token: str) -> str:
    separator = "&" if "?" in url else "?"
    return f"{url}{separator}{TOKEN_QUERY}={token}"


# ---- Token-Datei ---------------------------------------------------------


def token_file(port: int) -> Path:
    return TOKEN_DIR / f"token-{port}"


def write_token_file(port: int, token: str) -> Path:
    TOKEN_DIR.mkdir(parents=True, exist_ok=True)
    if os.name == "posix":
        TOKEN_DIR.chmod(0o700)
    path = token_file(port)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        if os.name == "posix":
            os.fchmod(fd, 0o600)  # bestehende Datei mit lockereren Rechten
        os.write(fd, token.encode("utf-8"))
    finally:
        os.close(fd)
    return path


def read_token_file(port: int) -> Optional[str]:
    try:
        token = token_file(port).read_text(encoding="utf-8").strip()
    except OSError:
        return None
    return token or None


def remove_token_file(port: int, token: str) -> None:
    """Token-Datei löschen, aber nur, wenn sie noch zu diesem Server gehört."""
    if read_token_file(port) == token:
        try:
            token_file(port).unlink()
        except OSError:
            pass


def resolve_token(port: int, *, prefer_file: bool) -> Optional[str]:
    """Token aus ``BACKLOT_TOKEN`` oder (für laufende Server) aus der Token-Datei."""
    env_token = os.environ.get(TOKEN_ENV)
    if env_token:
        return env_token
    return read_token_file(port) if prefer_file else None


# ---- ASGI-Middleware -----------------------------------------------------


class TokenAuthMiddleware:
    """Lässt nur Anfragen mit gültigem Token durch (Cookie, Header oder ?token=)."""

    def __init__(self, app, token: str) -> None:
        self.app = app
        self._token = validate_token(token).encode("utf-8")

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http" or scope.get("path") in PUBLIC_PATHS:
            await self.app(scope, receive, send)
            return

        name = cookie_name(_server_port(scope))
        query_parts = _split_query(scope.get("query_string", b""))
        query_tokens = [value for key, _part, value in query_parts if key == TOKEN_QUERY]
        if query_tokens:
            if len(query_tokens) == 1 and self._matches(query_tokens[0]):
                await _redirect_with_cookie(scope, send, query_parts, name, query_tokens[0])
            else:
                await _unauthorized(send)
            return

        if self._matches(_header_token(scope)) or self._matches(_cookie(scope, name)):
            await self.app(scope, receive, send)
            return
        await _unauthorized(send)

    def _matches(self, candidate: Optional[str]) -> bool:
        if not candidate:
            return False
        return secrets.compare_digest(candidate.encode("utf-8"), self._token)


def _server_port(scope) -> Optional[int]:
    server = scope.get("server")
    if server and len(server) > 1 and server[1]:
        return int(server[1])
    return None


def _headers(scope) -> Iterable[tuple[str, str]]:
    for key, value in scope.get("headers", []):
        yield key.decode("latin-1").lower(), value.decode("latin-1")


def _header_token(scope) -> Optional[str]:
    for key, value in _headers(scope):
        if key == TOKEN_HEADER.lower():
            return value.strip()
        if key == "authorization":
            scheme, _, credentials = value.partition(" ")
            if scheme.lower() == "bearer":
                return credentials.strip()
    return None


def _cookie(scope, name: str) -> Optional[str]:
    for key, value in _headers(scope):
        if key != "cookie":
            continue
        jar = SimpleCookie()
        try:
            jar.load(value)
        except Exception:
            continue
        if name in jar:
            return jar[name].value
    return None


def _split_query(raw: bytes) -> list[tuple[str, bytes, str]]:
    """Query in (Schlüssel, Rohteil, Wert) zerlegen; die Rohteile bleiben unverändert."""
    parts = []
    for part in raw.split(b"&"):
        if part:
            key, _, value = part.decode("latin-1").partition("=")
            parts.append((unquote(key), part, unquote(value)))
    return parts


async def _redirect_with_cookie(scope, send, query_parts, name: str, token: str) -> None:
    # raw_path behält Kodierungen wie %2F, damit die Umleitung genau dieselbe Seite trifft.
    path = (scope.get("raw_path") or scope["path"].encode("utf-8")).decode("latin-1")
    rest = b"&".join(part for key, part, _value in query_parts if key != TOKEN_QUERY).decode("latin-1")
    location = f"{path}?{rest}" if rest else path
    cookie = f"{name}={token}; Path=/; Max-Age={COOKIE_MAX_AGE}; HttpOnly; SameSite=Strict"
    await send({
        "type": "http.response.start",
        "status": 303,
        "headers": [
            (b"location", location.encode("latin-1")),
            (b"set-cookie", cookie.encode("latin-1")),
            (b"cache-control", b"no-store"),
            (b"referrer-policy", b"no-referrer"),
            (b"content-length", b"0"),
        ],
    })
    await send({"type": "http.response.body", "body": b""})


async def _unauthorized(send) -> None:
    body = UNAUTHORIZED_MESSAGE.encode("utf-8")
    await send({
        "type": "http.response.start",
        "status": 401,
        "headers": [
            (b"content-type", b"text/plain; charset=utf-8"),
            (b"content-length", str(len(body)).encode("ascii")),
            (b"cache-control", b"no-store"),
        ],
    })
    await send({"type": "http.response.body", "body": body})
