"""Simuliertes Telefonat: Ein Test-Client spielt Asterisk und legt nach kurzer Zeit auf."""

import asyncio
import json
import socket

import pytest
import uvicorn
import websockets
from fastapi import FastAPI, WebSocket
from pipecat.processors.frame_processor import FrameProcessor

from assistent.gespraech import gespraech_fuehren


class Durchreicher(FrameProcessor):
    """Ersatz für die Sprachausgabe (lädt keine Stimme herunter)."""

    async def process_frame(self, frame, direction):
        await super().process_frame(frame, direction)
        await self.push_frame(frame, direction)


def freier_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.mark.asyncio
async def test_gespraech_startet_und_endet_beim_auflegen(tmp_path):
    ergebnisse = []
    app = FastAPI()

    @app.websocket("/ws")
    async def ws(websocket: WebSocket):
        await websocket.accept(subprotocol="media")
        ergebnisse.append(
            await gespraech_fuehren(
                websocket,
                systemtext="Test",
                selbst_beginnen=False,
                groq_api_key="gsk_test",
                llm_modell="openai/gpt-oss-120b",
                stt_modell="whisper-large-v3-turbo",
                piper_stimme="de_DE-thorsten-medium",
                piper_ordner=tmp_path,
                max_sekunden=60,
                tts=Durchreicher(),
            )
        )

    port = freier_port()
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning"))
    server_aufgabe = asyncio.create_task(server.serve())
    while not server.started:
        await asyncio.sleep(0.05)

    async with websockets.connect(f"ws://127.0.0.1:{port}/ws", subprotocols=["media"]) as client:
        await client.send(json.dumps({
            "event": "MEDIA_START",
            "connection_id": "test",
            "channel": "WebSocket/ki_raus-1",
            "channel_id": "test-1",
            "format": "slin",
            "optimal_frame_size": 320,
            "ptime": 20,
            "channel_variables": {"__ANRUFER": "0221123456", "__KI_AUFTRAG": "abc"},
        }))
        for _ in range(25):  # 0,5 s Stille
            await client.send(bytes(320))
            await asyncio.sleep(0.02)
        await asyncio.sleep(0.5)

    for _ in range(300):
        if ergebnisse:
            break
        await asyncio.sleep(0.1)
    server.should_exit = True
    await server_aufgabe

    assert ergebnisse, "Gespräch wurde nach dem Auflegen nicht beendet"
    assert ergebnisse[0].anrufer == "0221123456"
    assert ergebnisse[0].protokoll == []


def _chunk(delta: dict, finish: str | None = None) -> str:
    return "data: " + json.dumps({
        "id": "chatcmpl-test", "object": "chat.completion.chunk", "created": 0, "model": "test",
        "choices": [{"index": 0, "delta": delta, "finish_reason": finish}],
    }) + "\n\n"


@pytest.mark.asyncio
async def test_ki_verabschiedet_sich_und_legt_auf(tmp_path):
    """Schein-KI sagt Tschüss und ruft gespraech_beenden auf → Asterisk bekommt HANGUP."""
    from fastapi.responses import StreamingResponse

    ergebnisse, llm_anfragen = [], []
    app = FastAPI()

    @app.post("/v1/chat/completions")
    async def schein_ki(anfrage: dict):
        llm_anfragen.append(anfrage)

        async def strom():
            yield _chunk({"role": "assistant", "content": "Vielen Dank, auf Wiederhören."})
            yield _chunk({"tool_calls": [{
                "index": 0, "id": "call_1", "type": "function",
                "function": {
                    "name": "gespraech_beenden",
                    "arguments": json.dumps({"ergebnis": "Tisch für 2 um 17 Uhr reserviert", "erfolgreich": True}),
                },
            }]})
            yield _chunk({}, "tool_calls")
            yield "data: [DONE]\n\n"

        return StreamingResponse(strom(), media_type="text/event-stream")

    port = freier_port()

    @app.websocket("/ws")
    async def ws(websocket: WebSocket):
        await websocket.accept(subprotocol="media")
        ergebnisse.append(
            await gespraech_fuehren(
                websocket,
                systemtext="Test",
                selbst_beginnen=True,
                groq_api_key="gsk_test",
                llm_modell="test",
                stt_modell="whisper-large-v3-turbo",
                piper_stimme="de_DE-thorsten-medium",
                piper_ordner=tmp_path,
                max_sekunden=60,
                tts=Durchreicher(),
                llm_basis_url=f"http://127.0.0.1:{port}/v1",
            )
        )

    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning"))
    server_aufgabe = asyncio.create_task(server.serve())
    while not server.started:
        await asyncio.sleep(0.05)

    befehle = []
    async with websockets.connect(f"ws://127.0.0.1:{port}/ws", subprotocols=["media"]) as client:
        await client.send(json.dumps({
            "event": "MEDIA_START", "connection_id": "t", "channel": "WebSocket/ki_rein-1",
            "channel_id": "t-1", "format": "slin", "optimal_frame_size": 320, "ptime": 20,
            "channel_variables": {},
        }))

        async def stille_senden():
            while True:
                await client.send(bytes(320))
                await asyncio.sleep(0.02)

        sender = asyncio.create_task(stille_senden())
        try:
            async with asyncio.timeout(30):
                async for nachricht in client:
                    if isinstance(nachricht, str):
                        befehle.append(nachricht)
                        if "HANGUP" in nachricht:
                            break
        finally:
            sender.cancel()

    for _ in range(100):
        if ergebnisse:
            break
        await asyncio.sleep(0.1)
    server.should_exit = True
    await server_aufgabe

    assert any("HANGUP" in b for b in befehle), befehle
    assert llm_anfragen and llm_anfragen[0]["tools"][0]["function"]["name"] == "gespraech_beenden"
    assert llm_anfragen[0]["messages"][0] == {"role": "system", "content": "Test"}
    ergebnis = ergebnisse[0]
    assert ergebnis.ergebnis == "Tisch für 2 um 17 Uhr reserviert" and ergebnis.erfolgreich is True
    assert ("Assistent", "Vielen Dank, auf Wiederhören.") in ergebnis.protokoll
