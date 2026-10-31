from conftest import VIN

from bmw_cardata.alert_store import load_alert_state
from bmw_cardata.alert_watch import AlertWatcher
from bmw_cardata.alerts import AlertSettings
from bmw_cardata.ntfy import NtfyError

HECK = "vehicle.body.trunk.isOpen"
SOC = "vehicle.drivetrain.batteryManagement.header"
LADEN = "vehicle.drivetrain.electricEngine.charging.status"


def _waechter(tmp_path, push=True, fehler=None):
    gemeldet, gepusht = [], []

    def senden(titel, zeilen):
        if fehler:
            raise NtfyError(fehler)
        gepusht.append((titel, zeilen))

    waechter = AlertWatcher(AlertSettings(), tmp_path / "z.json", senden if push else None, gemeldet.append)
    return waechter, gemeldet, gepusht


def test_neue_warnung_wird_gemeldet_und_gepusht_aber_nur_einmal(tmp_path):
    waechter, gemeldet, gepusht = _waechter(tmp_path)
    daten = {HECK: {"value": True}}
    assert [a.key for a in waechter.check(VIN, daten)] == ["offen:Heckklappe offen"]
    assert gemeldet == ["Warnung: Heckklappe offen"]
    assert gepusht == [("BMW …1234: 1 Warnung", ["Heckklappe offen"])]
    assert waechter.check(VIN, daten) == []
    assert len(gepusht) == 1


def test_behobene_warnung_meldet_sich_beim_nächsten_auftreten_wieder(tmp_path):
    waechter, gemeldet, _ = _waechter(tmp_path)
    waechter.check(VIN, {HECK: {"value": True}})
    waechter.check(VIN, {HECK: {"value": False}})
    waechter.check(VIN, {HECK: {"value": True}})
    assert gemeldet.count("Warnung: Heckklappe offen") == 2


def test_mehrere_warnungen_in_einem_push(tmp_path):
    waechter, _, gepusht = _waechter(tmp_path)
    waechter.check(VIN, {HECK: {"value": True}, SOC: {"value": 10, "unit": "%"}})
    assert gepusht[0][0] == "BMW …1234: 2 Warnungen"


def test_live_daten_werden_zusammengeführt(tmp_path):
    waechter, gemeldet, _ = _waechter(tmp_path)
    waechter.check(VIN, {HECK: {"value": True}}, merge=True)
    assert waechter.check(VIN, {SOC: {"value": 80, "unit": "%"}}, merge=True) == []
    assert load_alert_state(tmp_path / "z.json", VIN)["aktiv"] == ["offen:Heckklappe offen"]


def test_ohne_daten_zur_warnung_bleibt_sie_aktiv(tmp_path):
    waechter, gemeldet, _ = _waechter(tmp_path)
    waechter.check(VIN, {HECK: {"value": True}})
    waechter.check(VIN, {SOC: {"value": 80, "unit": "%"}})
    waechter.check(VIN, {HECK: {"value": True}})
    assert gemeldet.count("Warnung: Heckklappe offen") == 1


def test_laden_beendet(tmp_path):
    waechter, gemeldet, _ = _waechter(tmp_path)
    waechter.check(VIN, {LADEN: {"value": "CHARGINGACTIVE"}})
    waechter.check(VIN, {LADEN: {"value": "NOCHARGING"}})
    assert gemeldet == ["Warnung: Laden beendet (NOCHARGING)"]


def test_push_fehler_wird_gemeldet_ohne_abbruch(tmp_path):
    waechter, gemeldet, _ = _waechter(tmp_path, fehler="Push nicht zugestellt (HTTP 500).")
    waechter.check(VIN, {HECK: {"value": True}})
    assert gemeldet == ["Warnung: Heckklappe offen",
                        "Hinweis: Push nicht zugestellt (HTTP 500). Erneuter Versuch beim nächsten Mal."]


def test_ohne_push_nur_meldung(tmp_path):
    waechter, gemeldet, gepusht = _waechter(tmp_path, push=False)
    waechter.check(VIN, {HECK: {"value": True}})
    assert gemeldet == ["Warnung: Heckklappe offen"] and gepusht == []


def test_gescheiterter_push_wird_beim_nächsten_mal_wiederholt(tmp_path):
    waechter, gemeldet, _ = _waechter(tmp_path, fehler="Push nicht zugestellt (HTTP 503).")
    waechter.check(VIN, {HECK: {"value": True}})
    assert load_alert_state(tmp_path / "z.json", VIN)["aktiv"] == []
    waechter.push = lambda titel, zeilen: gemeldet.append(f"gepusht: {zeilen}")
    waechter.check(VIN, {HECK: {"value": True}})
    assert gemeldet[-1] == "gepusht: ['Heckklappe offen']"
    assert load_alert_state(tmp_path / "z.json", VIN)["aktiv"] == ["offen:Heckklappe offen"]


def test_gescheiterter_push_von_laden_beendet_wird_wiederholt(tmp_path):
    waechter, gemeldet, _ = _waechter(tmp_path, fehler="weg")
    waechter.check(VIN, {LADEN: {"value": "CHARGINGACTIVE"}})
    waechter.check(VIN, {LADEN: {"value": "NOCHARGING"}})
    assert load_alert_state(tmp_path / "z.json", VIN)["ladestatus"] == "CHARGINGACTIVE"
    waechter.push = lambda titel, zeilen: gemeldet.append(f"gepusht: {zeilen}")
    waechter.check(VIN, {LADEN: {"value": "NOCHARGING"}})
    assert gemeldet[-1] == "gepusht: ['Laden beendet (NOCHARGING)']"


def test_beschädigter_zustand_bricht_nichts_ab(tmp_path):
    import json

    pfad = tmp_path / "z.json"
    for inhalt in ({VIN: {"aktiv": 5}}, {VIN: {"aktiv": [1]}}, {VIN: {"ladestatus": ["x"]}}):
        pfad.write_text(json.dumps(inhalt))
        assert load_alert_state(pfad, VIN) == {}
    waechter, gemeldet, _ = _waechter(tmp_path)
    waechter.check(VIN, {HECK: {"value": True}})
    assert gemeldet == ["Warnung: Heckklappe offen"]
