import numpy as np
import pytest

audioop = pytest.importorskip("audioop")  # Referenz, gibt es nur bis Python 3.12

from assistent.handy import audio


@pytest.mark.parametrize("nutzlast, ref_kod, ref_dek", [
    (audio.PCMA, audioop.lin2alaw, audioop.alaw2lin),
    (audio.PCMU, audioop.lin2ulaw, audioop.ulaw2lin),
])
def test_g711_wie_referenz(nutzlast, ref_kod, ref_dek):
    alle = np.arange(-32768, 32768, dtype=np.int16)
    assert audio.kodieren(alle, nutzlast) == ref_kod(alle.tobytes(), 2)
    bytes_256 = bytes(range(256))
    assert audio.dekodieren(bytes_256, nutzlast).tobytes() == ref_dek(bytes_256, 2)


def test_umtasten_dauer_und_ton():
    t = np.arange(22050) / 22050
    ton = 0.5 * np.sin(2 * np.pi * 440 * t)
    neu = audio.umtasten(ton, 22050, 8000)
    assert abs(len(neu) - 8000) <= 1
    spektrum = np.abs(np.fft.rfft(neu))
    assert abs(np.argmax(spektrum) * 8000 / len(neu) - 440) < 5


def test_sprecherkennung():
    erk = audio.Sprecherkennung()
    stille = np.zeros(160, dtype=np.int16)
    rng = np.random.default_rng(1)
    sprache = (rng.standard_normal(160) * 3000).astype(np.int16)
    ereignisse = [erk.verarbeiten(stille) for _ in range(20)]
    ereignisse += [erk.verarbeiten(sprache) for _ in range(30)]
    ereignisse += [erk.verarbeiten(stille) for _ in range(40)]
    assert [e for e in ereignisse if e] == ["anfang", "ende"]


def test_wav():
    daten = audio.wav_bytes(np.zeros(800, dtype=np.int16))
    assert daten[:4] == b"RIFF" and len(daten) == 44 + 1600
