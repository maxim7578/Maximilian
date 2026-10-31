import pytest
from conftest import VIN, VIN2

from bmw_cardata.api import ApiError, CarDataApi, RateLimitError
from bmw_cardata.descriptors import CONTAINER_NAME, CONTAINER_PURPOSE, all_descriptors, descriptor_signature
from bmw_cardata.service import (
    Session,
    ensure_container,
    fetch_status,
    fetch_vehicle_status,
    open_session,
    remember_vehicles,
    resolve_vin,
)
from bmw_cardata.state import load_state, save_state

TOKEN_PATH = "/gcdm/oauth/token"
CONTAINERS = "/customers/containers"
TELEMATIK = f"/customers/vehicles/{VIN}/telematicData"


def _passender_container(container_id="behaelter-alt"):
    return {"containerId": container_id, "name": CONTAINER_NAME, "purpose": CONTAINER_PURPOSE,
            "technicalDescriptors": list(all_descriptors())}


def _sitzung(bmw, zustand):
    return Session(CarDataApi(bmw.client(), zustand.tokens.access_token), zustand)


def test_gültige_tokens_werden_ohne_anfrage_genutzt(bmw, make_state, tmp_path):
    sitzung = open_session(bmw.client(), make_state(), tmp_path / "s.json", now=0.0)
    assert bmw.requests == []
    assert sitzung.state == make_state()


def test_abgelaufene_tokens_werden_erneuert_und_gespeichert(bmw, make_state, tmp_path):
    pfad = tmp_path / "s.json"
    bmw.add("POST", TOKEN_PATH, body={"access_token": "zugang-neu", "refresh_token": "r-neu", "expires_in": 3600})
    sitzung = open_session(bmw.client(), make_state(expires_at=100.0), pfad, now=1000.0)
    assert sitzung.state.tokens.access_token == "zugang-neu"
    assert load_state(pfad).tokens.refresh_token == "r-neu"


def test_gespeicherter_container_wird_ohne_anfrage_genutzt(bmw, make_state, tmp_path):
    sitzung = _sitzung(bmw, make_state(container_id="behaelter-1"))
    assert ensure_container(sitzung, tmp_path / "s.json") is sitzung
    assert bmw.requests == []


def test_vorhandener_passender_container_wird_wiederverwendet(bmw, make_state, tmp_path):
    pfad = tmp_path / "s.json"
    fremd = {"containerId": "fremd", "name": "Anderes", "purpose": "x"}
    bmw.add("GET", CONTAINERS, body=[fremd, _passender_container()])
    sitzung = ensure_container(_sitzung(bmw, make_state()), pfad)
    assert sitzung.state.container_id == "behaelter-alt"
    assert load_state(pfad).container_signature == descriptor_signature()
    assert [r.method for r in bmw.requests] == ["GET"]


def test_container_mit_anderen_datenpunkten_wird_ersetzt(bmw, make_state, tmp_path):
    veraltet = {**_passender_container(), "technicalDescriptors": ["vehicle.alt"]}
    bmw.add("GET", CONTAINERS, body=[veraltet])
    bmw.add("DELETE", f"{CONTAINERS}/behaelter-alt", status=204)
    bmw.add("POST", CONTAINERS, status=201, body={"containerId": "behaelter-neu"})
    sitzung = ensure_container(_sitzung(bmw, make_state()), tmp_path / "s.json")
    assert sitzung.state.container_id == "behaelter-neu"
    assert [r.method for r in bmw.requests] == ["GET", "DELETE", "POST"]


def test_gespeicherter_container_mit_alter_signatur_wird_ersetzt(bmw, make_state, tmp_path):
    pfad = tmp_path / "s.json"
    alt = make_state().with_container("behaelter-alt", "alte-signatur")
    ohne_liste = {"containerId": "behaelter-alt", "name": CONTAINER_NAME, "purpose": CONTAINER_PURPOSE}
    bmw.add("GET", CONTAINERS, body=[ohne_liste, {"containerId": "fremd", "name": "Anderes", "purpose": "x"}])
    bmw.add("DELETE", f"{CONTAINERS}/behaelter-alt", status=204)
    bmw.add("POST", CONTAINERS, status=201, body={"containerId": "behaelter-neu"})
    sitzung = ensure_container(_sitzung(bmw, alt), pfad)
    assert sitzung.state.container_id == "behaelter-neu"
    assert load_state(pfad).container_signature == descriptor_signature()
    assert [r.method for r in bmw.requests] == ["GET", "DELETE", "POST"]


def test_fehler_beim_löschen_alter_container_halten_nicht_auf(bmw, make_state, tmp_path):
    veraltet = {**_passender_container(), "technicalDescriptors": ["vehicle.alt"]}
    bmw.add("GET", CONTAINERS, body=[veraltet])
    bmw.add("DELETE", f"{CONTAINERS}/behaelter-alt", status=500)
    bmw.add("POST", CONTAINERS, status=201, body={"containerId": "behaelter-neu"})
    assert ensure_container(_sitzung(bmw, make_state()), tmp_path / "s.json").state.container_id == "behaelter-neu"


def test_tageslimit_beim_löschen_wird_gemeldet(bmw, make_state, tmp_path):
    veraltet = {**_passender_container(), "technicalDescriptors": ["vehicle.alt"]}
    bmw.add("GET", CONTAINERS, body=[veraltet])
    bmw.add("DELETE", f"{CONTAINERS}/behaelter-alt", status=429)
    with pytest.raises(RateLimitError):
        ensure_container(_sitzung(bmw, make_state()), tmp_path / "s.json")


def test_status_holt_telematik_mit_gespeichertem_container(bmw, make_state, tmp_path):
    bmw.add("GET", TELEMATIK, body={"telematicData": {"a.b": {"value": 1}}})
    daten = fetch_status(_sitzung(bmw, make_state(container_id="behaelter-1")), VIN, tmp_path / "s.json")
    assert daten == {"a.b": {"value": 1}}


def test_verschwundener_container_wird_einmal_neu_angelegt(bmw, make_state, tmp_path):
    pfad = tmp_path / "s.json"
    bmw.add("GET", TELEMATIK, status=404)
    bmw.add("GET", TELEMATIK, body={"telematicData": {"a.b": {"value": 2}}})
    bmw.add("GET", CONTAINERS, body=[])
    bmw.add("POST", CONTAINERS, status=201, body={"containerId": "behaelter-neu"})
    daten = fetch_status(_sitzung(bmw, make_state(container_id="behaelter-weg")), VIN, pfad)
    assert daten == {"a.b": {"value": 2}}
    assert load_state(pfad).container_id == "behaelter-neu"


def test_andere_fehler_beim_status_werden_weitergereicht(bmw, make_state, tmp_path):
    bmw.add("GET", TELEMATIK, status=500)
    with pytest.raises(ApiError):
        fetch_status(_sitzung(bmw, make_state(container_id="b")), VIN, tmp_path / "s.json")


def test_angegebene_fahrgestellnummer_braucht_keinen_abruf(bmw, make_state, tmp_path):
    sitzung = _sitzung(bmw, make_state())
    assert resolve_vin(sitzung, VIN, lambda v: v[0], tmp_path / "s.json") == (sitzung, VIN)
    assert bmw.requests == []
    assert not (tmp_path / "s.json").exists()


def test_gemerkte_fahrgestellnummer_braucht_keinen_abruf(bmw, make_state, tmp_path):
    sitzung = _sitzung(bmw, make_state().with_vin(VIN2))
    assert resolve_vin(sitzung, None, lambda v: v[0], tmp_path / "s.json")[1] == VIN2
    assert bmw.requests == []


def test_ohne_fahrgestellnummer_entscheidet_die_auswahl_und_wird_gemerkt(bmw, make_state, tmp_path):
    pfad = tmp_path / "s.json"
    bmw.add("GET", "/customers/vehicles/mappings", body=[{"vin": VIN}, {"vin": VIN2}])
    sitzung, vin = resolve_vin(_sitzung(bmw, make_state()), None, lambda v: v[1], pfad)
    assert vin == VIN2
    assert sitzung.state.vin == VIN2
    assert load_state(pfad).vin == VIN2


def test_ohne_fahrzeuge_kommt_ein_klarer_fehler(bmw, make_state, tmp_path):
    bmw.add("GET", "/customers/vehicles/mappings", body=[])
    with pytest.raises(ApiError, match="kein Fahrzeug"):
        resolve_vin(_sitzung(bmw, make_state()), None, lambda v: v[0], tmp_path / "s.json")


def test_fahrzeugliste_merkt_sich_nur_ein_einzelnes_fahrzeug(bmw, make_state, tmp_path):
    pfad = tmp_path / "s.json"
    sitzung = remember_vehicles(_sitzung(bmw, make_state()), [VIN], pfad)
    assert sitzung.state.vin == VIN and load_state(pfad).vin == VIN
    sitzung = remember_vehicles(sitzung, [VIN, VIN2], pfad)
    assert sitzung.state.vin is None and load_state(pfad).vin is None


def test_unveränderte_fahrzeugliste_schreibt_nichts(bmw, make_state, tmp_path):
    sitzung = _sitzung(bmw, make_state().with_vin(VIN))
    assert remember_vehicles(sitzung, [VIN], tmp_path / "s.json") is sitzung
    assert not (tmp_path / "s.json").exists()


def test_gemerkte_fahrgestellnummer_bleibt_beim_container_anlegen_erhalten(bmw, make_state, tmp_path):
    pfad = tmp_path / "s.json"
    bmw.add("GET", CONTAINERS, body=[])
    bmw.add("POST", CONTAINERS, status=201, body={"containerId": "neu"})
    ensure_container(_sitzung(bmw, make_state().with_vin(VIN)), pfad)
    assert load_state(pfad).vin == VIN


def test_abrufe_werden_über_die_sitzung_gemeldet(bmw, make_state, tmp_path):
    gezaehlt = []
    bmw.add("GET", "/customers/vehicles/mappings", body=[])
    sitzung = open_session(bmw.client(), make_state(), tmp_path / "s.json", 0.0, on_request=lambda: gezaehlt.append(1))
    sitzung.api.vehicles()
    assert gezaehlt == [1]


def test_fahrgestellnummer_aus_der_liste_wird_vereinheitlicht(bmw, make_state, tmp_path):
    bmw.add("GET", "/customers/vehicles/mappings", body=[{"vin": VIN.lower()}])
    sitzung, vin = resolve_vin(_sitzung(bmw, make_state()), None, lambda v: v[0], tmp_path / "s.json")
    assert vin == VIN and sitzung.state.vin == VIN


def test_ungültige_fahrgestellnummer_aus_der_liste_wird_nicht_gemerkt(bmw, make_state, tmp_path):
    sitzung = remember_vehicles(_sitzung(bmw, make_state()), ["kaputt"], tmp_path / "s.json")
    assert sitzung.state.vin is None


def _status_mit_gemerkter_vin(bmw, make_state, tmp_path, gemerkt):
    pfad = tmp_path / "s.json"
    zustand = make_state(container_id="behaelter-1").with_vin(gemerkt)
    save_state(pfad, zustand)
    return pfad, fetch_vehicle_status(_sitzung(bmw, zustand), None, lambda v: v[0], pfad)


def test_veraltete_gemerkte_vin_wird_durch_die_aktuelle_ersetzt(bmw, make_state, tmp_path):
    bmw.add("GET", f"/customers/vehicles/{VIN2}/telematicData", status=403)
    bmw.add("GET", "/customers/vehicles/mappings", body=[{"vin": VIN}])
    bmw.add("GET", TELEMATIK, body={"telematicData": {"a.b": {"value": 3}}})
    pfad, (vin, daten) = _status_mit_gemerkter_vin(bmw, make_state, tmp_path, VIN2)
    assert (vin, daten) == (VIN, {"a.b": {"value": 3}})
    assert load_state(pfad).vin == VIN
    assert len(bmw.requests) == 3
    assert not any(r.url.path == CONTAINERS for r in bmw.requests)


def test_gemerkte_vin_ohne_fehler_kostet_einen_abruf(bmw, make_state, tmp_path):
    bmw.add("GET", TELEMATIK, body={"telematicData": {}})
    _, (vin, _) = _status_mit_gemerkter_vin(bmw, make_state, tmp_path, VIN)
    assert vin == VIN and len(bmw.requests) == 1


def test_gemerkte_vin_und_verschwundener_container_werden_beide_repariert(bmw, make_state, tmp_path):
    bmw.add("GET", TELEMATIK, status=404)
    bmw.add("GET", TELEMATIK, status=404)
    bmw.add("GET", TELEMATIK, body={"telematicData": {"a.b": {"value": 4}}})
    bmw.add("GET", "/customers/vehicles/mappings", body=[{"vin": VIN}])
    bmw.add("GET", CONTAINERS, body=[])
    bmw.add("POST", CONTAINERS, status=201, body={"containerId": "behaelter-neu"})
    pfad, (vin, daten) = _status_mit_gemerkter_vin(bmw, make_state, tmp_path, VIN)
    assert daten == {"a.b": {"value": 4}}
    assert load_state(pfad).container_id == "behaelter-neu"
    assert load_state(pfad).vin == VIN


def test_andere_fehler_mit_gemerkter_vin_werden_weitergereicht(bmw, make_state, tmp_path):
    bmw.add("GET", TELEMATIK, status=500)
    with pytest.raises(ApiError):
        _status_mit_gemerkter_vin(bmw, make_state, tmp_path, VIN)


def test_angegebene_vin_nutzt_den_normalen_ablauf(bmw, make_state, tmp_path):
    bmw.add("GET", TELEMATIK, body={"telematicData": {}})
    vin, _ = fetch_vehicle_status(_sitzung(bmw, make_state(container_id="b")), VIN, lambda v: v[0], tmp_path / "s.json")
    assert vin == VIN
