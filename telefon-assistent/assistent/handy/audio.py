"""Audio-Grundlagen fürs Telefon: G.711 (A-law/µ-law), Umtastung, WAV, Sprecherkennung."""

import io
import wave

import numpy as np

ABTASTRATE = 8000
RAHMEN = 160  # 20 ms bei 8 kHz


def _alaw_aus_linear(wert: int) -> int:
    wert >>= 3
    if wert >= 0:
        maske = 0xD5
    else:
        maske = 0x55
        wert = -wert - 1
    for segment, grenze in enumerate((0x1F, 0x3F, 0x7F, 0xFF, 0x1FF, 0x3FF, 0x7FF, 0xFFF)):
        if wert <= grenze:
            break
    else:
        return 0x7F ^ maske
    a = segment << 4
    a |= (wert >> 1) & 0x0F if segment < 2 else (wert >> segment) & 0x0F
    return a ^ maske


def _linear_aus_alaw(a: int) -> int:
    a ^= 0x55
    t = (a & 0x0F) << 4
    segment = (a & 0x70) >> 4
    if segment == 0:
        t += 8
    elif segment == 1:
        t += 0x108
    else:
        t = (t + 0x108) << (segment - 1)
    return t if a & 0x80 else -t


def _ulaw_aus_linear(wert: int) -> int:
    wert >>= 2
    if wert < 0:
        wert = -wert
        maske = 0x7F
    else:
        maske = 0xFF
    wert = min(wert, 8159) + 0x21
    for segment, grenze in enumerate((0x3F, 0x7F, 0xFF, 0x1FF, 0x3FF, 0x7FF, 0xFFF, 0x1FFF)):
        if wert <= grenze:
            break
    else:
        return 0x7F ^ maske
    return ((segment << 4) | ((wert >> (segment + 1)) & 0x0F)) ^ maske


def _linear_aus_ulaw(u: int) -> int:
    u = ~u & 0xFF
    t = (((u & 0x0F) << 3) + 0x84) << ((u & 0x70) >> 4)
    return 0x84 - t if u & 0x80 else t - 0x84


_ALLE = range(-32768, 32768)
_ALAW_KOD = np.array([_alaw_aus_linear(x) for x in _ALLE], dtype=np.uint8)
_ULAW_KOD = np.array([_ulaw_aus_linear(x) for x in _ALLE], dtype=np.uint8)
_ALAW_DEK = np.array([_linear_aus_alaw(x) for x in range(256)], dtype=np.int16)
_ULAW_DEK = np.array([_linear_aus_ulaw(x) for x in range(256)], dtype=np.int16)

# RTP-Nutzlasttypen
PCMU, PCMA = 0, 8


def kodieren(pcm: np.ndarray, nutzlast: int) -> bytes:
    tabelle = _ALAW_KOD if nutzlast == PCMA else _ULAW_KOD
    return tabelle[pcm.astype(np.int32) + 32768].tobytes()


def dekodieren(daten: bytes, nutzlast: int) -> np.ndarray:
    tabelle = _ALAW_DEK if nutzlast == PCMA else _ULAW_DEK
    return tabelle[np.frombuffer(daten, dtype=np.uint8)]


def umtasten(signal: np.ndarray, von: int, nach: int = ABTASTRATE) -> np.ndarray:
    """Ändert die Abtastrate (z. B. 22050 → 8000) mit Tiefpass gegen Verzerrungen."""
    x = np.asarray(signal, dtype=np.float32)
    if von == nach or len(x) == 0:
        return x
    if nach < von:
        grenze = 0.45 * nach / von
        n = np.arange(-32, 33)
        kern = 2 * grenze * np.sinc(2 * grenze * n) * np.hamming(len(n))
        x = np.convolve(x, (kern / kern.sum()).astype(np.float32), mode="same")
    dauer = len(x) / von
    ziel_zeiten = np.arange(int(dauer * nach)) / nach
    return np.interp(ziel_zeiten, np.arange(len(x)) / von, x).astype(np.float32)


def als_int16(signal: np.ndarray) -> np.ndarray:
    """float (-1..1) oder int → int16."""
    x = np.asarray(signal)
    if x.dtype.kind == "f":
        x = np.clip(x, -1.0, 1.0) * 32767
    return np.clip(x, -32768, 32767).astype(np.int16)


def wav_bytes(pcm: np.ndarray, abtastrate: int = ABTASTRATE) -> bytes:
    puffer = io.BytesIO()
    with wave.open(puffer, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(abtastrate)
        w.writeframes(als_int16(pcm).tobytes())
    return puffer.getvalue()


def lautstaerke(rahmen: np.ndarray) -> float:
    return float(np.sqrt(np.mean(rahmen.astype(np.float32) ** 2))) if len(rahmen) else 0.0


class Sprecherkennung:
    """Einfache, robuste Erkennung von Sprache in 20-ms-Rahmen (ohne KI-Modell).

    Passt sich dem Grundrauschen der Leitung an. Liefert pro Rahmen ein Ereignis:
    "anfang", "ende" oder None.
    """

    def __init__(
        self,
        anfang_ms: int = 100,
        ende_ms: int = 700,
        mindest_lautstaerke: float = 250.0,
        faktor: float = 3.0,
    ):
        self.anfang_rahmen = max(1, anfang_ms // 20)
        self.ende_rahmen = max(1, ende_ms // 20)
        self.mindest = mindest_lautstaerke
        self.faktor = faktor
        self.rauschen = 100.0
        self.spricht = False
        self._laut = 0
        self._leise = 0

    def schwelle(self) -> float:
        return max(self.mindest, self.rauschen * self.faktor)

    def verarbeiten(self, rahmen: np.ndarray, schwelle_extra: float = 1.0) -> str | None:
        pegel = lautstaerke(rahmen)
        ist_laut = pegel > self.schwelle() * schwelle_extra
        if not ist_laut:
            # Grundrauschen langsam nachführen (nur in leisen Rahmen)
            self.rauschen = 0.95 * self.rauschen + 0.05 * pegel
        if self.spricht:
            self._leise = 0 if ist_laut else self._leise + 1
            if self._leise >= self.ende_rahmen:
                self.spricht = False
                self._laut = 0
                return "ende"
        else:
            self._laut = self._laut + 1 if ist_laut else 0
            if self._laut >= self.anfang_rahmen:
                self.spricht = True
                self._leise = 0
                return "anfang"
        return None
