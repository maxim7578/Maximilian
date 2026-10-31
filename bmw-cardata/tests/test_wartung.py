import json

from conftest import VIN, VIN2, ist_privat

from bmw_cardata.api import CarDataApi
from bmw_cardata.maintenance import MAX_AGE_SECONDS, maintenance_path, maintenance_values

CONTAINERS = "/customers/containers"
TELEMATIK = f"/customers/vehicles/{VIN}/telematicData"
SERVICE = "vehicle.status.serviceDistance.next"
WERTE = {SERVICE: {"value": 12000, "unit": "km"}}


def _abrufen(bmw, pfad, jetzt=1_000_000.0, vin=VIN):
    return maintenance_values(CarDataApi(bmw.client(), "zugang"), vin, pfad, jetzt, "2026-10-31")


def _erstmals(bmw):
    bmw.add("GET", CONTAINERS, body=[])
    bmw.add("POST", CONTAINERS, status=201, body={"containerId": "wartung-1"})


def test_wartungsdatei_liegt_neben_der_anmeldedatei(tmp_path):
    assert maintenance_path(tmp_path / "state.json") == tmp_path / "wartung.json"


def test_erster_abruf_legt_den_container_an_und_speichert_die_werte(bmw, tmp_path):
    pfad = tmp_path / "wartung.json"
    _erstmals(bmw)
    bmw.add("GET", TELEMATIK, body={"telematicData": WERTE})
    assert _abrufen(bmw, pfad) == (WERTE, [])
    gespeichert = json.loads(pfad.read_text())
    assert gespeichert["container_id"] == "wartung-1"
    assert ist_privat(pfad)
    anlegen = json.loads(bmw.requests[1].content)
    assert anlegen["name"] == "bmw-cardata-cli Wartung"
    assert set(anlegen["technicalDescriptors"]) == {SERVICE, "vehicle.status.serviceTime.inspectionDateLegal"}


def test_innerhalb_eines_tages_kein_weiterer_abruf(bmw, tmp_path):
    pfad = tmp_path / "wartung.json"
    _erstmals(bmw)
    bmw.add("GET", TELEMATIK, body={"telematicData": WERTE})
    _abrufen(bmw, pfad)
    anzahl = len(bmw.requests)
    assert _abrufen(bmw, pfad, jetzt=1_000_000.0 + MAX_AGE_SECONDS - 1) == (WERTE, [])
    assert len(bmw.requests) == anzahl


def test_nach_einem_tag_wird_mit_dem_gespeicherten_container_neu_abgerufen(bmw, tmp_path):
    pfad = tmp_path / "wartung.json"
    _erstmals(bmw)
    bmw.add("GET", TELEMATIK, body={"telematicData": WERTE})
    _abrufen(bmw, pfad)
    _abrufen(bmw, pfad, jetzt=1_000_000.0 + MAX_AGE_SECONDS)
    assert [r.url.path for r in bmw.requests].count(CONTAINERS) == 2
    assert [r.url.path for r in bmw.requests].count(TELEMATIK) == 2


def test_fehler_behält_alte_werte_und_wartet_einen_tag(bmw, tmp_path):
    pfad = tmp_path / "wartung.json"
    _erstmals(bmw)
    bmw.add("GET", TELEMATIK, body={"telematicData": WERTE})
    bmw.add("GET", TELEMATIK, status=400, body={"code": "CU-400"})
    _abrufen(bmw, pfad)
    werte, hinweise = _abrufen(bmw, pfad, jetzt=1_000_000.0 + MAX_AGE_SECONDS)
    assert werte == WERTE
    assert "CU-400" in hinweise[0] and "morgen" in hinweise[0]
    anzahl = len(bmw.requests)
    assert _abrufen(bmw, pfad, jetzt=1_000_000.0 + MAX_AGE_SECONDS + 60) == (WERTE, [])
    assert len(bmw.requests) == anzahl


def test_tageslimit_wird_beim_nächsten_aufruf_erneut_versucht(bmw, tmp_path):
    pfad = tmp_path / "wartung.json"
    bmw.add("GET", CONTAINERS, status=429)
    werte, hinweise = _abrufen(bmw, pfad)
    assert werte == {} and "Tageslimit" in hinweise[0]
    assert not pfad.exists()


def test_verschwundener_wartungscontainer_wird_vergessen(bmw, tmp_path):
    pfad = tmp_path / "wartung.json"
    pfad.write_text(json.dumps({"container_id": "weg", "signatur": "x", "fahrzeuge": {}}))
    bmw.add("GET", CONTAINERS, body=[])
    bmw.add("POST", CONTAINERS, status=201, body={"containerId": "neu"})
    bmw.add("DELETE", f"{CONTAINERS}/weg", status=404)
    bmw.add("GET", TELEMATIK, status=403, body={"code": "CU-105"})
    _abrufen(bmw, pfad)
    assert json.loads(pfad.read_text())["container_id"] is None


def test_jedes_fahrzeug_hat_seinen_eigenen_stand(bmw, tmp_path):
    pfad = tmp_path / "wartung.json"
    _erstmals(bmw)
    bmw.add("GET", TELEMATIK, body={"telematicData": WERTE})
    bmw.add("GET", f"/customers/vehicles/{VIN2}/telematicData", body={"telematicData": {}})
    _abrufen(bmw, pfad)
    assert _abrufen(bmw, pfad, vin=VIN2) == ({}, [])
    assert set(json.loads(pfad.read_text())["fahrzeuge"]) == {VIN, VIN2}


def test_beschädigte_wartungsdatei_wird_ersetzt(bmw, tmp_path):
    pfad = tmp_path / "wartung.json"
    pfad.write_text("[kein objekt")
    _erstmals(bmw)
    bmw.add("GET", TELEMATIK, body={"telematicData": WERTE})
    assert _abrufen(bmw, pfad)[0] == WERTE


def test_falsche_typen_in_der_wartungsdatei_werden_ignoriert(bmw, tmp_path):
    pfad = tmp_path / "wartung.json"
    pfad.write_text(json.dumps({"container_id": 5, "fahrzeuge": {VIN: {"versucht": 999_999.0, "werte": [1]}}}))
    assert _abrufen(bmw, pfad) == ({}, [])
    pfad.write_text(json.dumps({"fahrzeuge": []}))
    _erstmals(bmw)
    bmw.add("GET", TELEMATIK, body={"telematicData": WERTE})
    assert _abrufen(bmw, pfad)[0] == WERTE


def test_nicht_schreibbare_wartungsdatei_bricht_nichts_ab(bmw, tmp_path, monkeypatch):
    import bmw_cardata.maintenance as wartung

    def kaputt(*args):
        raise PermissionError("kein Zugriff")

    monkeypatch.setattr(wartung, "write_private", kaputt)
    _erstmals(bmw)
    bmw.add("GET", TELEMATIK, body={"telematicData": WERTE})
    assert _abrufen(bmw, tmp_path / "wartung.json")[0] == WERTE
