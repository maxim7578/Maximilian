import json
from datetime import datetime, timezone

import pytest

from conftest import VIN, VIN2, ist_privat, nur_posix

from bmw_cardata.descriptors import LATITUDE, LONGITUDE
from bmw_cardata.history import (
    Entry,
    append_entry,
    delete_history,
    history_csv,
    history_lines,
    history_path,
    load_entries,
    prune_entries,
    without_location,
)

KM = "vehicle.vehicle.travelledDistance"
SOC = "vehicle.powertrain.electric.battery.stateOfCharge.displayed"


def _eintrag(zeit, km, vin=VIN, **weitere):
    daten = {KM: {"value": km, "unit": "km"}, **weitere}
    return Entry(zeit, vin, daten)


def test_verlauf_liegt_neben_der_anmeldedatei(tmp_path):
    assert history_path(tmp_path / "state.json") == tmp_path / "verlauf.jsonl"


def test_einträge_werden_angehängt_und_in_reihenfolge_geladen(tmp_path):
    pfad = tmp_path / "unter" / "verlauf.jsonl"
    erster, zweiter = _eintrag("2026-10-30T10:00:00Z", 100), _eintrag("2026-10-31T10:00:00Z", 150)
    append_entry(pfad, erster)
    append_entry(pfad, zweiter)
    assert load_entries(pfad) == [erster, zweiter]


def test_verlauf_ist_nur_für_den_eigenen_benutzer_lesbar(tmp_path):
    pfad = tmp_path / "verlauf.jsonl"
    append_entry(pfad, _eintrag("2026-10-30T10:00:00Z", 1))
    assert ist_privat(pfad)


def test_fehlender_verlauf_ist_leer_und_kaputte_zeilen_werden_übersprungen(tmp_path):
    pfad = tmp_path / "verlauf.jsonl"
    assert load_entries(pfad) == []
    append_entry(pfad, _eintrag("2026-10-30T10:00:00Z", 1))
    with pfad.open("a", encoding="utf-8") as datei:
        datei.write("kein json\n[1, 2]\n{\"zeit\": 5}\n\n")
    assert len(load_entries(pfad)) == 1


def test_verlaufszeilen_zeigen_werte_und_gefahrene_kilometer():
    eintraege = [
        _eintrag("2026-10-30T10:00:00Z", 42000, **{SOC: {"value": 80, "unit": "%"}}),
        _eintrag("2026-10-31T08:30:00Z", 42120),
    ]
    assert history_lines(eintraege, limit=10, tz=timezone.utc) == [
        "30.10.2026 10:00  Kilometerstand: 42000 km, Ladestand Hochvoltbatterie: 80 %",
        "31.10.2026 08:30  Kilometerstand: 42120 km  (+120 km)",
    ]


def test_verlauf_zeigt_nur_die_letzten_einträge_rechnet_aber_mit_dem_davor():
    eintraege = [_eintrag(f"2026-10-{tag}T10:00:00Z", km) for tag, km in ((28, 10), (29, 30), (30, 70))]
    zeilen = history_lines(eintraege, limit=1, tz=timezone.utc)
    assert zeilen == ["30.10.2026 10:00  Kilometerstand: 70 km  (+40 km)"]


def test_bei_mehreren_fahrzeugen_steht_die_fahrgestellnummer_dabei():
    eintraege = [_eintrag("2026-10-30T10:00:00Z", 5, VIN), _eintrag("2026-10-30T11:00:00Z", 9, VIN2)]
    zeilen = history_lines(eintraege, limit=10, tz=timezone.utc)
    assert zeilen[0].startswith(f"30.10.2026 10:00  {VIN}  ")
    assert "(+" not in zeilen[1]


def test_eintrag_ohne_werte_und_leerer_verlauf():
    leer = Entry("2026-10-30T10:00:00Z", VIN, {})
    assert history_lines([leer], limit=5, tz=timezone.utc) == ["30.10.2026 10:00  keine Werte"]
    assert "status --speichern" in history_lines([], limit=5)[0]


def test_unlesbare_zeit_wird_unverändert_gezeigt():
    assert history_lines([Entry("gestern", VIN, {})], limit=1) == ["gestern  keine Werte"]


def test_csv_export_mit_kopfzeile_und_rohwerten():
    text = history_csv([_eintrag("2026-10-30T10:00:00Z", 42000, **{SOC: {"value": 80, "unit": "%"}})])
    kopf, zeile = text.splitlines()
    spalten = kopf.split(";")
    werte = dict(zip(spalten, zeile.split(";")))
    assert spalten[:3] == ["zeit", "fahrgestellnummer", "Kilometerstand"]
    assert (werte["fahrgestellnummer"], werte["Kilometerstand"], werte["Ladestand Hochvoltbatterie"]) == (VIN, "42000", "80")


def test_csv_entschärft_formeln_aus_textwerten():
    daten = {"vehicle.cabin.door.lock.status": {"value": "=HYPERLINK(\"x\")"}}
    zeile = history_csv([Entry("2026-10-30T10:00:00Z", VIN, daten)]).splitlines()[1]
    assert "'=HYPERLINK" in zeile


def test_zeilen_mit_falschen_datentypen_werden_übersprungen(tmp_path):
    pfad = tmp_path / "verlauf.jsonl"
    pfad.write_text('{"zeit": 5, "fahrgestellnummer": "x", "werte": {}}\n', encoding="utf-8")
    assert load_entries(pfad) == []


def test_nicht_numerischer_kilometerstand_ergibt_keine_differenz():
    eintraege = [_eintrag("2026-10-30T10:00:00Z", "viel"), _eintrag("2026-10-31T10:00:00Z", 50)]
    assert "(+" not in history_lines(eintraege, limit=10, tz=timezone.utc)[1]


def test_kommazahlen_bei_der_differenz():
    eintraege = [_eintrag("2026-10-30T10:00:00Z", 10.5), _eintrag("2026-10-31T10:00:00Z", 12)]
    assert history_lines(eintraege, limit=10, tz=timezone.utc)[1].endswith("(+1.5 km)")


def test_ungültiges_utf8_im_verlauf_bricht_nicht_ab(tmp_path):
    pfad = tmp_path / "verlauf.jsonl"
    append_entry(pfad, _eintrag("2026-10-30T10:00:00Z", 1))
    with pfad.open("ab") as datei:
        datei.write(b"\xff\xfe kaputt\n")
    assert len(load_entries(pfad)) == 1


@nur_posix
def test_vorhandene_offene_verlaufsdatei_wird_auf_600_gesetzt(tmp_path):
    pfad = tmp_path / "verlauf.jsonl"
    pfad.write_text("")
    pfad.chmod(0o666)
    append_entry(pfad, _eintrag("2026-10-30T10:00:00Z", 1))
    assert ist_privat(pfad)


@nur_posix
def test_verlauf_folgt_keinem_symbolischen_link(tmp_path):
    ziel = tmp_path / "anderswo.txt"
    ziel.write_text("")
    pfad = tmp_path / "verlauf.jsonl"
    pfad.symlink_to(ziel)
    with pytest.raises(OSError):
        append_entry(pfad, _eintrag("2026-10-30T10:00:00Z", 1))
    assert ziel.read_text() == ""


def test_csv_kopf_nennt_die_einheit_des_reifendrucks():
    assert "Reifendruck vorne links (kPa)" in history_csv([]).splitlines()[0].split(";")


JETZT = datetime(2026, 11, 1, 12, 0, tzinfo=timezone.utc).timestamp()


def test_einträge_älter_als_die_frist_werden_entfernt_jüngere_bleiben_unverändert(tmp_path):
    pfad = tmp_path / "verlauf.jsonl"
    alt, grenze = _eintrag("2025-10-31T11:59:59Z", 1), _eintrag("2025-11-01T12:00:00Z", 2)
    jung = _eintrag("2026-10-31T10:00:00Z", 3, **{SOC: {"value": 80, "unit": "%"}})
    for eintrag in (alt, grenze, jung):
        append_entry(pfad, eintrag)
    jüngere_zeilen = pfad.read_text(encoding="utf-8").splitlines()[1:]
    assert prune_entries(pfad, 365, JETZT) == 1
    assert pfad.read_text(encoding="utf-8").splitlines() == jüngere_zeilen
    assert load_entries(pfad) == [grenze, jung]


def test_aufräumen_hält_die_rechte_600_und_hinterlässt_keine_zwischendatei(tmp_path):
    pfad = tmp_path / "verlauf.jsonl"
    append_entry(pfad, _eintrag("2020-01-01T00:00:00Z", 1))
    append_entry(pfad, _eintrag("2026-10-31T10:00:00Z", 2))
    assert prune_entries(pfad, 30, JETZT) == 1
    assert ist_privat(pfad)
    assert sorted(datei.name for datei in tmp_path.iterdir()) == ["verlauf.jsonl"]


def test_ohne_abgelaufene_einträge_wird_die_datei_nicht_neu_geschrieben(tmp_path, monkeypatch):
    import bmw_cardata.history as verlauf

    pfad = tmp_path / "verlauf.jsonl"
    append_entry(pfad, _eintrag("2026-10-31T10:00:00Z", 1))
    monkeypatch.setattr(verlauf, "write_private", lambda *args: pytest.fail("darf nicht schreiben"))
    assert prune_entries(pfad, 30, JETZT) == 0


def test_frist_null_bedeutet_unbegrenzt_aufbewahren(tmp_path):
    pfad = tmp_path / "verlauf.jsonl"
    append_entry(pfad, _eintrag("2001-01-01T00:00:00Z", 1))
    assert prune_entries(pfad, 0, JETZT) == 0
    assert len(load_entries(pfad)) == 1


def test_aufräumen_ohne_verlauf_tut_nichts(tmp_path):
    assert prune_entries(tmp_path / "verlauf.jsonl", 365, JETZT) == 0
    assert not (tmp_path / "verlauf.jsonl").exists()


def test_unlesbare_zeilen_bleiben_beim_aufräumen_erhalten(tmp_path):
    pfad = tmp_path / "verlauf.jsonl"
    append_entry(pfad, _eintrag("2001-01-01T00:00:00Z", 1))
    with pfad.open("a", encoding="utf-8") as datei:
        datei.write('kein json\n{"zeit": "gestern"}\n{"zeit": 5}\n')
    assert prune_entries(pfad, 365, JETZT) == 1
    assert pfad.read_text(encoding="utf-8").splitlines() == ["kein json", '{"zeit": "gestern"}', '{"zeit": 5}']


def test_zeit_ohne_zeitzone_gilt_als_utc(tmp_path):
    pfad = tmp_path / "verlauf.jsonl"
    pfad.write_text(json.dumps({"zeit": "2001-01-01T00:00:00", "fahrgestellnummer": VIN, "werte": {}}) + "\n")
    assert prune_entries(pfad, 365, JETZT) == 1


def test_ohne_standort_fallen_breiten_und_längengrad_weg():
    daten = {
        KM: {"value": 1},
        LATITUDE: {"value": 48.1},
        LONGITUDE: {"value": 11.5},
        "vehicle.cabin.infotainment.navigation.destinationSet.latitude": {"value": 52.5},
    }
    assert without_location(daten) == {KM: {"value": 1}}
    assert LATITUDE in daten  # das Original bleibt unverändert


def test_verlauf_löschen_entfernt_datei_und_reste_von_zwischendateien(tmp_path):
    pfad = tmp_path / "verlauf.jsonl"
    append_entry(pfad, _eintrag("2026-10-31T10:00:00Z", 1))
    (tmp_path / ".verlauf.jsonl.abc123.tmp").write_text("rest")
    (tmp_path / "state.json").write_text("{}")
    assert delete_history(pfad) is True
    assert sorted(datei.name for datei in tmp_path.iterdir()) == ["state.json"]
    assert delete_history(pfad) is False


def test_aufräumen_erhält_ungültiges_utf8_und_zeilentrenner_im_text(tmp_path):
    pfad = tmp_path / "verlauf.jsonl"
    append_entry(pfad, _eintrag("2001-01-01T00:00:00Z", 1))
    append_entry(pfad, _eintrag("2026-10-31T10:00:00Z", "a\u2028b"))
    with pfad.open("ab") as datei:
        datei.write(b"\xff\xfe kaputt\n")
    rest = pfad.read_bytes().splitlines()[1:]  # Zeilenenden je nach System \n oder \r\n
    assert prune_entries(pfad, 365, JETZT) == 1
    assert pfad.read_bytes().splitlines() == rest
    assert load_entries(pfad)[0].data[KM]["value"] == "a\u2028b"


@nur_posix
def test_aufräumen_folgt_keinem_symbolischen_link(tmp_path):
    ziel = tmp_path / "anderswo.jsonl"
    ziel.write_text(json.dumps({"zeit": "2001-01-01T00:00:00Z"}) + "\n")
    pfad = tmp_path / "verlauf.jsonl"
    pfad.symlink_to(ziel)
    with pytest.raises(OSError):
        prune_entries(pfad, 365, JETZT)
    assert "2001" in ziel.read_text()
