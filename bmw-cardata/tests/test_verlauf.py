import stat
from datetime import timezone

import pytest

from conftest import VIN, VIN2

from bmw_cardata.history import Entry, append_entry, history_csv, history_lines, history_path, load_entries

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
    assert stat.S_IMODE(pfad.stat().st_mode) == 0o600


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


def test_vorhandene_offene_verlaufsdatei_wird_auf_600_gesetzt(tmp_path):
    pfad = tmp_path / "verlauf.jsonl"
    pfad.write_text("")
    pfad.chmod(0o666)
    append_entry(pfad, _eintrag("2026-10-30T10:00:00Z", 1))
    assert stat.S_IMODE(pfad.stat().st_mode) == 0o600


def test_verlauf_folgt_keinem_symbolischen_link(tmp_path):
    ziel = tmp_path / "anderswo.txt"
    ziel.write_text("")
    pfad = tmp_path / "verlauf.jsonl"
    pfad.symlink_to(ziel)
    with pytest.raises(OSError):
        append_entry(pfad, _eintrag("2026-10-30T10:00:00Z", 1))
    assert ziel.read_text() == ""
