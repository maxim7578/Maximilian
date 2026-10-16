"""Stimmen: Ersatz bei Ausfall, Rückkehr zu Microsoft, Auswahl und Hörprobe."""

import asyncio
import shutil

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
