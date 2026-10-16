import asyncio

import aiohttp
import numpy as np
import pytest

from assistent.handy import gemini as modul
from assistent.handy.gemini import Abtaster, GeminiFehler, GeminiGespraech, hochtasten
from tests.handy.schein_gemini import ScheinGemini
from tests.handy.test_gespraech import Leitung, sprache, stille


@pytest.mark.asyncio
async def test_gemini_hoert_spricht_und_legt_auf():
    server = ScheinGemini()
    url = await server.starten()
    leitung = Leitung(np.concatenate([stille(0.3), sprache(1.2), stille(10)]))
    async with aiohttp.ClientSession() as sitzung:
        g = GeminiGespraech(leitung, "testkey", "Du bist ein Test.", False, 60, url=url)
        ergebnis = await asyncio.wait_for(g.fuehren(sitzung), 15)
    await server.stoppen()
    setup = server.setup
    assert setup["model"] == "models/gemini-2.5-flash-native-audio-latest"
    erkennung = setup["realtimeInputConfig"]["automaticActivityDetection"]
    assert erkennung["silenceDurationMs"] == 300 and erkennung["endOfSpeechSensitivity"] == "END_SENSITIVITY_HIGH"
    assert setup["generationConfig"]["responseModalities"] == ["AUDIO"]
    assert setup["generationConfig"]["speechConfig"]["voiceConfig"]["prebuiltVoiceConfig"]["voiceName"] == "Kore"
    assert "Du bist ein Test." in setup["systemInstruction"]["parts"][0]["text"]
    assert setup["tools"][0]["functionDeclarations"][0]["name"] == "gespraech_beenden"
    assert server.werkzeug_antwort["functionResponses"][0]["id"] == "f1"
    gesendet = np.concatenate(leitung.gesendet)
    assert abs(len(gesendet) - 4000) < 200  # 0,5 s bei 8 kHz
    assert leitung.aufgelegt and ergebnis.erfolgreich
    assert ergebnis.ergebnis == "Tisch für 2 um 17 Uhr reserviert"
    assert ergebnis.protokoll == [
        ("Gegenüber", "Restaurant Da Mario, guten Tag."),
        ("Assistent", "Guten Tag, hier ist der digitale Assistent. Auf Wiederhören."),
    ]


@pytest.mark.asyncio
async def test_gemini_beginnt_selbst_wenn_niemand_spricht(monkeypatch):
    monkeypatch.setattr(modul, "SELBST_BEGINNEN_NACH", 0.3)
    server = ScheinGemini()
    url = await server.starten()
    leitung = Leitung(stille(30))
    async with aiohttp.ClientSession() as sitzung:
        g = GeminiGespraech(leitung, "k", "Test", False, 60, url=url)
        await asyncio.wait_for(g.fuehren(sitzung), 15)
    await server.stoppen()
    assert server.hinweise and "niemand hörbar" in server.hinweise[0]
    assert leitung.aufgelegt


@pytest.mark.asyncio
async def test_gemini_lehnt_ab():
    server = ScheinGemini(ablehnen="API key not valid")
    url = await server.starten()
    async with aiohttp.ClientSession() as sitzung:
        with pytest.raises(GeminiFehler, match="abgelehnt"):
            await GeminiGespraech(None, "falsch", "Test", False, 60, url=url).verbinden(sitzung)
    await server.stoppen()


def test_abtaster_ohne_knackser():
    t = np.arange(24000) / 24000
    ton = (10000 * np.sin(2 * np.pi * 440 * t)).astype(np.int16)
    abt = Abtaster()
    stuecke = np.concatenate([abt.verarbeiten(ton[i:i + 1234]) for i in range(0, len(ton), 1234)])
    assert abs(len(stuecke) - 8000) < 30
    mitte = stuecke[100:-100].astype(np.float32)
    # Glatter Sinus: keine Sprünge an Stückgrenzen
    assert np.max(np.abs(np.diff(mitte))) < 2 * np.pi * 440 / 8000 * 10000 * 1.1
    spektrum = np.abs(np.fft.rfft(mitte))
    assert abs(np.argmax(spektrum) * 8000 / len(mitte) - 440) < 5


def test_hochtasten():
    x = np.array([0, 100, 200], dtype=np.int16)
    assert hochtasten(x).tolist() == [0, 50, 100, 150, 200, 200]


@pytest.mark.asyncio
async def test_ersatzmodell_wenn_modell_nicht_verfuegbar():
    from types import SimpleNamespace

    from assistent.handy.anrufe import GeminiEinstellungen, HandyAnrufverwaltung

    server = ScheinGemini(nur_modell="gemini-3.8-live")
    url = await server.starten()
    meldungen = []

    async def melden(text):
        meldungen.append(text)

    verwaltung = HandyAnrufverwaltung.__new__(HandyAnrufverwaltung)
    verwaltung.einst = SimpleNamespace(max_gespraech_sekunden=60)
    verwaltung.gemini = GeminiEinstellungen(api_key="k", url=url)
    verwaltung._sitzung = None
    verwaltung.melden = melden
    try:
        gespraech = await verwaltung._gemini_vorbereiten(None, "System", False)
        assert gespraech is not None and gespraech.modell == "gemini-3.8-live"
        assert server.modelle == ["models/gemini-2.5-flash-native-audio-latest"] * 2 + ["models/gemini-3.8-live"]
        assert meldungen == []
        await gespraech._ws.close()
    finally:
        await verwaltung._sitzung.close()
        await server.stoppen()
