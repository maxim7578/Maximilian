"""Nachgemachter Gemini-Live-Server (gleiches WebSocket-Protokoll) für Tests."""

import asyncio
import base64
import json

import numpy as np
from aiohttp import web


class ScheinGemini:
    def __init__(self, ablehnen: str = ""):
        self.ablehnen = ablehnen
        self.setup: dict = {}
        self.hinweise: list[str] = []
        self.audio_sekunden = 0.0
        self.werkzeug_antwort: dict = {}
        self.runner: web.AppRunner | None = None
        self.url = ""

    async def starten(self) -> str:
        app = web.Application()
        app.router.add_get("/ws", self._ws)
        self.runner = web.AppRunner(app)
        await self.runner.setup()
        site = web.TCPSite(self.runner, "127.0.0.1", 0)
        await site.start()
        port = site._server.sockets[0].getsockname()[1]
        self.url = f"ws://127.0.0.1:{port}/ws"
        return self.url

    async def stoppen(self) -> None:
        if self.runner:
            await self.runner.cleanup()

    async def _ws(self, request: web.Request) -> web.WebSocketResponse:
        ws = web.WebSocketResponse(max_msg_size=0)
        await ws.prepare(request)
        assert request.query.get("key")
        self.setup = json.loads((await ws.receive()).data)["setup"]
        if self.ablehnen:
            await ws.close(code=1008, message=self.ablehnen.encode())
            return ws
        await ws.send_str(json.dumps({"setupComplete": {}}))
        laut = 0.0
        geantwortet = False
        async for nachricht in ws:
            daten = json.loads(nachricht.data)
            eingabe = daten.get("realtimeInput", {})
            if "text" in eingabe:
                self.hinweise.append(eingabe["text"])
            if "audio" in eingabe:
                assert eingabe["audio"]["mimeType"] == "audio/pcm;rate=16000"
                pcm = np.frombuffer(base64.b64decode(eingabe["audio"]["data"]), dtype="<i2")
                self.audio_sekunden += len(pcm) / 16000
                if np.sqrt(np.mean(pcm.astype(np.float32) ** 2)) > 500:
                    laut += len(pcm) / 16000
            if "toolResponse" in daten:
                self.werkzeug_antwort = daten["toolResponse"]
                await ws.send_str(json.dumps({"serverContent": {"turnComplete": True}}))
            if not geantwortet and (laut >= 0.8 or self.hinweise):
                geantwortet = True
                asyncio.create_task(self._antworten(ws, bool(laut)))
        return ws

    async def _antworten(self, ws, gehoert: bool) -> None:
        if gehoert:
            await ws.send_str(json.dumps({"serverContent": {"inputTranscription": {"text": "Restaurant Da Mario, "}}}))
            await ws.send_str(json.dumps({"serverContent": {"inputTranscription": {"text": "guten Tag."}}}))
        t = np.arange(2400) / 24000
        for i in range(5):  # 0,5 s Ton (24 kHz), in 5 Stücken wie bei Gemini
            ton = (8000 * np.sin(2 * np.pi * 400 * (t + i * 0.1))).astype("<i2")
            await ws.send_str(json.dumps({"serverContent": {"modelTurn": {"parts": [
                {"inlineData": {"mimeType": "audio/pcm;rate=24000", "data": base64.b64encode(ton.tobytes()).decode()}}]}}}))
            if i == 0:
                await ws.send_str(json.dumps({"serverContent": {"outputTranscription": {"text": "Guten Tag, hier ist der digitale Assistent. "}}}))
            await asyncio.sleep(0.05)
        await ws.send_str(json.dumps({"serverContent": {"outputTranscription": {"text": "Auf Wiederhören."}}}))
        await ws.send_str(json.dumps({"toolCall": {"functionCalls": [{"id": "f1", "name": "gespraech_beenden",
            "args": {"ergebnis": "Tisch für 2 um 17 Uhr reserviert", "erfolgreich": True}}]}}))
