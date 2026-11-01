"""Mengenlimit für eingehende KI-Gespräche – mit simulierter Uhr."""

import pytest

from assistent.anruflimit import Anruflimit

STUNDE = 3600
TAG = 24 * STUNDE


class Uhr:
    def __init__(self):
        self.jetzt = 1000.0

    def __call__(self) -> float:
        return self.jetzt


@pytest.fixture
def uhr():
    return Uhr()


def test_unter_dem_limit_wird_angenommen(uhr):
    limit = Anruflimit(pro_nummer_tag=2, pro_stunde=10, uhr=uhr)
    assert limit.pruefen("0221123456").erlaubt
    assert limit.pruefen("0221123456").erlaubt


def test_zu_viele_anrufe_derselben_nummer_am_tag(uhr):
    limit = Anruflimit(pro_nummer_tag=2, pro_stunde=10, uhr=uhr)
    limit.pruefen("0221123456")
    uhr.jetzt += 2 * STUNDE
    limit.pruefen("0221123456")
    uhr.jetzt += 2 * STUNDE
    ergebnis = limit.pruefen("0221123456")
    assert not ergebnis.erlaubt
    assert "0221123456" in ergebnis.meldung
    assert limit.pruefen("0301234567").erlaubt, "andere Nummern sind nicht betroffen"


def test_nach_einem_tag_wieder_erlaubt(uhr):
    limit = Anruflimit(pro_nummer_tag=1, pro_stunde=10, uhr=uhr)
    assert limit.pruefen("0221123456").erlaubt
    uhr.jetzt += TAG - 1
    assert not limit.pruefen("0221123456").erlaubt
    uhr.jetzt += 2
    assert limit.pruefen("0221123456").erlaubt


def test_zu_viele_anrufe_insgesamt_pro_stunde(uhr):
    limit = Anruflimit(pro_nummer_tag=5, pro_stunde=3, uhr=uhr)
    for i in range(3):
        assert limit.pruefen(f"02211234{i}").erlaubt
    ergebnis = limit.pruefen("0301234567")
    assert not ergebnis.erlaubt and "Stunde" in ergebnis.meldung
    uhr.jetzt += STUNDE + 1
    assert limit.pruefen("0301234567").erlaubt


def test_abgelehnte_anrufe_zaehlen_nicht_mit(uhr):
    """Sonst bliebe eine Nummer, die es dauernd versucht, für immer gesperrt."""
    limit = Anruflimit(pro_nummer_tag=1, pro_stunde=10, uhr=uhr)
    limit.pruefen("0221123456")
    for _ in range(20):
        uhr.jetzt += STUNDE
        limit.pruefen("0221123456")
    uhr.jetzt += 5 * STUNDE  # gut 25 Stunden nach dem ersten Anruf
    assert limit.pruefen("0221123456").erlaubt


def test_unterdrueckte_nummern_teilen_sich_ein_limit(uhr):
    limit = Anruflimit(pro_nummer_tag=1, pro_stunde=10, uhr=uhr)
    assert limit.pruefen("").erlaubt
    ergebnis = limit.pruefen("")
    assert not ergebnis.erlaubt and "unterdrückt" in ergebnis.meldung


def test_meldung_nur_einmal_pro_stunde(uhr):
    """Wer es immer wieder versucht, soll Telegram nicht mit Meldungen fluten."""
    limit = Anruflimit(pro_nummer_tag=1, pro_stunde=10, uhr=uhr)
    limit.pruefen("0221123456")
    assert limit.pruefen("0221123456").meldung
    uhr.jetzt += 60
    zweite = limit.pruefen("0221123456")
    assert not zweite.erlaubt and zweite.meldung == ""
    uhr.jetzt += STUNDE
    assert limit.pruefen("0221123456").meldung


def test_null_bedeutet_ohne_grenze(uhr):
    limit = Anruflimit(pro_nummer_tag=0, pro_stunde=0, uhr=uhr)
    assert all(limit.pruefen("0221123456").erlaubt for _ in range(100))


@pytest.mark.parametrize("pro_nummer_tag, pro_stunde", [(-1, 10), (3, -1)])
def test_negative_werte_sind_ungueltig(pro_nummer_tag, pro_stunde):
    with pytest.raises(ValueError):
        Anruflimit(pro_nummer_tag=pro_nummer_tag, pro_stunde=pro_stunde)
