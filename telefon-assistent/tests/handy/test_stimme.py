"""Stimmen: Ersatz bei Ausfall, Rückkehr zu Microsoft, Auswahl und Hörprobe."""

import asyncio
import shutil
from pathlib import Path

import numpy as np
import pytest

from assistent.handy import stimme as modul
from assistent.handy.stimme import EdgeStimme, Stimmen, pcm_zu_ogg, stimme_info


class Wackelig(EdgeStimme):
    def __init__(self):
        super().__init__("de-DE-KatjaNeural")
        self.fehler_noch = 1

    async def sprechen(self, text):
        if self.fehler_noch:
            self.fehler_noch -= 1
            raise ConnectionError("kurz weg")
        return np.ones(10, dtype=np.int16)


class Ersatz:
    name = "Piper"

    async def sprechen(self, text):
        return np.zeros(10, dtype=np.int16)


@pytest.mark.asyncio
async def test_microsoft_kommt_nach_kurzem_ausfall_zurueck(monkeypatch):
    ms = Wackelig()
    stimmen = Stimmen([ms, Ersatz()])
    await stimmen.sprechen("a")
    assert stimmen.zuletzt == "Piper" and "kurz weg" in stimmen.beschreibung()
    await stimmen.sprechen("b")  # noch in der Pause → Piper
    assert stimmen.zuletzt == "Piper"
    monkeypatch.setattr(modul.time, "monotonic", lambda: 10**9)
    await stimmen.sprechen("c")  # Pause vorbei → wieder Microsoft
    assert stimmen.zuletzt == "Microsoft" and "⚠️" not in stimmen.beschreibung()


def test_auswahl_und_vorstellung():
    stimmen = Stimmen([EdgeStimme("de-DE-KatjaNeural"), Ersatz()])
    assert stimmen.vorstellung() == ("Katja", True)
    stimmen.microsoft_waehlen("de-DE-FlorianMultilingualNeural")
    assert stimmen.vorstellung() == ("Florian", False)
    assert stimmen.beschreibung() == "Stimme: Microsoft Florian"
    assert stimme_info("de-DE-NeueNeural") == ("Neue", True)


@pytest.mark.asyncio
@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg fehlt")
async def test_hoerprobe_ist_ogg():
    ton = (np.sin(np.arange(8000) / 5) * 8000).astype(np.int16)
    ogg = await pcm_zu_ogg(ton)
    assert ogg[:4] == b"OggS"


@pytest.mark.asyncio
async def test_telegram_stimmen_befehl(tmp_path):
    from types import SimpleNamespace

    from assistent.telegram_bot import TelegramBot

    bot = TelegramBot.__new__(TelegramBot)
    bot.einst = SimpleNamespace(telegram_chat_id=1)
    gesendet, texte = [], []

    class Anrufe:
        async def status(self):
            return "Stimme: Microsoft Katja"

        def stimmen_liste(self):
            return [("de-DE-KatjaNeural", "Katja", True), ("de-DE-ConradNeural", "Conrad", False)]

        async def stimmprobe(self, kurzname):
            if "Conrad" in kurzname:
                raise ConnectionError("weg")
            return b"OggS..."

    class Nachricht:
        async def reply_text(self, text, **_):
            texte.append(text)

        async def reply_voice(self, ogg, caption, reply_markup):
            gesendet.append((ogg, caption, reply_markup.inline_keyboard[0][0].callback_data))

    bot.anrufe = Anrufe()
    update = SimpleNamespace(effective_chat=SimpleNamespace(id=1), effective_message=Nachricht())
    await bot._stimmen(update, None)
    assert gesendet == [(b"OggS...", "Katja (weiblich)", "stimme:0")]
    assert any("Conrad" in t and "nicht erreichbar" in t for t in texte)


TON_MP3 = (Path(__file__).parent / "ton.mp3").read_bytes()  # 2 s Sinus, wie von Microsoft (24 kHz MP3)


class ScheinCommunicate:
    """Ersetzt edge_tts.Communicate: liefert das MP3 in Stücken mit Verzögerung (wie übers Netz)."""

    gesendet_um: list[float] = []

    def __init__(self, text, stimme, rate="+0%"):
        pass

    async def stream(self):
        for i in range(0, len(TON_MP3), 2000):
            await asyncio.sleep(0.05)
            ScheinCommunicate.gesendet_um.append(asyncio.get_running_loop().time())
            yield {"type": "audio", "data": TON_MP3[i:i + 2000]}


@pytest.mark.asyncio
@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg fehlt")
async def test_microsoft_ton_kommt_stueckweise(monkeypatch):
    import edge_tts

    monkeypatch.setattr(edge_tts, "Communicate", ScheinCommunicate)
    ScheinCommunicate.gesendet_um = []
    stuecke, erstes_um = [], None
    async for stueck in EdgeStimme("de-DE-KatjaNeural").sprechen_strom("Hallo"):
        erstes_um = erstes_um or asyncio.get_running_loop().time()
        stuecke.append(stueck)
    assert erstes_um < ScheinCommunicate.gesendet_um[-1]  # Ton beginnt, bevor alles übertragen ist
    dauer = sum(len(s) for s in stuecke) / 8000
    assert 1.9 < dauer < 2.2 and len(stuecke) > 3


@pytest.mark.asyncio
async def test_vorrat_kommt_sofort_und_ersatz_bei_ausfall():
    class Zaehler(EdgeStimme):
        aufrufe = 0

        async def sprechen_strom(self, text):
            Zaehler.aufrufe += 1
            yield np.ones(800, dtype=np.int16)
            yield np.ones(800, dtype=np.int16)

    stimmen = Stimmen([Zaehler("de-DE-KatjaNeural"), Ersatz()])
    erst = [s async for s in stimmen.sprechen_strom("Okay.")]
    zweit = [s async for s in stimmen.sprechen_strom("Okay.")]
    assert Zaehler.aufrufe == 1 and len(erst) == 2 and len(zweit) == 1 and len(zweit[0]) == 1600

    class Kaputt(EdgeStimme):
        async def sprechen_strom(self, text):
            raise ConnectionError("weg")
            yield  # noqa

    stimmen = Stimmen([Kaputt("de-DE-KatjaNeural"), Ersatz()])
    ton = [s async for s in stimmen.sprechen_strom("Ein langer Satz, der nicht im Vorrat ist.")]
    assert len(ton) == 1 and stimmen.zuletzt == "Piper" and "weg" in stimmen.beschreibung()
