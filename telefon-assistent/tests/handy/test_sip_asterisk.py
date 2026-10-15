"""SIP-Tests gegen ein echtes Asterisk in Docker (ahmt die FRITZ!Box nach).

Läuft nur, wenn Docker verfügbar ist: ASTERISK_TEST=1 python -m pytest tests/handy
"""

import asyncio
import os
import subprocess
import time
from pathlib import Path

import httpx
import numpy as np
import pytest
import pytest_asyncio

from assistent.handy import audio
from assistent.handy.sip import AnrufFehler, Telefon

pytestmark = pytest.mark.skipif(os.getenv("ASTERISK_TEST") != "1", reason="nur mit ASTERISK_TEST=1 (Docker)")
BILD = "andrius/asterisk:23.5.0_debian-trixie"
NAME = "sip-test-asterisk"


@pytest.fixture(scope="module")
def asterisk():
    subprocess.run(["docker", "rm", "-f", NAME], capture_output=True)
    konf = Path(__file__).parent / "asterisk"
    toene = Path("/tmp/test-sounds")
    toene.mkdir(exist_ok=True)
    rng = np.random.default_rng(0)  # "Sprache": 1,5 s lautes Rauschen in Silben
    silben = np.concatenate([(rng.standard_normal(1600) * 4000) if i % 2 == 0 else np.zeros(400) for i in range(10)])
    (toene / "gruss.wav").write_bytes(audio.wav_bytes(silben))
    subprocess.run(["docker", "run", "-d", "--name", NAME, "--network", "host",
                    "-v", f"{konf}:/etc/asterisk", "-v", f"{toene}:/tmp/test-sounds", BILD],
                   check=True, capture_output=True)
    for _ in range(60):
        r = subprocess.run(["docker", "exec", NAME, "asterisk", "-rx", "core show version"], capture_output=True)
        if r.returncode == 0 and b"Asterisk" in r.stdout:
            break
        time.sleep(0.5)
    yield
    subprocess.run(["docker", "rm", "-f", NAME], capture_output=True)


@pytest_asyncio.fixture
async def telefon(asterisk):
    t = Telefon("127.0.0.1", "kiassistent", "Test123", server_port=5070, lokaler_port=0, ablauf=120)
    await t.starten()
    for _ in range(50):
        if t.angemeldet:
            break
        await asyncio.sleep(0.1)
    yield t
    await t.stoppen()


def ton(frequenz=440, sekunden=1.0):
    t = np.arange(int(8000 * sekunden)) / 8000
    return (8000 * np.sin(2 * np.pi * frequenz * t)).astype(np.int16)


@pytest.mark.asyncio
async def test_anmeldung_mit_passwort(telefon):
    assert telefon.angemeldet, telefon.letzter_fehler
    r = subprocess.run(["docker", "exec", NAME, "asterisk", "-rx", "pjsip show contacts"], capture_output=True, text=True)
    assert "kiassistent" in r.stdout


@pytest.mark.asyncio
async def test_falsches_kennwort(asterisk):
    t = Telefon("127.0.0.1", "kiassistent", "falsch", server_port=5070, lokaler_port=0)
    await t.starten()
    await asyncio.sleep(2)
    assert not t.angemeldet and "abgelehnt" in t.letzter_fehler
    await t.stoppen()


@pytest.mark.asyncio
async def test_anruf_mit_echo_ton_kommt_zurueck(telefon):
    gespraech = await telefon.anrufen("100", klingeldauer=10)
    gespraech.senden(ton(440, 1.5))
    empfangen = []
    ende = asyncio.get_running_loop().time() + 3
    while asyncio.get_running_loop().time() < ende:
        stueck = await gespraech.empfangen()
        if stueck is None:
            break
        empfangen.append(stueck)
    await gespraech.auflegen()
    signal = np.concatenate(empfangen).astype(np.float32)
    assert audio.lautstaerke(signal) > 500, "kein Echo empfangen"
    spektrum = np.abs(np.fft.rfft(signal))
    assert abs(np.argmax(spektrum) * 8000 / len(signal) - 440) < 10
    assert gespraech.beendet.is_set()


@pytest.mark.asyncio
async def test_besetzt(telefon):
    with pytest.raises(AnrufFehler, match="besetzt"):
        await telefon.anrufen("200", klingeldauer=10)


@pytest.mark.asyncio
async def test_niemand_nimmt_ab(telefon):
    start = time.monotonic()
    with pytest.raises(AnrufFehler, match="niemand"):
        await telefon.anrufen("300", klingeldauer=3)
    assert time.monotonic() - start < 10
    await asyncio.sleep(1)
    r = subprocess.run(["docker", "exec", NAME, "asterisk", "-rx", "core show channels count"], capture_output=True, text=True)
    assert "0 active channels" in r.stdout


@pytest.mark.asyncio
async def test_gegenseite_legt_auf(telefon):
    gespraech = await telefon.anrufen("400", klingeldauer=10)
    await asyncio.wait_for(gespraech.beendet.wait(), 6)
    assert "aufgelegt" in gespraech.grund
    assert await gespraech.empfangen() is None


@pytest.mark.asyncio
async def test_eingehender_anruf(telefon):
    angenommen = asyncio.get_running_loop().create_future()

    async def annehmen(gespraech):
        angenommen.set_result(gespraech)

    telefon.bei_eingehendem_anruf = annehmen
    async with httpx.AsyncClient(auth=("test", "test")) as c:
        r = await c.post("http://127.0.0.1:8089/ari/channels", params={
            "endpoint": "PJSIP/kiassistent", "context": "test-warte", "extension": "s",
            "priority": 1, "callerId": "Max <0221555>"})
        assert r.status_code == 200, r.text
    gespraech = await asyncio.wait_for(angenommen, 10)
    assert gespraech.fern_nummer == "0221555" and gespraech.richtung == "rein"
    gespraech.senden(ton(600, 1.0))
    empfangen = []
    for _ in range(40):
        stueck = await gespraech.empfangen()
        if stueck is None:
            break
        empfangen.append(stueck)
    await gespraech.auflegen()
    assert audio.lautstaerke(np.concatenate(empfangen)) > 300


@pytest.mark.asyncio
async def test_gesamter_ablauf_handy(telefon, tmp_path):
    """Telegram-Auftrag → Anruf → „Restaurant“ meldet sich → KI verabschiedet sich → Auflegen → Bericht."""
    from assistent.auftrag import Anruf
    from assistent.einstellungen import Einstellungen
    from assistent.handy.anrufe import HandyAnrufverwaltung
    from assistent.ki import Antwort

    class KI:
        gehoert = []

        async def transkribieren(self, wav, name):
            self.gehoert.append(len(wav))
            return "Restaurant Da Mario, guten Tag."

        async def gespraech_antwort(self, verlauf, werkzeuge):
            return Antwort(
                text="Guten Tag, hier ist der digitale Assistent. Auf Wiederhören.",
                werkzeug="gespraech_beenden", werkzeug_id="c1",
                argumente={"ergebnis": "Tisch für 2 um 17 Uhr reserviert", "erfolgreich": True},
                roh={"role": "assistant", "content": "x", "tool_calls": [{"id": "c1"}]})

        async def bericht_schreiben(self, *args):
            raise RuntimeError("im Test kein Groq")

    class Stimme:
        async def sprechen(self, text):
            return ton(300, 1.0)

    meldungen = []

    async def melden(text):
        meldungen.append(text)

    einst = Einstellungen(
        telegram_token="1:a", telegram_chat_id=1, groq_api_key="x", inhaber="Herrn Test", wohnort="",
        rueckrufnummer="", eingehende_anrufe=False, llm_modell="m", stt_modell="s", piper_stimme="p",
        max_gespraech_sekunden=60, ari_url="", ari_benutzer="", ari_kennwort="", app_port=0,
        daten_ordner=str(tmp_path))
    verwaltung = HandyAnrufverwaltung(einst, telefon, KI(), Stimme(), melden)
    start = time.monotonic()
    await verwaltung.starten(Anruf(ziel="Da Mario", nummer="500", auftrag="Tisch reservieren", spielraum=""))
    for _ in range(300):
        if any("Bericht" in m for m in meldungen):
            break
        await asyncio.sleep(0.1)
    dauer = time.monotonic() - start
    assert any("abgenommen" in m for m in meldungen), meldungen
    bericht = next(m for m in meldungen if "Bericht" in m)
    assert "Tisch für 2 um 17 Uhr reserviert" in bericht and "Gegenüber: Restaurant Da Mario" in bericht
    assert KI.gehoert, "Ansage des Restaurants wurde nicht gehört"
    assert dauer < 15, f"Assistent hat nicht selbst aufgelegt ({dauer:.1f}s)"
    assert not verwaltung.beschaeftigt
    await asyncio.sleep(1)
    r = subprocess.run(["docker", "exec", NAME, "asterisk", "-rx", "core show channels count"], capture_output=True, text=True)
    assert "0 active channels" in r.stdout
