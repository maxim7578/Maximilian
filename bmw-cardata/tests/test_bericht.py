import json

from bmw_cardata.descriptors import STATUS_FIELDS, STATUS_GROUPS, all_descriptors, descriptor_signature
from bmw_cardata.report import basic_data_lines, format_value, map_link, status_json, status_lines


def test_wert_mit_einheit():
    assert format_value({"value": 12345, "unit": "km"}) == "12345 km"


def test_wahrheitswerte_werden_übersetzt():
    assert format_value({"value": True}) == "ja"
    assert format_value({"value": "false"}) == "nein"


def test_leere_werte_gelten_als_fehlend():
    assert format_value({"value": None}) is None
    assert format_value({"value": ""}) is None


def test_statusbericht_zeigt_vorhandene_felder_mit_zeitstempel():
    daten = {
        "vehicle.vehicle.travelledDistance": {"value": 42000, "unit": "km", "timestamp": "2026-10-30T10:00:00Z"},
        "vehicle.drivetrain.electricEngine.charging.status": {"value": "CHARGINGACTIVE"},
    }
    assert status_lines(daten) == [
        "Fahren und Reichweite",
        "  Kilometerstand: 42000 km  (Stand: 2026-10-30T10:00:00Z)",
        "Laden",
        "  Ladestatus: CHARGINGACTIVE",
    ]


def test_ersatz_datenpunkt_wird_genutzt_wenn_der_erste_fehlt():
    daten = {
        "vehicle.drivetrain.batteryManagement.header": {"value": None},
        "vehicle.powertrain.electric.battery.stateOfCharge.displayed": {"value": 80, "unit": "%"},
    }
    assert status_lines(daten) == ["Laden", "  Ladestand Hochvoltbatterie: 80 %"]


def test_ohne_daten_kommt_ein_hinweis_statt_einer_leeren_ausgabe():
    zeilen = status_lines({})
    assert len(zeilen) == 1
    assert "My-BMW-App" in zeilen[0]


def test_basisdaten_sortiert_und_ohne_leere_felder():
    assert basic_data_lines({"modelName": "i3", "brand": "BMW", "colour": ""}) == ["brand: BMW", "modelName: i3"]
    assert basic_data_lines({}) == ["Keine Basisdaten vorhanden."]


def test_jeder_datenpunkt_kommt_nur_einmal_vor():
    punkte = all_descriptors()
    assert len(punkte) == len(set(punkte))
    assert all(p.startswith("vehicle.") for p in punkte)
    assert len(STATUS_FIELDS) >= 40


BREITE = "vehicle.cabin.infotainment.navigation.currentLocation.latitude"
LAENGE = "vehicle.cabin.infotainment.navigation.currentLocation.longitude"


def test_position_ergibt_einen_kartenlink():
    daten = {BREITE: {"value": 48.1772}, LAENGE: {"value": "11.5562"}}
    assert map_link(daten) == "https://www.openstreetmap.org/?mlat=48.1772&mlon=11.5562#map=17/48.1772/11.5562"
    assert status_lines(daten)[-1] == f"  Karte: {map_link(daten)}"


def test_ohne_gültige_position_gibt_es_keinen_kartenlink():
    assert map_link({BREITE: {"value": 48.1}}) is None
    assert map_link({BREITE: {"value": 91}, LAENGE: {"value": 11}}) is None
    assert map_link({BREITE: {"value": "abc"}, LAENGE: {"value": 11}}) is None
    assert map_link({BREITE: {"value": True}, LAENGE: {"value": 11}}) is None


def test_json_ausgabe_enthält_nur_die_abgefragten_datenpunkte():
    daten = {"vehicle.vehicle.travelledDistance": {"value": 5, "unit": "km"}, "fremd.punkt": {"value": 1}}
    ergebnis = json.loads(status_json("WBA12345678901234", daten, "2026-10-31T10:00:00Z"))
    assert ergebnis == {
        "fahrgestellnummer": "WBA12345678901234",
        "abgerufen": "2026-10-31T10:00:00Z",
        "werte": {"vehicle.vehicle.travelledDistance": {"value": 5, "unit": "km"}},
    }


def test_steuerzeichen_in_werten_werden_entfernt():
    assert format_value({"value": "zu\x1b[31m‮", "unit": "\x07km"}) == "zu[31m km"


def test_neue_datenpunkte_stehen_in_ihren_gruppen():
    daten = {
        "vehicle.chassis.axle.row1.wheel.left.tire.pressure": {"value": 240, "unit": "kPa"},
        "vehicle.cabin.window.row1.driver.status": {"value": "INTERMEDIATE"},
        "vehicle.body.trunk.isOpen": {"value": False},
        "vehicle.electricalSystem.battery.voltage": {"value": 12.4, "unit": "V"},
    }
    assert status_lines(daten) == [
        "Türen, Fenster und Klappen",
        "  Fenster Fahrer: teilweise offen",
        "  Heckklappe offen: nein",
        "Reifen",
        "  Reifendruck vorne links: 2.40 bar (240 kPa)",
        "Wartung und Bordnetz",
        "  12-V-Spannung: 12.4 V",
    ]


def test_öffnungswerte_werden_übersetzt():
    assert format_value({"value": "CLOSED"}) == "geschlossen"
    assert format_value({"value": "OPEN"}) == "offen"
    assert format_value({"value": "invalid"}) == "ungültig"
    assert format_value({"value": "SECURED"}) == "SECURED"


def test_reifendruck_nur_bei_kpa_und_zahlen_umgerechnet():
    assert format_value({"value": "240", "unit": "kPa"}) == "2.40 bar (240 kPa)"
    assert format_value({"value": "hoch", "unit": "kPa"}) == "hoch kPa"
    assert format_value({"value": True, "unit": "kPa"}) == "ja"
    assert format_value({"value": "INVALID", "unit": "kPa"}) == "ungültig"
    assert format_value({"value": "nan", "unit": "kPa"}) == "nan kPa"
    assert format_value({"value": 2.4, "unit": "bar"}) == "2.4 bar"


def test_gruppen_enthalten_jedes_feld_genau_einmal():
    aus_gruppen = [feld for gruppe in STATUS_GROUPS for feld in gruppe.fields]
    assert tuple(aus_gruppen) == STATUS_FIELDS
    assert len({feld.label for feld in STATUS_FIELDS}) == len(STATUS_FIELDS)


def test_signatur_hängt_nur_von_den_datenpunkten_ab():
    assert descriptor_signature() == descriptor_signature()
    assert descriptor_signature(("b", "a")) == descriptor_signature(("a", "b"))
    assert descriptor_signature(("a",)) != descriptor_signature(("a", "b"))
    assert len(descriptor_signature()) == 16
