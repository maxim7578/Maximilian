"""Push-Nachrichten aufs Handy über ntfy (https://ntfy.sh oder ein eigener Server).

Veröffentlicht wird als JSON an die Server-Adresse, damit Umlaute im Titel ankommen.
Die Pushes enthalten nur die Warnung und die letzten vier Zeichen der Fahrgestellnummer,
nie die Position.
"""

from __future__ import annotations

import httpx

from .alerts import AlertSettings


PUSH_TIMEOUT_SECONDS = 10.0


class NtfyError(Exception):
    """Der Push konnte nicht zugestellt werden."""


def mask_vin(vin: str) -> str:
    return f"…{vin[-4:]}"


def send_push(http: httpx.Client, settings: AlertSettings, title: str, lines: list[str]) -> None:
    if not settings.ntfy_topic:
        raise NtfyError("Es ist kein ntfy-Thema eingestellt ('bmw-cardata warnungen einstellen --ntfy-thema neu').")
    payload = {"topic": settings.ntfy_topic, "title": title, "message": "\n".join(lines),
               "priority": 4, "tags": ["warning"]}
    try:
        # kurzes Zeitlimit: im Live-Modus wartet sonst der Empfang auf einen hängenden Server
        response = http.post(settings.ntfy_server.rstrip("/") + "/", json=payload, timeout=PUSH_TIMEOUT_SECONDS)
    except (httpx.HTTPError, httpx.InvalidURL) as error:
        raise NtfyError(f"Push nicht zugestellt ({type(error).__name__}).") from error
    if not response.is_success:  # auch eine Weiterleitung ist kein zugestellter Push
        raise NtfyError(f"Push nicht zugestellt (HTTP {response.status_code}).")
