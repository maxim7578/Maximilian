from bmw_cardata.descriptors import STATUS_FIELDS, all_descriptors
from bmw_cardata.report import basic_data_lines, format_value, status_lines


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
        "Kilometerstand: 42000 km  (Stand: 2026-10-30T10:00:00Z)",
        "Ladestatus: CHARGINGACTIVE",
    ]


def test_ersatz_datenpunkt_wird_genutzt_wenn_der_erste_fehlt():
    daten = {
        "vehicle.drivetrain.batteryManagement.header": {"value": None},
        "vehicle.powertrain.electric.battery.stateOfCharge.displayed": {"value": 80, "unit": "%"},
    }
    assert status_lines(daten) == ["Ladestand Hochvoltbatterie: 80 %"]


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
    assert len(STATUS_FIELDS) >= 10
