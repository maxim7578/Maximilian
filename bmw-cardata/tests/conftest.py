"""Gemeinsame Hilfen: simulierter BMW-Server ohne echte Netzwerkzugriffe."""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

import httpx
import pytest

from bmw_cardata.auth import Tokens
from bmw_cardata.state import State

VIN = "WBA12345678901234"
VIN2 = "WBY98765432109876"


@dataclass
class FakeBmw:
    """Beantwortet Anfragen der Reihe nach je (Methode, Pfad) und protokolliert sie."""

    routes: dict[tuple[str, str], list[httpx.Response]] = field(default_factory=dict)
    requests: list[httpx.Request] = field(default_factory=list)

    def add(self, method: str, path: str, status: int = 200, body: Any = None, raw: bytes | None = None) -> None:
        content = raw if raw is not None else (b"" if body is None else json.dumps(body).encode())
        self.routes.setdefault((method, path), []).append(httpx.Response(status, content=content))

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        queue = self.routes.get((request.method, request.url.path))
        if not queue:
            return httpx.Response(599, content=b"unerwartete Anfrage")
        return queue.pop(0) if len(queue) > 1 else queue[0]

    def client(self) -> httpx.Client:
        return httpx.Client(transport=httpx.MockTransport(self.handler))

    def form(self, index: int) -> dict[str, str]:
        return dict(httpx.QueryParams(self.requests[index].content.decode()))


@pytest.fixture
def bmw() -> FakeBmw:
    return FakeBmw()


@pytest.fixture
def make_state() -> Callable[..., State]:
    def _make(expires_at: float = 10_000_000_000.0, container_id: str | None = None) -> State:
        tokens = Tokens("zugang-alt", "erneuerung-alt", expires_at, "cardata:api:read")
        return State("client-1234-abcd", tokens, container_id)

    return _make
