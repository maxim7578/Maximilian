"""Ablauf im Telegram-Bot und in der Anrufverwaltung – mit Ersatzteilen statt Telegram/Groq/Asterisk."""

import asyncio
from dataclasses import replace
from types import SimpleNamespace

import pytest

from assistent import anrufe as anrufe_modul
from assistent.anrufe import Anrufverwaltung
from assistent.anruflimit import Anruflimit
from assistent.auftrag import Anruf
from assistent.einstellungen import Einstellungen
from assistent.gespraech import Gespraechsergebnis
from assistent.ki import Auftrag
from assistent.telegram_bot import TelegramBot


def einstellungen(tmp_path, chat_id=42):
    return Einstellungen(
        telegram_token="123:abc", telegram_chat_id=chat_id, groq_api_key="gsk_x",
        inhaber="Herrn Koch", wohnort="Köln", rueckrufnummer="", eingehende_anrufe=False,
        llm_modell="m", stt_modell="s", piper_stimme="p", max_gespraech_sekunden=300,
        ari_url="http://127.0.0.1:1/ari", ari_benutzer="a", ari_kennwort="b", app_port=1,
        daten_ordner=str(tmp_path),
    )


class ErsatzKI:
    def __init__(self, auftraege):
        self.auftraege = list(auftraege)
        self.texte = []

    async def auftrag_verstehen(self, text, jetzt):
        self.texte.append(text)
        return self.auftraege.pop(0)


class ErsatzAri:
    def __init__(self, nimmt_ab=False):
        self.gewaehlt = []
        self.nimmt_ab = nimmt_ab

    async def anrufen(self, nummer, auftrag_id, klingeldauer=45):
        self.gewaehlt.append(nummer)
        return "kanal-1"

    async def kanal_aktiv(self, kanal_id):
        return False

    async def auflegen(self, kanal_id):
        pass


class ErsatzNachricht:
    def __init__(self, text=""):
        self.text = text
        self.antworten = []

    async def reply_text(self, text, reply_markup=None):
        self.antworten.append((text, reply_markup))


def update(chat_id=42, text="", art="private", nutzer_id=42):
    nachricht = ErsatzNachricht(text)
    return SimpleNamespace(
        effective_chat=SimpleNamespace(id=chat_id, type=art),
        effective_user=SimpleNamespace(id=nutzer_id) if nutzer_id is not None else None,
        effective_message=nachricht,
    ), nachricht


@pytest.mark.asyncio
async def test_fremde_chats_werden_ignoriert(tmp_path):
    bot = TelegramBot(einstellungen(tmp_path), ErsatzKI([]))
    upd, nachricht = update(chat_id=999, text="Ruf 0221 123456 an")
    await bot._textnachricht(upd, None)
    assert nachricht.antworten == []


@pytest.mark.asyncio
async def test_rueckfrage_dann_bestaetigung_mit_nummer_aus_kontakten(tmp_path):
    ki = ErsatzKI([
        Auftrag(typ="rueckfrage", rueckfrage="Für wie viele Personen?"),
        Auftrag(typ="anruf", ziel="Da Mario", auftrag="Tisch für 2 um 17 Uhr reservieren"),
    ])
    bot = TelegramBot(einstellungen(tmp_path), ki)
    bot.kontakte.speichern("Da Mario", "0221 123456")

    upd, nachricht = update(text="Reservier bei Da Mario um 17 Uhr")
    await bot._textnachricht(upd, None)
    assert "Für wie viele Personen?" in nachricht.antworten[-1][0]

    upd, nachricht = update(text="zu zweit")
    await bot._textnachricht(upd, None)
    assert "Ergänzung: zu zweit" in ki.texte[-1]
    text, knoepfe = nachricht.antworten[-1]
    assert "0221123456" in text and knoepfe is not None
    assert bot.offen.anruf and bot.offen.anruf.nummer == "0221123456"


@pytest.mark.asyncio
async def test_notruf_wird_nie_gewaehlt(tmp_path):
    ki = ErsatzKI([Auftrag(typ="anruf", ziel="Polizei", telefonnummer="110", auftrag="Etwas melden")])
    bot = TelegramBot(einstellungen(tmp_path), ki)
    upd, nachricht = update(text="Ruf die 110 an")
    await bot._textnachricht(upd, None)
    assert "nicht gewählt" in nachricht.antworten[-1][0]
    assert bot.offen.anruf is None


@pytest.mark.asyncio
async def test_niemand_nimmt_ab(tmp_path, monkeypatch):
    meldungen = []

    async def melden(text):
        meldungen.append(text)

    echtes_sleep = asyncio.sleep

    async def schnell(_):
        await echtes_sleep(0)

    monkeypatch.setattr(anrufe_modul.asyncio, "sleep", schnell)
    ari = ErsatzAri()
    verwaltung = Anrufverwaltung(einstellungen(tmp_path), ari, None, melden)
    await verwaltung.starten(Anruf(ziel="Da Mario", nummer="0221123456", auftrag="x", spielraum=""))
    with pytest.raises(RuntimeError):
        await verwaltung.starten(Anruf(ziel="Zweiter", nummer="0221999", auftrag="x", spielraum=""))
    for _ in range(50):
        if meldungen:
            break
        await echtes_sleep(0)
    assert ari.gewaehlt == ["0221123456"]
    assert meldungen and "niemand abgenommen" in meldungen[0]
    assert not verwaltung.beschaeftigt


# ---------- Berechtigung je Person (TELEGRAM_ERLAUBTE_NUTZER) ----------


@pytest.mark.asyncio
async def test_gruppe_ohne_erlaubte_nutzer_wird_abgelehnt(tmp_path):
    """In einer Gruppe dürfte sonst jedes Mitglied Anrufe auslösen."""
    bot = TelegramBot(einstellungen(tmp_path, chat_id=-100), ErsatzKI([]))
    upd, nachricht = update(chat_id=-100, art="supergroup", nutzer_id=7, text="Ruf 0221 123456 an")
    await bot._textnachricht(upd, None)
    assert len(nachricht.antworten) == 1 and "TELEGRAM_ERLAUBTE_NUTZER" in nachricht.antworten[0][0]
    upd, nachricht = update(chat_id=-100, art="group", nutzer_id=7, text="nochmal")
    await bot._textnachricht(upd, None)
    assert nachricht.antworten == [], "Hinweis nur einmal, nicht bei jeder Nachricht"


@pytest.mark.asyncio
async def test_gruppe_mit_erlaubten_nutzern(tmp_path):
    ki = ErsatzKI([Auftrag(typ="rueckfrage", rueckfrage="Wen soll ich anrufen?")])
    einst = replace(einstellungen(tmp_path, chat_id=-100), telegram_erlaubte_nutzer=frozenset({7}))
    bot = TelegramBot(einst, ki)
    upd, nachricht = update(chat_id=-100, art="group", nutzer_id=8, text="Ruf an")
    await bot._textnachricht(upd, None)
    assert nachricht.antworten == [] and ki.texte == []
    upd, nachricht = update(chat_id=-100, art="group", nutzer_id=7, text="Ruf an")
    await bot._textnachricht(upd, None)
    assert "Wen soll ich anrufen?" in nachricht.antworten[-1][0]


@pytest.mark.asyncio
async def test_privater_chat_mit_erlaubten_nutzern_prueft_die_person(tmp_path):
    einst = replace(einstellungen(tmp_path), telegram_erlaubte_nutzer=frozenset({7}))
    bot = TelegramBot(einst, ErsatzKI([]))
    upd, nachricht = update(chat_id=42, nutzer_id=42, text="Ruf 0221 123456 an")
    await bot._textnachricht(upd, None)
    assert nachricht.antworten == []


@pytest.mark.asyncio
async def test_ohne_absender_abgelehnt(tmp_path):
    einst = replace(einstellungen(tmp_path, chat_id=-100), telegram_erlaubte_nutzer=frozenset({7}))
    bot = TelegramBot(einst, ErsatzKI([]))
    upd, nachricht = update(chat_id=-100, art="channel", nutzer_id=None, text="Ruf an")
    await bot._textnachricht(upd, None)
    assert nachricht.antworten == []


# ---------- Mengenlimit für eingehende Anrufe (PC-Version) ----------


@pytest.mark.asyncio
async def test_eingehende_anrufe_ueber_dem_limit(tmp_path, monkeypatch):
    meldungen, gespraeche = [], []
    uhr = [0.0]

    async def melden(text):
        meldungen.append(text)

    async def schein_gespraech(websocket, *, zulassen, selbst_beginnen, **_):
        assert selbst_beginnen
        erlaubt = await zulassen("0221555")
        gespraeche.append(erlaubt)
        return Gespraechsergebnis(anrufer="0221555", abgelehnt=not erlaubt, ergebnis="Rückruf erbeten")

    class KI:
        async def bericht_schreiben(self, *args):
            return "Bericht"

    monkeypatch.setattr(anrufe_modul, "gespraech_fuehren", schein_gespraech)
    verwaltung = Anrufverwaltung(einstellungen(tmp_path), ErsatzAri(), KI(), melden)
    verwaltung.limit = Anruflimit(pro_nummer_tag=1, pro_stunde=10, uhr=lambda: uhr[0])

    await verwaltung.eingehend_verbunden(None)
    assert gespraeche == [True] and any("Anruf von 0221555" in m for m in meldungen)

    meldungen.clear()
    await verwaltung.eingehend_verbunden(None)
    assert gespraeche == [True, False]
    assert len(meldungen) == 1 and "nicht angenommen" in meldungen[0], meldungen

    uhr[0] += 25 * 3600
    await verwaltung.eingehend_verbunden(None)
    assert gespraeche == [True, False, True]


def test_limit_aus_den_einstellungen(tmp_path):
    einst = replace(einstellungen(tmp_path), eingehend_pro_nummer_tag=4, eingehend_pro_stunde=7)
    verwaltung = Anrufverwaltung(einst, ErsatzAri(), None, None)
    assert (verwaltung.limit.pro_nummer_tag, verwaltung.limit.pro_stunde) == (4, 7)
