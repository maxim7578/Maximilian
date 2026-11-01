"""Tests der Fehlerspeicher-Auswertung."""

from bmw_hu_info.fehler_analyse import analysiere

BEISPIEL = """[    0.000000] Booting Linux
[    3.111222] mmc1: error -110 whilst initialising SD card
[    4.222333] WARNING: CPU: 1 PID: 88 at drivers/gpu/hmi.c:204
Oct 31 11:40:02 bmw-nbtevo hmi[412]: failed to load skin 'night'
Oct 31 11:41:15 bmw-nbtevo connd[511]: BT a2dp stream reset
[    9.900000] mmc2: error -110 whilst initialising SD card
"""


def test_zaehlt_fehler_und_warnungen():
    bericht = analysiere(BEISPIEL)
    assert bericht.fehler == 3  # 2x mmc error + 1x failed
    assert bericht.warnungen == 1  # WARNING


def test_zaehlt_gesamtzeilen_ohne_leerzeilen():
    bericht = analysiere(BEISPIEL)
    assert bericht.gesamt_zeilen == 6


def test_gruppiert_aehnliche_meldungen():
    bericht = analysiere(BEISPIEL)
    # Die zwei mmc-Fehler unterscheiden sich nur in Zahlen -> gruppiert.
    top_meldung, anzahl = bericht.haeufigste[0]
    assert anzahl == 2
    assert "error" in top_meldung.lower()
    assert "#" in top_meldung  # Zahlen wurden normalisiert


def test_leerer_text_ergibt_nullbericht():
    bericht = analysiere("")
    assert bericht.gesamt_zeilen == 0
    assert bericht.fehler == 0
    assert bericht.warnungen == 0
    assert bericht.haeufigste == ()


def test_als_text_enthaelt_kennzahlen():
    text = analysiere(BEISPIEL).als_text()
    assert "Fehler:" in text
    assert "Warnungen:" in text
