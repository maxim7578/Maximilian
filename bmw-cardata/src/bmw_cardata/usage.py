"""Zählt die Abrufe dieses Programms, damit das Tageslimit von BMW sichtbar bleibt.

Gezählt wird lokal über ein gleitendes 24-Stunden-Fenster. Abrufe anderer Programme
mit derselben Client-ID (z. B. Home Assistant) sieht diese Zählung nicht.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .files import write_private

DAILY_LIMIT = 50
WINDOW_SECONDS = 24 * 60 * 60
USAGE_FILE = "abrufe.json"


@dataclass(frozen=True)
class Usage:
    calls: tuple[float, ...] = ()

    def recent(self, now: float) -> tuple[float, ...]:
        return tuple(t for t in self.calls if now - t < WINDOW_SECONDS)

    def record(self, now: float) -> Usage:
        return Usage((*self.recent(now), now))

    def remaining(self, now: float) -> int:
        return max(0, DAILY_LIMIT - len(self.recent(now)))

    def next_free_at(self, now: float) -> float | None:
        """Ab wann wieder weniger als DAILY_LIMIT Abrufe im Fenster liegen, falls alles verbraucht ist.

        Auch abgelehnte Abrufe (HTTP 429) werden gezählt, es können also mehr als
        DAILY_LIMIT im Fenster liegen; frei wird es erst, wenn genug davon herausfallen.
        """
        recent = sorted(self.recent(now))
        if len(recent) < DAILY_LIMIT:
            return None
        return recent[len(recent) - DAILY_LIMIT] + WINDOW_SECONDS


def usage_path(state_file: Path) -> Path:
    return state_file.with_name(USAGE_FILE)


def load_usage(path: Path) -> Usage:
    """Liest die Zählung; fehlt sie oder ist sie beschädigt, beginnt sie von vorn."""
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        calls = raw["abrufe"]
        if not all(isinstance(t, (int, float)) and not isinstance(t, bool) for t in calls):
            return Usage()
        return Usage(tuple(float(t) for t in calls))
    except (OSError, ValueError, KeyError, TypeError):
        return Usage()


def save_usage(path: Path, usage: Usage) -> None:
    write_private(path, json.dumps({"abrufe": list(usage.calls)}))


def record_call(path: Path, now: float) -> None:
    """Erfasst einen Abruf. Der Zähler ist nur eine Anzeige: Schreibfehler brechen nichts ab."""
    try:
        save_usage(path, load_usage(path).record(now))
    except OSError:
        pass
