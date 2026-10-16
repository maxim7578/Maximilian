"""Gesprächsführung mit Google Gemini Live: ein Modell hört, denkt und spricht – fast ohne Pause.

Protokoll: WebSocket "BidiGenerateContent" der Gemini API (wie im offiziellen Beispiel
google-gemini/cookbook, quickstarts/websockets/Get_started_LiveAPI.py), ohne SDK, damit es
auch auf Android/Termux läuft.
"""

import asyncio
import base64
import json

import aiohttp
import numpy as np
from loguru import logger

from . import audio
from .gespraech import Gespraechsergebnis

GEMINI_URL = (
    "wss://generativelanguage.googleapis.com/ws/"
    "google.ai.generativelanguage.v1beta.GenerativeService.BidiGenerateContent"
)
SELBST_BEGINNEN_NACH = 3.0

BEENDEN = {
    "name": "gespraech_beenden",
    "description": (
        "Beendet das Telefonat (legt auf). Erst aufrufen, nachdem du dich verabschiedet hast "
        "– oder sofort bei Anrufbeantworter oder Bandansage."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "ergebnis": {"type": "STRING", "description": "Alle wichtigen Details des Gesprächs für den Bericht."},
            "erfolgreich": {"type": "BOOLEAN", "description": "true, wenn der Auftrag erledigt wurde."},
        },
        "required": ["ergebnis", "erfolgreich"],
    },
}


class GeminiFehler(Exception):
    pass


class Abtaster:
    """Wandelt fortlaufend 24 kHz (Gemini) in 8 kHz (Telefon) um – ohne Knackser an Stückgrenzen."""

    def __init__(self, faktor: int = 3, laenge: int = 63):
        n = np.arange(laenge) - (laenge - 1) / 2
        grenze = 0.9 / (2 * faktor)
        kern = 2 * grenze * np.sinc(2 * grenze * n) * np.hamming(laenge)
        self.kern = (kern / kern.sum()).astype(np.float32)
        self.faktor = faktor
        self.rest = np.zeros(laenge - 1, dtype=np.float32)
        self.versatz = 0

    def verarbeiten(self, pcm: np.ndarray) -> np.ndarray:
        x = np.concatenate([self.rest, pcm.astype(np.float32)])
        gefiltert = np.convolve(x, self.kern, mode="valid")
        self.rest = x[-(len(self.kern) - 1):]
        ausgabe = gefiltert[self.versatz::self.faktor]
        self.versatz = (self.versatz - len(gefiltert)) % self.faktor
        return audio.runden_int16(ausgabe)


def hochtasten(pcm8k: np.ndarray) -> np.ndarray:
    """8 kHz → 16 kHz für Gemini (Sprache bleibt gut verständlich)."""
    x = pcm8k.astype(np.float32)
    zwischen = (x + np.concatenate([x[1:], x[-1:]])) / 2
    return audio.runden_int16(np.stack([x, zwischen], axis=1).reshape(-1))


class GeminiGespraech:
    def __init__(
        self,
        leitung,
        api_key: str,
        systemtext: str,
        selbst_beginnen: bool,
        max_sekunden: int,
        modell: str = "gemini-2.5-flash-native-audio-latest",
        stimme: str = "Kore",
        url: str = GEMINI_URL,
    ):
        self.leitung = leitung
        self.api_key = api_key
        self.systemtext = systemtext
        self.selbst_beginnen = selbst_beginnen
        self.max_sekunden = max_sekunden
        self.modell = modell
        self.stimme = stimme
        self.url = url
        self.ergebnis = Gespraechsergebnis(anrufer=getattr(leitung, "fern_nummer", ""))
        self._ws: aiohttp.ClientWebSocketResponse | None = None
        self._beenden = asyncio.Event()
        self._etwas_gehoert = asyncio.Event()
        self._letztes_audio = 0.0
        self._ein_text = ""
        self._aus_text = ""

    # ---------- Verbindung ----------

    def _setup(self) -> dict:
        return {
            "setup": {
                "model": f"models/{self.modell}",
                "generationConfig": {
                    "responseModalities": ["AUDIO"],
                    "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": self.stimme}}},
                },
                "systemInstruction": {
                    "parts": [{"text": self.systemtext + "\n\nSprich ausschließlich Deutsch."}]
                },
                "tools": [{"functionDeclarations": [BEENDEN]}],
                "inputAudioTranscription": {},
                "outputAudioTranscription": {},
            }
        }

    async def verbinden(self, sitzung: aiohttp.ClientSession) -> None:
        """Baut die Verbindung auf. Schlägt das fehl, kann der Anrufer auf die klassische Variante ausweichen."""
        try:
            self._ws = await sitzung.ws_connect(f"{self.url}?key={self.api_key}", heartbeat=20, max_msg_size=0)
            await self._ws.send_str(json.dumps(self._setup()))
            antwort = await asyncio.wait_for(self._ws.receive(), 10)
        except (aiohttp.ClientError, TimeoutError) as fehler:
            raise GeminiFehler(f"Gemini nicht erreichbar: {fehler}") from fehler
        if antwort.type in (aiohttp.WSMsgType.CLOSE, aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
            raise GeminiFehler(f"Gemini hat abgelehnt: {self._ws.close_code} {antwort.extra or ''}".strip())
        daten = json.loads(antwort.data if isinstance(antwort.data, str) else antwort.data.decode())
        if "setupComplete" not in daten:
            raise GeminiFehler(f"Unerwartete Antwort von Gemini: {str(daten)[:200]}")

    async def _senden(self, nachricht: dict) -> None:
        if self._ws is not None and not self._ws.closed:
            await self._ws.send_str(json.dumps(nachricht))

    async def _hinweis(self, text: str) -> None:
        await self._senden({"realtimeInput": {"text": f"({text})"}})

    # ---------- Ton zu Gemini ----------

    async def _hoeren(self) -> None:
        puffer: list[np.ndarray] = []
        erkennung = audio.Sprecherkennung()
        while True:
            stueck = await self.leitung.empfangen()
            if stueck is None:
                return
            if erkennung.verarbeiten(stueck[: audio.RAHMEN]) == "anfang":
                self._etwas_gehoert.set()
            puffer.append(stueck)
            if sum(len(p) for p in puffer) >= 800:  # alle 100 ms senden
                ton = hochtasten(np.concatenate(puffer))
                puffer = []
                await self._senden({"realtimeInput": {"audio": {
                    "data": base64.b64encode(ton.tobytes()).decode(),
                    "mimeType": "audio/pcm;rate=16000",
                }}})

    # ---------- Antworten von Gemini ----------

    def _protokoll_ein(self) -> None:
        if self._ein_text.strip():
            self.ergebnis.protokoll.append(("Gegenüber", self._ein_text.strip()))
        self._ein_text = ""

    def _protokoll_aus(self) -> None:
        if self._aus_text.strip():
            self.ergebnis.protokoll.append(("Assistent", self._aus_text.strip()))
        self._aus_text = ""

    async def _empfangen(self) -> None:
        abtaster = Abtaster()
        loop = asyncio.get_running_loop()
        async for nachricht in self._ws:
            if nachricht.type not in (aiohttp.WSMsgType.TEXT, aiohttp.WSMsgType.BINARY):
                break
            daten = json.loads(nachricht.data if isinstance(nachricht.data, str) else nachricht.data.decode())
            inhalt = daten.get("serverContent") or {}
            if inhalt.get("interrupted"):
                logger.info("Gegenüber unterbricht – Assistent hört auf zu sprechen.")
                self.leitung.leeren()
            if "inputTranscription" in inhalt:
                self._protokoll_aus()
                self._ein_text += inhalt["inputTranscription"].get("text", "")
            if "outputTranscription" in inhalt:
                self._protokoll_ein()
                self._aus_text += inhalt["outputTranscription"].get("text", "")
            for teil in (inhalt.get("modelTurn") or {}).get("parts", []):
                ton = (teil.get("inlineData") or {}).get("data")
                if ton:
                    pcm = np.frombuffer(base64.b64decode(ton), dtype="<i2")
                    self.leitung.senden(abtaster.verarbeiten(pcm))
                    self._letztes_audio = loop.time()
            if inhalt.get("turnComplete"):
                self._protokoll_ein()
                self._protokoll_aus()
            for aufruf in (daten.get("toolCall") or {}).get("functionCalls", []):
                if aufruf.get("name") == "gespraech_beenden":
                    argumente = aufruf.get("args") or {}
                    self.ergebnis.ergebnis = str(argumente.get("ergebnis", ""))
                    self.ergebnis.erfolgreich = bool(argumente.get("erfolgreich", False))
                    self._beenden.set()
                await self._senden({"toolResponse": {"functionResponses": [{
                    "id": aufruf.get("id"), "name": aufruf.get("name"), "response": {"ergebnis": "ok"},
                }]}})
            if "goAway" in daten:
                logger.warning(f"Gemini beendet die Sitzung bald: {daten['goAway']}")
        logger.info(f"Gemini-Verbindung geschlossen ({self._ws.close_code})")

    # ---------- Ablauf ----------

    async def _start(self) -> None:
        if self.selbst_beginnen:
            await self._hinweis("Der Anruf wurde angenommen. Begrüße den Anrufer.")
            return
        try:
            await asyncio.wait_for(self._etwas_gehoert.wait(), SELBST_BEGINNEN_NACH)
        except TimeoutError:
            await self._hinweis("Am anderen Ende meldet sich niemand hörbar. Beginne du das Gespräch.")

    async def _zeitlimit(self) -> None:
        await asyncio.sleep(max(self.max_sekunden - 30, 10))
        await self._hinweis("Die Gesprächszeit ist fast um. Fasse kurz zusammen, verabschiede dich "
                            "und rufe gespraech_beenden auf.")
        await asyncio.sleep(30)
        self._beenden.set()

    async def _ausreden_lassen(self) -> None:
        """Nach dem Beenden-Aufruf: den Abschied noch fertig sprechen lassen, dann auflegen."""
        loop = asyncio.get_running_loop()
        ende = loop.time() + 20
        while loop.time() < ende:
            still_seit = loop.time() - self._letztes_audio
            if not self.leitung.spielt and still_seit > 1.5:
                break
            await asyncio.sleep(0.1)
        await asyncio.sleep(0.5)
        await self.leitung.auflegen()

    async def fuehren(self, sitzung: aiohttp.ClientSession) -> Gespraechsergebnis:
        if self._ws is None:
            await self.verbinden(sitzung)
        self._letztes_audio = asyncio.get_running_loop().time()
        aufgaben = [
            asyncio.create_task(self._hoeren()),
            asyncio.create_task(self._start()),
            asyncio.create_task(self._zeitlimit()),
        ]
        empfang = asyncio.create_task(self._empfangen())
        beenden = asyncio.create_task(self._beenden.wait())
        aufgelegt = asyncio.create_task(self.leitung.beendet.wait())
        try:
            fertig, _ = await asyncio.wait({empfang, beenden, aufgelegt}, return_when=asyncio.FIRST_COMPLETED)
            if beenden in fertig and not self.leitung.beendet.is_set():
                await self._ausreden_lassen()
            elif empfang in fertig and not self.leitung.beendet.is_set():
                # Gemini hat die Verbindung beendet (z. B. Limit erreicht)
                fehler = empfang.exception()
                self.ergebnis.ergebnis = self.ergebnis.ergebnis or f"Verbindung zu Gemini abgebrochen: {fehler or self._ws.close_code}"
                await self.leitung.warte_bis_ausgegeben()
                await self.leitung.auflegen()
        finally:
            for aufgabe in (*aufgaben, empfang, beenden, aufgelegt):
                aufgabe.cancel()
            if self._ws is not None:
                await self._ws.close()
            self._protokoll_ein()
            self._protokoll_aus()
        return self.ergebnis
