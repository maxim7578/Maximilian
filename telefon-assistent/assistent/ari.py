"""Steuerung von Asterisk über die ARI-Schnittstelle (nur lokal auf dem Laptop erreichbar)."""

import uuid

import httpx


class AriFehler(Exception):
    pass


class Ari:
    def __init__(self, url: str, benutzer: str, kennwort: str):
        self._client = httpx.AsyncClient(base_url=url, auth=(benutzer, kennwort), timeout=10)

    async def anrufen(self, nummer: str, auftrag_id: str, klingeldauer: int = 45) -> str:
        """Wählt über die FRITZ!Box. Nimmt jemand ab, übergibt Asterisk das Gespräch an die KI."""
        kanal_id = f"ki-{uuid.uuid4().hex[:12]}"
        try:
            antwort = await self._client.post(
                "/channels",
                params={
                    "endpoint": f"PJSIP/{nummer}@fritzbox",
                    "context": "ki-raus",
                    "extension": "s",
                    "priority": 1,
                    "timeout": klingeldauer,
                    "channelId": kanal_id,
                },
                json={"variables": {"KI_AUFTRAG": auftrag_id}},
            )
        except httpx.HTTPError as fehler:
            raise AriFehler(f"Asterisk ist nicht erreichbar ({fehler}).") from fehler
        if antwort.status_code >= 400:
            raise AriFehler(f"Asterisk konnte nicht wählen: {antwort.status_code} {antwort.text}")
        return kanal_id

    async def kanal_aktiv(self, kanal_id: str) -> bool:
        antwort = await self._client.get(f"/channels/{kanal_id}")
        return antwort.status_code == 200

    async def auflegen(self, kanal_id: str) -> None:
        await self._client.delete(f"/channels/{kanal_id}")

    async def erreichbar(self) -> bool:
        try:
            antwort = await self._client.get("/asterisk/info")
        except httpx.HTTPError:
            return False
        return antwort.status_code == 200
