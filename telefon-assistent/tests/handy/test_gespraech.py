"""Gesprächssteuerung mit simulierter Leitung, Schein-KI und Schein-Stimme."""

import asyncio

import numpy as np
import pytest

from assistent.handy import gespraech as modul
from assistent.handy.gespraech import Gespraech
from assistent.ki import Antwort


class Leitung:
    def __init__(self, ton: np.ndarray):
        self.ton = ton
        self.pos = 0
        self.gesendet: list[np.ndarray] = []
        self.beendet = asyncio.Event()
        self.aufgelegt = False
        self.fern_nummer = "0221555"
        self.spielt = False

    async def empfangen(self):
        if self.beendet.is_set():
            return None
        await asyncio.sleep(0.001)
        stueck = self.ton[self.pos:self.pos + 160]
        self.pos += 160
        return stueck if len(stueck) == 160 else np.zeros(160, dtype=np.int16)

    def senden(self, pcm):
        self.gesendet.append(pcm)

    def leeren(self):
        pass

    async def warte_bis_ausgegeben(self):
        pass

    async def auflegen(self):
        self.aufgelegt = True
        self.beendet.set()


class KI:
    def __init__(self, antworten, transkript="Restaurant Da Mario, guten Tag."):
        self.antworten = list(antworten)
        self.transkript = transkript
        self.verlaeufe = []
        self.transkribiert = 0

    async def transkribieren(self, wav, name):
        self.transkribiert += 1
        return self.transkript

    async def gespraech_antwort(self, verlauf, werkzeuge):
        self.verlaeufe.append(list(verlauf))
        antwort = self.antworten.pop(0)
        if isinstance(antwort, Exception):
            raise antwort
        return antwort


class Stimme:
    def __init__(self):
        self.texte = []

    async def sprechen(self, text):
        self.texte.append(text)
        return np.ones(800, dtype=np.int16)


def sprache(sekunden):
    rng = np.random.default_rng(0)
    return (rng.standard_normal(int(8000 * sekunden)) * 3000).astype(np.int16)


def stille(sekunden):
    return np.zeros(int(8000 * sekunden), dtype=np.int16)


TSCHUESS = Antwort(
    text="Guten Tag, hier ist der digitale Assistent. Vielen Dank, auf Wiederhören.",
    werkzeug="gespraech_beenden", werkzeug_id="c1",
    argumente={"ergebnis": "Tisch reserviert", "erfolgreich": True},
    roh={"role": "assistant", "content": "…", "tool_calls": [{"id": "c1"}]},
)


@pytest.mark.asyncio
async def test_hoeren_antworten_auflegen():
    leitung = Leitung(np.concatenate([stille(0.4), sprache(1.0), stille(5)]))
    ki, stimme = KI([TSCHUESS]), Stimme()
    ergebnis = await asyncio.wait_for(Gespraech(leitung, ki, stimme, "System", False, 60).fuehren(), 10)
    assert ki.transkribiert == 1
    assert ki.verlaeufe[0][-1] == {"role": "user", "content": "Restaurant Da Mario, guten Tag."}
    assert stimme.texte == ["Guten Tag, hier ist der digitale Assistent.", "Vielen Dank, auf Wiederhören."]
    assert leitung.aufgelegt and ergebnis.erfolgreich and ergebnis.ergebnis == "Tisch reserviert"
    assert ergebnis.protokoll[0] == ("Gegenüber", "Restaurant Da Mario, guten Tag.")


@pytest.mark.asyncio
async def test_niemand_meldet_sich_assistent_beginnt(monkeypatch):
    monkeypatch.setattr(modul, "SELBST_BEGINNEN_NACH", 0.3)
    leitung = Leitung(stille(30))
    ki = KI([TSCHUESS])
    await asyncio.wait_for(Gespraech(leitung, ki, Stimme(), "System", False, 60).fuehren(), 10)
    assert "niemand hörbar" in ki.verlaeufe[0][-1]["content"]
    assert leitung.aufgelegt


@pytest.mark.asyncio
async def test_eingehend_assistent_begruesst_zuerst():
    leitung = Leitung(stille(30))
    ki = KI([TSCHUESS])
    ergebnis = await asyncio.wait_for(Gespraech(leitung, ki, Stimme(), "System", True, 60).fuehren(), 10)
    assert "angenommen" in ki.verlaeufe[0][-1]["content"] and ergebnis.anrufer == "0221555"


@pytest.mark.asyncio
async def test_whisper_halluzination_wird_ignoriert(monkeypatch):
    monkeypatch.setattr(modul, "SELBST_BEGINNEN_NACH", 30)
    leitung = Leitung(np.concatenate([sprache(1.0), stille(3)]))
    ki = KI([TSCHUESS], transkript="Untertitel im Auftrag des ZDF, 2021")
    gespraech = Gespraech(leitung, ki, Stimme(), "System", False, 60)
    aufgabe = asyncio.create_task(gespraech.fuehren())
    await asyncio.sleep(2)
    assert ki.transkribiert == 1 and ki.verlaeufe == []
    await leitung.auflegen()
    await aufgabe


@pytest.mark.asyncio
async def test_ki_fehler_entschuldigung_und_auflegen():
    leitung = Leitung(np.concatenate([sprache(1.0), stille(5)]))
    stimme = Stimme()
    ergebnis = await asyncio.wait_for(
        Gespraech(leitung, KI([RuntimeError("Groq weg")]), stimme, "System", False, 60).fuehren(), 10)
    assert "technische Probleme" in " ".join(stimme.texte)
    assert leitung.aufgelegt and "Groq weg" in ergebnis.ergebnis


@pytest.mark.asyncio
@pytest.mark.parametrize("transkript", ["Beep.", "Piep, piep, piep.", "Tuut tuut"])
async def test_piepen_wird_ignoriert(monkeypatch, transkript):
    monkeypatch.setattr(modul, "SELBST_BEGINNEN_NACH", 30)
    leitung = Leitung(np.concatenate([sprache(1.0), stille(3)]))
    ki = KI([TSCHUESS], transkript=transkript)
    aufgabe = asyncio.create_task(Gespraech(leitung, ki, Stimme(), "System", False, 60).fuehren())
    await asyncio.sleep(2)
    assert ki.transkribiert == 1 and ki.verlaeufe == [] and not leitung.aufgelegt
    await leitung.auflegen()
    await aufgabe


SOFORT_AUFLEGEN = Antwort(
    text="", werkzeug="gespraech_beenden", werkzeug_id="c0",
    argumente={"ergebnis": "Anrufbeantworter", "erfolgreich": False},
    roh={"role": "assistant", "content": "", "tool_calls": [{"id": "c0"}]},
)
VORSTELLEN = Antwort(text="Guten Tag, hier ist der digitale Assistent von Herrn Koch.",
                     roh={"role": "assistant", "content": "Guten Tag …"})


@pytest.mark.asyncio
async def test_legt_bei_kurzem_hallo_nicht_sofort_auf():
    leitung = Leitung(np.concatenate([sprache(1.0), stille(4)]))
    ki, stimme = KI([SOFORT_AUFLEGEN, VORSTELLEN], transkript="Hallo?"), Stimme()
    aufgabe = asyncio.create_task(Gespraech(leitung, ki, stimme, "System", False, 60).fuehren())
    await asyncio.sleep(2)
    assert not leitung.aufgelegt
    assert stimme.texte == ["Guten Tag, hier ist der digitale Assistent von Herrn Koch."]
    assert "Nicht aufgelegt" in ki.verlaeufe[1][-1]["content"]
    await leitung.auflegen()
    await aufgabe


@pytest.mark.asyncio
async def test_legt_bei_eindeutiger_ansage_auf():
    leitung = Leitung(np.concatenate([sprache(1.0), stille(5)]))
    ki = KI([SOFORT_AUFLEGEN], transkript="Der Teilnehmer ist zurzeit nicht erreichbar, bitte sprechen Sie nach dem Signalton.")
    ergebnis = await asyncio.wait_for(Gespraech(leitung, ki, Stimme(), "System", False, 60).fuehren(), 10)
    assert leitung.aufgelegt and ergebnis.ergebnis == "Anrufbeantworter"


ANLIEGEN = Antwort(text="Ich würde gern einen Tisch reservieren.", roh={"role": "assistant", "content": "…"})


@pytest.mark.asyncio
async def test_begruessung_kommt_sofort_ohne_ki():
    """Nach dem "Hallo" des Gegenübers kommt sofort die vorbereitete Begrüßung, dann das Anliegen."""
    leitung = Leitung(np.concatenate([stille(0.2), sprache(0.8), stille(5)]))
    ki, stimme = KI([ANLIEGEN], transkript="Hallo?"), Stimme()
    gruss = "Hallo! Hier ist die Telefonassistentin von Herrn Koch."
    gespraech = Gespraech(leitung, ki, stimme, "System", False, 60, begruessung=gruss)
    aufgabe = asyncio.create_task(gespraech.fuehren())
    await asyncio.sleep(2.5)
    assert stimme.texte[:2] == [gruss, "Ich würde gern einen Tisch reservieren."]
    verlauf = ki.verlaeufe[0]
    assert verlauf[1] == {"role": "user", "content": "Hallo?"}
    assert verlauf[2] == {"role": "assistant", "content": gruss}
    assert "Anliegen" in verlauf[3]["content"]
    await leitung.auflegen()
    ergebnis = await aufgabe
    assert ergebnis.protokoll[:2] == [("Gegenüber", "Hallo?"), ("Assistent", gruss)]


@pytest.mark.asyncio
async def test_eingehend_begruessung_sofort():
    leitung = Leitung(stille(30))
    ki, stimme = KI([]), Stimme()
    gruss = "Hallo, hier ist die Telefonassistentin von Herrn Koch, worum geht es denn?"
    aufgabe = asyncio.create_task(Gespraech(leitung, ki, stimme, "System", True, 60, begruessung=gruss).fuehren())
    await asyncio.sleep(0.5)
    assert stimme.texte == [gruss] and ki.verlaeufe == []  # sofort, ohne auf die KI zu warten
    await leitung.auflegen()
    await aufgabe


@pytest.mark.asyncio
async def test_begruessung_faellt_aus_dann_wie_bisher():
    class KaputteStimme(Stimme):
        async def sprechen(self, text):
            if text == "Hallo, guten Tag!":
                raise ConnectionError("weg")
            return await super().sprechen(text)

    leitung = Leitung(np.concatenate([sprache(1.0), stille(5)]))
    ki = KI([TSCHUESS])
    ergebnis = await asyncio.wait_for(Gespraech(
        leitung, ki, KaputteStimme(), "System", False, 60,
        begruessung="Hallo, guten Tag!").fuehren(), 10)
    assert ki.verlaeufe[0][-1] == {"role": "user", "content": "Restaurant Da Mario, guten Tag."}
    assert leitung.aufgelegt and ergebnis.erfolgreich
