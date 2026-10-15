"""Sprachausgabe: natürliche Microsoft-Neural-Stimme (edge-tts), Ersatz: Piper (lokal)."""

import asyncio
import ctypes
import ctypes.util
import json
import re
import unicodedata
from pathlib import Path

import numpy as np
from loguru import logger

from . import audio


class StimmenFehler(Exception):
    pass


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


class EdgeStimme:
    """Microsoft-Neural-Stimmen (wie beim Vorlesen im Edge-Browser). Sehr natürlich, braucht Internet."""

    name = "Microsoft"

    def __init__(self, stimme: str = "de-DE-KatjaNeural", tempo: str = "+5%"):
        self.stimme = stimme
        self.tempo = tempo

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

    async def sprechen(self, text: str) -> np.ndarray:
        letzter_fehler = None
        for stimme in list(self.stimmen):
            try:
                return await asyncio.wait_for(stimme.sprechen(text), 15)
            except Exception as fehler:
                letzter_fehler = fehler
                logger.warning(f"Stimme {stimme.name} fehlgeschlagen: {fehler}")
                if len(self.stimmen) > 1 and stimme is self.stimmen[0]:
                    # Für den Rest des Tages die Ersatzstimme zuerst nehmen
                    self.stimmen = self.stimmen[1:] + [stimme]
        raise StimmenFehler(f"Keine Stimme funktioniert: {letzter_fehler}")


def stimmen_laden(art: str, edge_stimme: str, piper_modell: Path | None) -> Stimmen:
    liste = []
    if art in ("microsoft", "edge"):
        liste.append(EdgeStimme(edge_stimme))
    if piper_modell and piper_modell.exists():
        try:
            liste.append(PiperStimme(piper_modell))
        except Exception as fehler:
            logger.warning(f"Piper-Ersatzstimme nicht verfügbar: {fehler}")
    if art == "piper":
        liste.reverse()
    return Stimmen(liste)
