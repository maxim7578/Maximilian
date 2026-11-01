"""Handy-Version: Mengenlimit für eingehende Anrufe – über dem Limit wird gar nicht abgehoben."""

import asyncio
from dataclasses import replace
from types import SimpleNamespace

import pytest

from assistent.anruflimit import Anruflimit
from assistent.handy.anrufe import HandyAnrufverwaltung
from tests.test_ablauf import einstellungen


def verwaltung_bauen(tmp_path, eingehend=True):
    meldungen = []

    async def melden(text):
        meldungen.append(text)

    telefon = SimpleNamespace(bei_eingehendem_anruf=None, eingehend_zulassen=None)
    einst = replace(einstellungen(tmp_path), eingehende_anrufe=eingehend)
    return HandyAnrufverwaltung(einst, telefon, None, None, melden), telefon, meldungen


@pytest.mark.asyncio
async def test_limit_wird_vor_dem_abheben_gefragt(tmp_path):
    verwaltung, telefon, meldungen = verwaltung_bauen(tmp_path)
    uhr = [0.0]
    verwaltung.limit = Anruflimit(pro_nummer_tag=1, pro_stunde=10, uhr=lambda: uhr[0])
    assert telefon.eingehend_zulassen("0221555") is True
    assert telefon.eingehend_zulassen("0221555") is False
    await asyncio.sleep(0)
    assert len(meldungen) == 1 and "nicht angenommen" in meldungen[0]
    uhr[0] += 25 * 3600
    assert telefon.eingehend_zulassen("0221555") is True


def test_ohne_eingehende_anrufe_kein_limit_noetig(tmp_path):
    _, telefon, _ = verwaltung_bauen(tmp_path, eingehend=False)
    assert telefon.bei_eingehendem_anruf is None and telefon.eingehend_zulassen is None


def test_limit_aus_den_einstellungen(tmp_path):
    verwaltung, _, _ = verwaltung_bauen(tmp_path)
    assert (verwaltung.limit.pro_nummer_tag, verwaltung.limit.pro_stunde) == (3, 10)
