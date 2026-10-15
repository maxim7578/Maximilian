"""Ein Telefonat mit der KI führen: Zuhören (Groq Whisper) → Denken (Groq) → Sprechen (Piper)."""

import asyncio
from dataclasses import dataclass, field

from fastapi import WebSocket
from loguru import logger
from pipecat.adapters.schemas.function_schema import FunctionSchema
from pipecat.adapters.schemas.tools_schema import ToolsSchema
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.frames.frames import (
    BotStartedSpeakingFrame,
    BotStoppedSpeakingFrame,
    EndFrame,
    FunctionCallResultProperties,
    InputTransportMessageFrame,
    LLMMessagesAppendFrame,
    LLMRunFrame,
    TranscriptionFrame,
)
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.worker import PipelineParams, PipelineWorker
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.processors.aggregators.llm_response_universal import LLMContextAggregatorPair
from pipecat.processors.audio.vad_processor import VADProcessor
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor
from pipecat.services.groq.llm import GroqLLMService
from pipecat.services.groq.stt import GroqSTTService
from pipecat.services.llm_service import FunctionCallParams
from pipecat.services.piper.tts import PiperTTSService
from pipecat.transcriptions.language import Language
from pipecat.workers.runner import WorkerRunner
from pipecat_asterisk import AsteriskWebsocketTransport

# Telefonnetz (G.711) hat 8 kHz – Asterisk liefert uns genau das (slin).
ABTASTRATE = 8000
# Meldet sich nach dem Abheben niemand hörbar, beginnt der Assistent selbst.
SELBST_BEGINNEN_NACH = 5.0


@dataclass
class Gespraechsergebnis:
    ergebnis: str = ""
    erfolgreich: bool | None = None
    protokoll: list[tuple[str, str]] = field(default_factory=list)
    anrufer: str = ""

    def protokoll_text(self) -> str:
        return "\n".join(f"{wer}: {text}" for wer, text in self.protokoll)


class Ohr(FrameProcessor):
    """Merkt sich, ob schon etwas gehört wurde, und liest Kanaldaten von Asterisk."""

    def __init__(self):
        super().__init__()
        self.etwas_gehoert = asyncio.Event()
        self.kanal_variablen: dict = {}

    async def process_frame(self, frame, direction: FrameDirection):
        await super().process_frame(frame, direction)
        if isinstance(frame, TranscriptionFrame) and frame.text.strip():
            self.etwas_gehoert.set()
        elif isinstance(frame, InputTransportMessageFrame):
            nachricht = frame.message if isinstance(frame.message, dict) else {}
            if nachricht.get("event") == "MEDIA_START":
                # Vererbte Variablen heißen bei Asterisk "__NAME" – Unterstriche entfernen.
                self.kanal_variablen = {
                    str(name).lstrip("_"): wert
                    for name, wert in (nachricht.get("channel_variables") or {}).items()
                }
        await self.push_frame(frame, direction)


class Mund(FrameProcessor):
    """Verfolgt, ob der Assistent gerade spricht – damit erst nach dem Abschied aufgelegt wird."""

    def __init__(self):
        super().__init__()
        self.still = asyncio.Event()
        self.still.set()
        self.angefangen = asyncio.Event()

    async def process_frame(self, frame, direction: FrameDirection):
        await super().process_frame(frame, direction)
        if isinstance(frame, BotStartedSpeakingFrame):
            self.still.clear()
            self.angefangen.set()
        elif isinstance(frame, BotStoppedSpeakingFrame):
            self.still.set()
        await self.push_frame(frame, direction)


BEENDEN = FunctionSchema(
    name="gespraech_beenden",
    description=(
        "Beendet das Telefonat (legt auf). Erst aufrufen, nachdem du dich verabschiedet hast "
        "– oder sofort bei Anrufbeantworter oder Bandansage."
    ),
    properties={
        "ergebnis": {
            "type": "string",
            "description": "Alle wichtigen Details des Gesprächs für den Bericht.",
        },
        "erfolgreich": {
            "type": "boolean",
            "description": "true, wenn der Auftrag erledigt wurde bzw. alles Wichtige notiert ist.",
        },
    },
    required=["ergebnis", "erfolgreich"],
)


async def gespraech_fuehren(
    websocket: WebSocket,
    *,
    systemtext: str,
    selbst_beginnen: bool,
    groq_api_key: str,
    llm_modell: str,
    stt_modell: str,
    piper_stimme: str,
    piper_ordner,
    max_sekunden: int,
    tts=None,
    llm_basis_url: str = "https://api.groq.com/openai/v1",
) -> Gespraechsergebnis:
    """Führt ein Telefonat über die Asterisk-Websocket-Verbindung bis zum Auflegen."""
    ergebnis = Gespraechsergebnis()
    transport = AsteriskWebsocketTransport(websocket=websocket)

    stt = GroqSTTService(
        api_key=groq_api_key,
        settings=GroqSTTService.Settings(model=stt_modell, language=Language.DE),
    )
    llm = GroqLLMService(
        api_key=groq_api_key,
        base_url=llm_basis_url,
        settings=GroqLLMService.Settings(model=llm_modell, system_instruction=systemtext),
    )
    if tts is None:
        tts = PiperTTSService(
            settings=PiperTTSService.Settings(voice=piper_stimme),
            download_dir=piper_ordner,
        )

    context = LLMContext(tools=ToolsSchema(standard_tools=[BEENDEN]))
    benutzer, assistent = LLMContextAggregatorPair(context)
    ohr, mund = Ohr(), Mund()

    pipeline = Pipeline(
        [
            transport.input(),
            VADProcessor(vad_analyzer=SileroVADAnalyzer()),
            stt,
            ohr,
            benutzer,
            llm,
            tts,
            transport.output(),
            mund,
            assistent,
        ]
    )
    worker = PipelineWorker(
        pipeline,
        params=PipelineParams(audio_in_sample_rate=ABTASTRATE, audio_out_sample_rate=ABTASTRATE),
    )
    hintergrund: list[asyncio.Task] = []
    beendet = False

    async def auflegen_nach_abschied():
        nonlocal beendet
        if beendet:
            return
        beendet = True
        if mund.still.is_set():
            # Der Abschied ist vielleicht noch in der Sprachausgabe – kurz darauf warten.
            try:
                await asyncio.wait_for(mund.angefangen.wait(), timeout=4)
            except TimeoutError:
                pass
        try:
            await asyncio.wait_for(mund.still.wait(), timeout=20)
        except TimeoutError:
            pass
        await asyncio.sleep(1.5)  # Asterisk spielt den Rest des Puffers noch ab
        await worker.queue_frame(EndFrame())

    async def beenden(params: FunctionCallParams):
        ergebnis.ergebnis = str(params.arguments.get("ergebnis", ""))
        ergebnis.erfolgreich = bool(params.arguments.get("erfolgreich", False))
        mund.angefangen.clear()
        await params.result_callback(
            {"status": "Gespräch wird beendet."},
            properties=FunctionCallResultProperties(run_llm=False),
        )
        hintergrund.append(asyncio.create_task(auflegen_nach_abschied()))

    llm.register_function("gespraech_beenden", beenden)

    async def selbst_anfangen():
        try:
            await asyncio.wait_for(ohr.etwas_gehoert.wait(), timeout=SELBST_BEGINNEN_NACH)
        except TimeoutError:
            await worker.queue_frames(
                [
                    LLMMessagesAppendFrame(
                        messages=[
                            {
                                "role": "user",
                                "content": "(Am anderen Ende meldet sich niemand hörbar. "
                                "Beginne du das Gespräch.)",
                            }
                        ],
                        run_llm=True,
                    )
                ]
            )

    async def zeitlimit():
        await asyncio.sleep(max(max_sekunden - 30, 10))
        logger.info("Zeitlimit fast erreicht – Assistent soll zum Ende kommen.")
        await worker.queue_frames(
            [
                LLMMessagesAppendFrame(
                    messages=[
                        {
                            "role": "user",
                            "content": "(Die Gesprächszeit ist fast um. Fasse kurz zusammen, "
                            "verabschiede dich und rufe gespraech_beenden auf.)",
                        }
                    ],
                    run_llm=True,
                )
            ]
        )
        await asyncio.sleep(30)
        await auflegen_nach_abschied()

    @transport.event_handler("on_client_connected")
    async def verbunden(_transport, _client):
        if selbst_beginnen:
            await worker.queue_frames(
                [
                    LLMMessagesAppendFrame(
                        messages=[{"role": "user", "content": "(Der Anruf wurde angenommen.)"}],
                        run_llm=False,
                    ),
                    LLMRunFrame(),
                ]
            )
        else:
            hintergrund.append(asyncio.create_task(selbst_anfangen()))
        hintergrund.append(asyncio.create_task(zeitlimit()))

    @transport.event_handler("on_client_disconnected")
    async def getrennt(_transport, _client):
        await worker.cancel()

    runner = WorkerRunner(handle_sigint=False)
    try:
        await runner.add_workers(worker)
        await runner.run()
    finally:
        for aufgabe in hintergrund:
            aufgabe.cancel()

    ergebnis.anrufer = str(ohr.kanal_variablen.get("ANRUFER", ""))
    for nachricht in context.get_messages():
        rolle = nachricht.get("role") if isinstance(nachricht, dict) else None
        inhalt = nachricht.get("content") if isinstance(nachricht, dict) else None
        if rolle in ("user", "assistant") and isinstance(inhalt, str) and inhalt.strip():
            if inhalt.startswith("("):
                continue  # interne Hinweise, kein Gesprochenes
            ergebnis.protokoll.append(("Gegenüber" if rolle == "user" else "Assistent", inhalt.strip()))
    return ergebnis
