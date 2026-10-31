import pytest

from bmw_cardata.api import ApiError, CarDataApi, RateLimitError
from bmw_cardata.config import ConfigError

from conftest import VIN, VIN2

MAPPINGS = "/customers/vehicles/mappings"
CONTAINERS = "/customers/containers"
TELEMATIK = f"/customers/vehicles/{VIN}/telematicData"


def _api(bmw):
    return CarDataApi(bmw.client(), "zugang-123")


def test_jede_anfrage_trägt_token_und_api_version(bmw):
    bmw.add("GET", MAPPINGS, body=[])
    _api(bmw).vehicles()
    kopf = bmw.requests[0].headers
    assert kopf["Authorization"] == "Bearer zugang-123"
    assert kopf["x-version"] == "v1"
    assert bmw.requests[0].url.host == "api-cardata.bmwgroup.com"


@pytest.mark.parametrize("antwort", [
    [{"vin": VIN, "mappingType": "PRIMARY"}, {"vin": VIN2, "mappingType": "SECONDARY"}],
    {"mappings": [{"vin": VIN, "mappingType": "primary"}, {"vin": VIN2, "mappingType": "SECONDARY"}]},
])
def test_nur_fahrzeuge_als_hauptnutzer_werden_gelistet(bmw, antwort):
    bmw.add("GET", MAPPINGS, body=antwort)
    assert _api(bmw).vehicles() == [VIN]


def test_unerwartetes_format_ergibt_leere_fahrzeugliste(bmw):
    bmw.add("GET", MAPPINGS, body={"etwas": "anderes"})
    assert _api(bmw).vehicles() == []


def test_basisdaten_werden_als_wörterbuch_geliefert(bmw):
    bmw.add("GET", f"/customers/vehicles/{VIN}/basicData", body={"brand": "BMW", "modelName": "i3"})
    assert _api(bmw).basic_data(VIN.lower()) == {"brand": "BMW", "modelName": "i3"}


def test_ungültige_fahrgestellnummer_erreicht_nie_den_server(bmw):
    with pytest.raises(ConfigError):
        _api(bmw).basic_data("../containers")
    assert bmw.requests == []


def test_container_anlegen_sendet_name_zweck_und_datenpunkte(bmw):
    bmw.add("POST", CONTAINERS, status=201, body={"containerId": "behaelter-9"})
    neu = _api(bmw).create_container("Name", "Zweck", ("a.b", "c.d"))
    assert neu == "behaelter-9"
    assert bmw.requests[0].read() == b'{"name":"Name","purpose":"Zweck","technicalDescriptors":["a.b","c.d"]}'


def test_container_ohne_id_in_der_antwort_ist_ein_fehler(bmw):
    bmw.add("POST", CONTAINERS, status=201, body={})
    with pytest.raises(ApiError, match="Container-ID"):
        _api(bmw).create_container("N", "Z", ("a",))


def test_containerliste_versteht_beide_formate(bmw):
    bmw.add("GET", CONTAINERS, body={"containers": [{"containerId": "a"}, "müll"]})
    assert _api(bmw).containers() == [{"containerId": "a"}]


def test_telematikdaten_übergeben_container_id(bmw):
    bmw.add("GET", TELEMATIK, body={"telematicData": {"x.y": {"value": 5}, "kaputt": 3}})
    daten = _api(bmw).telematic_data(VIN, "behaelter-1")
    assert daten == {"x.y": {"value": 5}}
    assert bmw.requests[0].url.params["containerId"] == "behaelter-1"


def test_telematik_ohne_daten_ergibt_leeres_ergebnis(bmw):
    bmw.add("GET", TELEMATIK, body={})
    assert _api(bmw).telematic_data(VIN, "b") == {}


def test_tageslimit_wird_als_eigener_fehler_gemeldet(bmw):
    bmw.add("GET", MAPPINGS, status=429)
    with pytest.raises(RateLimitError, match="50 Abrufe"):
        _api(bmw).vehicles()


@pytest.mark.parametrize("status", [401, 403])
def test_fehlende_berechtigung_verweist_auf_das_portal(bmw, status):
    bmw.add("GET", MAPPINGS, status=status)
    with pytest.raises(ApiError, match="Portal") as fehler:
        _api(bmw).vehicles()
    assert fehler.value.status == status


def test_serverfehler_verrät_keine_fahrgestellnummer(bmw):
    bmw.add("GET", TELEMATIK, status=500)
    with pytest.raises(ApiError) as fehler:
        _api(bmw).telematic_data(VIN, "b")
    assert VIN not in str(fehler.value)
    assert fehler.value.status == 500


def test_ungültiges_json_wird_erkannt(bmw):
    bmw.add("GET", MAPPINGS, raw=b"<html>")
    with pytest.raises(ApiError, match="JSON"):
        _api(bmw).vehicles()


def test_leere_antwort_ergibt_keine_daten(bmw):
    bmw.add("GET", f"/customers/vehicles/{VIN}/basicData", raw=b"")
    assert _api(bmw).basic_data(VIN) == {}
