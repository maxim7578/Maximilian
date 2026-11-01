"""Einstellungen aus der Datei .env: Mengenlimit und erlaubte Telegram-Nutzer."""

import pytest

from assistent.einstellungen import Einstellungen, EinstellungsFehler

PFLICHT = {"TELEGRAM_BOT_TOKEN": "123:abc", "GROQ_API_KEY": "gsk_x", "INHABER_NAME": "Herrn Koch"}


@pytest.fixture
def umgebung(monkeypatch):
    for name in ("EINGEHEND_MAX_PRO_NUMMER_TAG", "EINGEHEND_MAX_PRO_STUNDE", "TELEGRAM_ERLAUBTE_NUTZER"):
        monkeypatch.delenv(name, raising=False)
    for name, wert in PFLICHT.items():
        monkeypatch.setenv(name, wert)
    return monkeypatch


def test_standardwerte(umgebung):
    einst = Einstellungen.laden()
    assert einst.eingehend_pro_nummer_tag == 3
    assert einst.eingehend_pro_stunde == 10
    assert einst.telegram_erlaubte_nutzer == frozenset()


def test_limits_einstellbar(umgebung):
    umgebung.setenv("EINGEHEND_MAX_PRO_NUMMER_TAG", "5")
    umgebung.setenv("EINGEHEND_MAX_PRO_STUNDE", "0")
    einst = Einstellungen.laden()
    assert (einst.eingehend_pro_nummer_tag, einst.eingehend_pro_stunde) == (5, 0)


@pytest.mark.parametrize("wert", ["-1", "abc", "2.5"])
def test_ungueltige_limits(umgebung, wert):
    umgebung.setenv("EINGEHEND_MAX_PRO_STUNDE", wert)
    with pytest.raises(EinstellungsFehler):
        Einstellungen.laden()


def test_erlaubte_nutzer_kommagetrennt(umgebung):
    umgebung.setenv("TELEGRAM_ERLAUBTE_NUTZER", "123, 456,789")
    assert Einstellungen.laden().telegram_erlaubte_nutzer == frozenset({123, 456, 789})


@pytest.mark.parametrize("wert", ["abc", "123;456", "12 34"])
def test_ungueltige_erlaubte_nutzer(umgebung, wert):
    umgebung.setenv("TELEGRAM_ERLAUBTE_NUTZER", wert)
    with pytest.raises(EinstellungsFehler):
        Einstellungen.laden()
