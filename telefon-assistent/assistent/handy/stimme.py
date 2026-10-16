"""Sprachausgabe: natürliche Microsoft-Neural-Stimme (edge-tts), Ersatz: Piper (lokal)."""

import asyncio
import ctypes
import ctypes.util
import json
import re
import time
import unicodedata
from pathlib import Path

import numpy as np
from loguru import logger

from . import audio


class StimmenFehler(Exception):
    pass


# Deutsche Microsoft-Stimmen zur Auswahl: (Kurzname, Vorname für die Vorstellung, weiblich?)
MICROSOFT_STIMMEN = [
    ("de-DE-SeraphinaMultilingualNeural", "Seraphina", True),
    ("de-DE-KatjaNeural", "Katja", True),
    ("de-DE-AmalaNeural", "Amala", True),
    ("de-DE-FlorianMultilingualNeural", "Florian", False),
    ("de-DE-ConradNeural", "Conrad", False),
    ("de-DE-KillianNeural", "Killian", False),
]
PROBESATZ = ("Hallo, guten Tag! Ich bin {rolle} und rufe für {inhaber} an. Ich wollte mal fragen, ob heute "
             "Abend so gegen sieben noch ein Tisch für zwei Personen frei ist?")
PAUSE_NACH_FEHLER = 300  # s


def stimme_info(kurzname: str) -> tuple[str, bool]:
    """Vorname und Geschlecht zu einer Microsoft-Stimme (unbekannt: Vorname aus dem Namen)."""
    for name, vorname, weiblich in MICROSOFT_STIMMEN:
        if name.lower() == kurzname.lower():
            return vorname, weiblich
    vorname = re.sub(r"(Multilingual)?Neural$", "", kurzname.split("-")[-1]) or "Assistent"
    return vorname, True


async def mp3_zu_pcm(mp3: bytes) -> np.ndarray:
    """Dekodiert MP3 mit ffmpeg zu 8-kHz-PCM (int16)."""
    prozess = await asyncio.create_subprocess_exec(
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-i", "pipe:0",
        "-f", "s16le", "-ac", "1", "-ar", str(audio.ABTASTRATE), "pipe:1",
        stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    ausgabe, fehler = await prozess.communicate(mp3)
    if prozess.returncode != 0:
        raise StimmenFehler(f"ffmpeg: {fehler.decode(errors='replace')[:200]}")
    return np.frombuffer(ausgabe, dtype=np.int16)


async def pcm_zu_ogg(pcm: np.ndarray) -> bytes:
    """8-kHz-PCM → OGG/Opus (Telegram-Sprachnachricht) – klingt so, wie es am Telefon ankommt."""
    roh = audio.als_int16(pcm).tobytes()
    fehler = b""
    for kodierer in (["-c:a", "libopus"], ["-c:a", "opus", "-strict", "-2"]):  # ohne libopus: eingebauter
        prozess = await asyncio.create_subprocess_exec(
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-f", "s16le", "-ar", str(audio.ABTASTRATE),
            "-ac", "1", "-i", "pipe:0", *kodierer, "-ar", "48000", "-b:a", "32k", "-f", "ogg", "pipe:1",
            stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        ausgabe, fehler = await prozess.communicate(roh)
        if prozess.returncode == 0 and ausgabe:
            return ausgabe
    raise StimmenFehler(f"ffmpeg: {fehler.decode(errors='replace')[:200]}")


class EdgeStimme:
    """Microsoft-Neural-Stimmen (wie beim Vorlesen im Edge-Browser). Sehr natürlich, braucht Internet."""

    name = "Microsoft"

    def __init__(self, stimme: str = "de-DE-SeraphinaMultilingualNeural", tempo: str = "+8%"):
        self.stimme = stimme
        self.tempo = tempo
        self.vorname, self.weiblich = stimme_info(stimme)

    async def sprechen(self, text: str) -> np.ndarray:
        import edge_tts

        kommunikation = edge_tts.Communicate(text, self.stimme, rate=self.tempo)
        mp3 = bytearray()
        async for stueck in kommunikation.stream():
            if stueck["type"] == "audio":
                mp3.extend(stueck["data"])
        if not mp3:
            raise StimmenFehler("Keine Audiodaten von Microsoft erhalten")
        return await mp3_zu_pcm(bytes(mp3))


class _Espeak:
    """Zugriff auf die espeak-ng-Bibliothek (nur Lautschrift, keine Ausgabe)."""

    def __init__(self, sprache: str):
        pfad = ctypes.util.find_library("espeak-ng")
        for kandidat in (pfad, "libespeak-ng.so", "libespeak-ng.so.1"):
            if not kandidat:
                continue
            try:
                self._lib = ctypes.CDLL(kandidat)
                break
            except OSError:
                continue
        else:
            raise StimmenFehler("espeak-ng nicht gefunden (Termux: pkg install espeak)")
        self._lib.espeak_Initialize.restype = ctypes.c_int
        if self._lib.espeak_Initialize(2, 0, None, 0) < 0:  # AUDIO_OUTPUT_SYNCHRONOUS
            raise StimmenFehler("espeak-ng konnte nicht starten")
        self._lib.espeak_SetVoiceByName(sprache.encode())
        self._lib.espeak_TextToPhonemes.restype = ctypes.c_char_p
        self._lib.espeak_TextToPhonemes.argtypes = [ctypes.POINTER(ctypes.c_char_p), ctypes.c_int, ctypes.c_int]

    def lautschrift(self, text: str) -> str:
        puffer = ctypes.c_char_p(text.encode("utf-8"))
        zeiger = ctypes.pointer(puffer)
        teile = []
        while zeiger.contents.value:
            ergebnis = self._lib.espeak_TextToPhonemes(zeiger, 1, 0x02)  # UTF-8, IPA
            if ergebnis:
                teile.append(ergebnis.decode("utf-8"))
        return " ".join(teile)


class PiperStimme:
    """Lokale Piper-Stimme (onnxruntime + espeak-ng). Klingt künstlicher, läuft aber ohne Internet."""

    name = "Piper"

    def __init__(self, modell: Path):
        import onnxruntime

        self.konfig = json.loads(Path(f"{modell}.json").read_text(encoding="utf-8"))
        self._sitzung = onnxruntime.InferenceSession(str(modell), providers=["CPUExecutionProvider"])
        self._espeak = _Espeak(self.konfig.get("espeak", {}).get("voice", "de"))
        self._ids = self.konfig["phoneme_id_map"]
        inferenz = self.konfig.get("inference", {})
        self._skalen = np.array(
            [inferenz.get("noise_scale", 0.667), inferenz.get("length_scale", 1.0), inferenz.get("noise_w", 0.8)],
            dtype=np.float32,
        )
        self._rate = self.konfig["audio"]["sample_rate"]

    def _phoneme_ids(self, satz: str) -> list[int]:
        ids = [*self._ids["^"], *self._ids["_"]]
        for teil, zeichen in re.findall(r"([^,;:.!?]+)([,;:.!?]?)", satz):
            if not teil.strip():
                continue
            lautschrift = re.sub(r"\([^)]+\)", "", self._espeak.lautschrift(teil.strip())) + zeichen
            if zeichen in ",;:":
                lautschrift += " "
            for laut in unicodedata.normalize("NFD", lautschrift):
                if laut in self._ids:
                    ids += [*self._ids[laut], *self._ids["_"]]
        return ids + [*self._ids["$"]]

    def _synthese(self, text: str) -> np.ndarray:
        stuecke = []
        for satz in re.findall(r"[^.!?]+[.!?]?", text):
            if not satz.strip():
                continue
            ids = np.array([self._phoneme_ids(satz)], dtype=np.int64)
            eingaben = {"input": ids, "input_lengths": np.array([ids.shape[1]], dtype=np.int64), "scales": self._skalen}
            if self.konfig.get("num_speakers", 1) > 1:
                eingaben["sid"] = np.array([0], dtype=np.int64)
            ton = self._sitzung.run(None, eingaben)[0].squeeze()
            stuecke.append(audio.umtasten(ton, self._rate))
            stuecke.append(np.zeros(int(0.15 * audio.ABTASTRATE), dtype=np.float32))
        return audio.als_int16(np.concatenate(stuecke)) if stuecke else np.zeros(0, dtype=np.int16)

    async def sprechen(self, text: str) -> np.ndarray:
        return await asyncio.to_thread(self._synthese, text)


class Stimmen:
    """Probiert die Stimmen der Reihe nach; fällt eine aus, übernimmt die nächste."""

    def __init__(self, stimmen: list):
        if not stimmen:
            raise StimmenFehler("Keine Stimme verfügbar")
        self.stimmen = stimmen
        self.zuletzt = ""  # Name der zuletzt benutzten Stimme
        self.fehler: dict[str, str] = {}  # letzter Fehler je Stimme
        self._pause_bis: dict[str, float] = {}

    @property
    def microsoft(self) -> EdgeStimme | None:
        return next((s for s in self.stimmen if isinstance(s, EdgeStimme)), None)

    def vorstellung(self) -> tuple[str, bool]:
        """Vorname und Geschlecht, mit denen sich der Assistent am Telefon vorstellt."""
        ms = self.microsoft
        return (ms.vorname, ms.weiblich) if ms else ("", True)

    def microsoft_waehlen(self, kurzname: str) -> None:
        ms = self.microsoft
        if ms is None:
            ms = EdgeStimme(kurzname)
            self.stimmen.insert(0, ms)
        ms.stimme = kurzname
        ms.vorname, ms.weiblich = stimme_info(kurzname)
        self.stimmen.remove(ms)
        self.stimmen.insert(0, ms)  # die gewählte Stimme wieder zuerst probieren
        self.fehler.pop(ms.name, None)
        self._pause_bis.pop(ms.name, None)

    def beschreibung(self) -> str:
        ms = self.microsoft
        if ms is None:
            return "Stimme: Piper (lokal, klingt künstlich)"
        text = f"Stimme: Microsoft {ms.vorname}"
        if ms.name in self.fehler:
            text += f" ⚠️ zuletzt nicht erreichbar ({self.fehler[ms.name][:80]}) – Ersatz: Piper (klingt künstlich)"
        elif self.zuletzt and self.zuletzt != ms.name:
            text += f" ⚠️ zuletzt sprach die Ersatzstimme {self.zuletzt}"
        return text

    async def sprechen(self, text: str) -> np.ndarray:
        letzter_fehler = None
        jetzt = time.monotonic()
        # Eine kurz ausgefallene Stimme wird ein paar Minuten übersprungen, danach wieder probiert.
        reihenfolge = sorted(self.stimmen, key=lambda s: self._pause_bis.get(s.name, 0) > jetzt)
        for stimme in reihenfolge:
            try:
                ton = await asyncio.wait_for(stimme.sprechen(text), 10 if isinstance(stimme, EdgeStimme) else 30)
                self.zuletzt = stimme.name
                self.fehler.pop(stimme.name, None)
                self._pause_bis.pop(stimme.name, None)
                return ton
            except Exception as fehler:
                letzter_fehler = fehler
                self.fehler[stimme.name] = f"{fehler.__class__.__name__}: {fehler}"
                if len(self.stimmen) > 1:
                    self._pause_bis[stimme.name] = time.monotonic() + PAUSE_NACH_FEHLER
                logger.warning(f"Stimme {stimme.name} fehlgeschlagen: {fehler!r}")
        raise StimmenFehler(f"Keine Stimme funktioniert: {letzter_fehler}")


def stimmen_laden(art: str, edge_stimme: str, piper_modell: Path | None, tempo: str = "+8%") -> Stimmen:
    liste = []
    if art in ("microsoft", "edge"):
        liste.append(EdgeStimme(edge_stimme, tempo))
    if piper_modell and piper_modell.exists():
        try:
            liste.append(PiperStimme(piper_modell))
        except Exception as fehler:
            logger.warning(f"Piper-Ersatzstimme nicht verfügbar: {fehler}")
    if art == "piper":
        liste.reverse()
    return Stimmen(liste)
