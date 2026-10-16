"""Gesprächssteuerung für die Handy-Version: Zuhören → Groq Whisper → Groq LLM → Stimme."""

import asyncio
import re
from dataclasses import dataclass, field

import numpy as np
from loguru import logger

from . import audio

SELBST_BEGINNEN_NACH = 5.0  # s: meldet sich niemand hörbar, beginnt der Assistent
VORLAUF_RAHMEN = 15  # 300 ms Ton vor dem erkannten Sprechbeginn mitnehmen
MAX_AEUSSERUNG_S = 25
MIN_WOERTER_VOR_AUFLEGEN = 4  # so wenig Gehörtes reicht nicht, um auf "Anrufbeantworter" zu schließen
UNTERBRECHEN_NACH_RAHMEN = 20  # 400 ms Sprache des Gegenübers unterbricht den Assistenten

# Whisper "hört" in Stille gern solche Sätze – die ignorieren wir.
HALLUZINATIONEN = re.compile(
    r"^(untertitel.*|vielen dank( fürs zuschauen)?\.?|danke\.?|tschüss\.?|"
    r"copyright.*|swr.*|zdf.*|((beep|piep|bip|tu+t|dü+t)\W*)+|\W*)$",
    re.IGNORECASE,
)

BEENDEN = {
    "type": "function",
    "function": {
        "name": "gespraech_beenden",
        "description": (
            "Beendet das Telefonat (legt auf). Erst aufrufen, nachdem du dich verabschiedet hast "
            "– oder sofort bei Anrufbeantworter oder Bandansage."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "ergebnis": {"type": "string", "description": "Alle wichtigen Details des Gesprächs für den Bericht."},
                "erfolgreich": {"type": "boolean", "description": "true, wenn der Auftrag erledigt wurde bzw. alles Wichtige notiert ist."},
            },
            "required": ["ergebnis", "erfolgreich"],
        },
    },
}


@dataclass
class Gespraechsergebnis:
    ergebnis: str = ""
    erfolgreich: bool | None = None
    protokoll: list[tuple[str, str]] = field(default_factory=list)
    anrufer: str = ""

    def protokoll_text(self) -> str:
        return "\n".join(f"{wer}: {text}" for wer, text in self.protokoll)


def saetze(text: str) -> list[str]:
    """Teilt eine Antwort in Sätze, damit der erste schon gesprochen wird, während der Rest entsteht."""
    teile = [t.strip() for t in re.findall(r"[^.!?]+[.!?]*", text) if t.strip()]
    return teile or ([text.strip()] if text.strip() else [])


class Gespraech:
    def __init__(self, leitung, ki, stimme, systemtext: str, selbst_beginnen: bool, max_sekunden: int):
        self.leitung = leitung
        self.ki = ki
        self.stimme = stimme
        self.verlauf: list[dict] = [{"role": "system", "content": systemtext}]
        self.selbst_beginnen = selbst_beginnen
        self.max_sekunden = max_sekunden
        self.ergebnis = Gespraechsergebnis(anrufer=getattr(leitung, "fern_nummer", ""))
        self._aeusserungen: asyncio.Queue[np.ndarray] = asyncio.Queue()
        self._spricht_seit = 0
        self._beenden = False
        self._unterbrochen = False

    # ---------- Zuhören ----------

    async def _zuhoeren(self) -> None:
        erkennung = audio.Sprecherkennung()
        vorlauf: list[np.ndarray] = []
        aktuell: list[np.ndarray] = []
        rest = np.zeros(0, dtype=np.int16)
        while True:
            stueck = await self.leitung.empfangen()
            if stueck is None:
                return
            rest = np.concatenate([rest, stueck])
            while len(rest) >= audio.RAHMEN:
                rahmen, rest = rest[:audio.RAHMEN], rest[audio.RAHMEN:]
                # Während der Assistent spricht, braucht es mehr Lautstärke (Echo der eigenen Stimme)
                ereignis = erkennung.verarbeiten(rahmen, 2.0 if self.leitung.spielt else 1.0)
                if erkennung.spricht or ereignis == "ende":
                    aktuell.append(rahmen)
                else:
                    vorlauf = (vorlauf + [rahmen])[-VORLAUF_RAHMEN:]
                if ereignis == "anfang":
                    aktuell = vorlauf + aktuell
                    vorlauf = []
                    self._spricht_seit = 0
                if erkennung.spricht:
                    self._spricht_seit += 1
                    if self.leitung.spielt and self._spricht_seit >= UNTERBRECHEN_NACH_RAHMEN and not self._beenden:
                        logger.info("Gegenüber unterbricht – Assistent hört auf zu sprechen.")
                        self._unterbrochen = True
                        self.leitung.leeren()
                if ereignis == "ende" or len(aktuell) * 0.02 > MAX_AEUSSERUNG_S:
                    if len(aktuell) >= 15:  # mindestens 300 ms
                        await self._aeusserungen.put(np.concatenate(aktuell))
                    aktuell = []

    # ---------- Antworten ----------

    async def _sprechen(self, text: str) -> None:
        """Spricht Satz für Satz; der nächste Satz wird erzeugt, während der vorige läuft."""
        self._unterbrochen = False
        aufgaben = [asyncio.create_task(self.stimme.sprechen(s)) for s in saetze(text)]
        try:
            for aufgabe in aufgaben:
                ton = await aufgabe
                if self._unterbrochen:
                    break
                self.leitung.senden(ton)
        finally:
            for aufgabe in aufgaben:
                aufgabe.cancel()

    def _zu_frueh_zum_auflegen(self) -> bool:
        """Noch nichts gesagt und kaum etwas gehört (z. B. nur "Beep") – dann nicht gleich auflegen."""
        if any(wer == "Assistent" for wer, _ in self.ergebnis.protokoll):
            return False
        gehoert = " ".join(text for wer, text in self.ergebnis.protokoll if wer == "Gegenüber")
        return len(gehoert.split()) < MIN_WOERTER_VOR_AUFLEGEN

    async def _ki_antwort(self, nachfassen: bool = True) -> None:
        antwort = await self.ki.gespraech_antwort(self.verlauf, [BEENDEN])
        self.verlauf.append(antwort.roh)
        if antwort.werkzeug == "gespraech_beenden" and not antwort.text and nachfassen and self._zu_frueh_zum_auflegen():
            logger.info("KI wollte sofort auflegen, obwohl kaum etwas zu hören war – Assistent meldet sich stattdessen.")
            self.verlauf.append({"role": "tool", "tool_call_id": antwort.werkzeug_id, "content": (
                "Nicht aufgelegt: Das war zu wenig, um sicher zu sein, dass niemand dran ist. "
                "Melde dich jetzt und stell dich vor.")})
            await self._ki_antwort(nachfassen=False)
            return
        if antwort.text:
            self.ergebnis.protokoll.append(("Assistent", antwort.text))
            await self._sprechen(antwort.text)
        if antwort.werkzeug == "gespraech_beenden":
            argumente = antwort.argumente or {}
            self.ergebnis.ergebnis = str(argumente.get("ergebnis", ""))
            self.ergebnis.erfolgreich = bool(argumente.get("erfolgreich", False))
            self.verlauf.append({"role": "tool", "tool_call_id": antwort.werkzeug_id, "content": "Aufgelegt."})
            self._beenden = True

    async def _hinweis(self, text: str) -> None:
        self.verlauf.append({"role": "user", "content": f"({text})"})
        await self._ki_antwort()

    async def _verarbeiten(self) -> None:
        if self.selbst_beginnen:
            await self._hinweis("Der Anruf wurde angenommen.")
        else:
            try:
                erste = await asyncio.wait_for(self._aeusserungen.get(), SELBST_BEGINNEN_NACH)
                await self._aeusserungen.put(erste)
            except TimeoutError:
                await self._hinweis("Am anderen Ende meldet sich niemand hörbar. Beginne du das Gespräch.")
        while not self._beenden:
            ton = await self._aeusserungen.get()
            # Kurz hintereinander Gesagtes zusammenfassen
            while not self._aeusserungen.empty():
                ton = np.concatenate([ton, self._aeusserungen.get_nowait()])
            try:
                text = await self.ki.transkribieren(audio.wav_bytes(ton), "aeusserung.wav")
            except Exception as fehler:
                logger.warning(f"Spracherkennung fehlgeschlagen: {fehler}")
                continue
            if not text or HALLUZINATIONEN.match(text.strip()):
                continue
            logger.info(f"Gegenüber: {text}")
            self.ergebnis.protokoll.append(("Gegenüber", text))
            self.verlauf.append({"role": "user", "content": text})
            await self._ki_antwort()

    async def _zeitlimit(self) -> None:
        await asyncio.sleep(max(self.max_sekunden - 30, 10))
        if not self._beenden:
            await self._hinweis("Die Gesprächszeit ist fast um. Fasse kurz zusammen, verabschiede dich "
                                "und rufe gespraech_beenden auf.")
        await asyncio.sleep(30)
        self._beenden = True

    async def fuehren(self) -> Gespraechsergebnis:
        hoeren = asyncio.create_task(self._zuhoeren())
        denken = asyncio.create_task(self._verarbeiten())
        uhr = asyncio.create_task(self._zeitlimit())
        aufgelegt = asyncio.create_task(self.leitung.beendet.wait())
        try:
            while not self.leitung.beendet.is_set():
                fertig, _ = await asyncio.wait({denken, aufgelegt, uhr}, return_when=asyncio.FIRST_COMPLETED)
                if aufgelegt in fertig:
                    break
                if denken in fertig and denken.exception():
                    logger.error(f"Gesprächsfehler: {denken.exception()}")
                    try:
                        self.leitung.leeren()
                        await self._sprechen("Entschuldigung, ich habe gerade technische Probleme. "
                                             "Ich melde mich später noch einmal. Auf Wiederhören.")
                    except Exception:
                        pass
                    self.ergebnis.ergebnis = self.ergebnis.ergebnis or f"Technischer Fehler: {denken.exception()}"
                    self._beenden = True
                if self._beenden or denken.done() or uhr.done():
                    # Abschied noch ausreden lassen, dann auflegen
                    try:
                        await asyncio.wait_for(self.leitung.warte_bis_ausgegeben(), 20)
                    except TimeoutError:
                        pass
                    await asyncio.sleep(0.8)
                    await self.leitung.auflegen()
                    break
        finally:
            for aufgabe in (hoeren, denken, uhr, aufgelegt):
                aufgabe.cancel()
        return self.ergebnis
