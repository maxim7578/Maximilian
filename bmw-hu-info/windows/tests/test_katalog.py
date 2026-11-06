"""Tests fuer das Laden und Filtern des Befehlskatalogs."""

import json

import pytest

from bmw_hu_info.catalog import lade_katalog


def test_laedt_standardkatalog():
    katalog = lade_katalog()
    assert katalog.version >= 1
    assert len(katalog.kategorien) > 0


def test_findet_systemkategorie():
    katalog = lade_katalog()
    ids = {k.id for k in katalog.kategorien}
    assert "system" in ids
    assert "fehlerspeicher" in ids


def test_filtert_auf_headunit_nbt():
    katalog = lade_katalog().fuer_headunit("NBT")
    for kategorie in katalog.kategorien:
        for befehl in kategorie.befehle:
            assert "NBT" in befehl.headunits


def test_filter_entfernt_leere_kategorien():
    katalog = lade_katalog().fuer_headunit("NBT")
    for kategorie in katalog.kategorien:
        assert len(kategorie.befehle) > 0


def test_erkennt_platzhalterbefehl():
    katalog = lade_katalog()
    platzhalter = [
        b
        for k in katalog.kategorien
        for b in k.befehle
        if b.hat_platzhalter
    ]
    assert len(platzhalter) > 0


def test_meldet_defektes_json(tmp_path):
    kaputt = tmp_path / "kaputt.json"
    kaputt.write_text("{ das ist kein json", encoding="utf-8")
    with pytest.raises(ValueError):
        lade_katalog(kaputt)


def test_meldet_fehlende_datei(tmp_path):
    with pytest.raises(FileNotFoundError):
        lade_katalog(tmp_path / "gibtsnicht.json")


def test_meldet_falsches_format(tmp_path):
    datei = tmp_path / "format.json"
    datei.write_text(json.dumps({"version": 1}), encoding="utf-8")
    with pytest.raises(ValueError):
        lade_katalog(datei)
