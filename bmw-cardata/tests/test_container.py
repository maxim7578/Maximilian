import pytest

from bmw_cardata.api import ApiError, CarDataApi, RateLimitError
from bmw_cardata.containers import (
    SERVICE_CONTAINER,
    STATUS_CONTAINER,
    ContainerChoice,
    container_gone,
    provide_container,
)
from bmw_cardata.descriptors import SERVICE_DESCRIPTORS, all_descriptors, descriptor_signature, polled_descriptors

CONTAINERS = "/customers/containers"
HEUTE = "2026-10-31"
SIGNATUR = descriptor_signature(STATUS_CONTAINER.descriptors)


def _api(bmw):
    return CarDataApi(bmw.client(), "zugang")


def _eigener(container_id, deskriptoren=None):
    return {"containerId": container_id, "name": STATUS_CONTAINER.name, "purpose": STATUS_CONTAINER.purpose,
            "technicalDescriptors": list(deskriptoren if deskriptoren is not None else STATUS_CONTAINER.descriptors)}


def _bereitstellen(bmw, gespeichert=None, signatur=None, heute=HEUTE):
    return provide_container(_api(bmw), STATUS_CONTAINER, gespeichert, signatur, heute)


def _methoden(bmw):
    return [(r.method, r.url.path.rsplit("/", 1)[-1]) for r in bmw.requests]


def test_wartungsdaten_liegen_nicht_im_status_container():
    assert not set(SERVICE_DESCRIPTORS) & set(polled_descriptors())
    assert set(polled_descriptors()) | set(SERVICE_DESCRIPTORS) == set(all_descriptors())
    assert SERVICE_CONTAINER.descriptors == SERVICE_DESCRIPTORS
    assert descriptor_signature() == SIGNATUR


def test_passender_gespeicherter_container_braucht_keinen_abruf(bmw):
    assert _bereitstellen(bmw, "b-1", SIGNATUR) == ContainerChoice("b-1", SIGNATUR)
    assert bmw.requests == []


def test_neuer_container_wird_vor_dem_löschen_des_alten_angelegt(bmw):
    bmw.add("GET", CONTAINERS, body=[])
    bmw.add("POST", CONTAINERS, status=201, body={"containerId": "b-neu"})
    bmw.add("DELETE", f"{CONTAINERS}/b-alt", status=204)
    assert _bereitstellen(bmw, "b-alt", "alte-signatur") == ContainerChoice("b-neu", SIGNATUR)
    assert _methoden(bmw) == [("GET", "containers"), ("POST", "containers"), ("DELETE", "b-alt")]


def test_container_anderer_installationen_bleiben_unberührt(bmw):
    bmw.add("GET", CONTAINERS, body=[_eigener("b-fremd", ["vehicle.alt"]), {"containerId": "b-zwei",
             "name": STATUS_CONTAINER.name, "purpose": STATUS_CONTAINER.purpose}])
    bmw.add("POST", CONTAINERS, status=201, body={"containerId": "b-neu"})
    assert _bereitstellen(bmw).container_id == "b-neu"
    assert not any(r.method == "DELETE" for r in bmw.requests)


def test_passender_vorhandener_container_wird_wiederverwendet(bmw):
    bmw.add("GET", CONTAINERS, body=[_eigener("b-passt"), _eigener("b-passt")])
    bmw.add("DELETE", f"{CONTAINERS}/b-alt", status=204)
    assert _bereitstellen(bmw, "b-alt", None).container_id == "b-passt"
    assert _methoden(bmw) == [("GET", "containers"), ("DELETE", "b-alt")]


def test_wiederverwendeter_container_wird_nie_gelöscht(bmw):
    bmw.add("GET", CONTAINERS, body=[_eigener("b-1")])
    assert _bereitstellen(bmw, "b-1", None) == ContainerChoice("b-1", SIGNATUR)
    assert _methoden(bmw) == [("GET", "containers")]


def test_abgelehnter_container_lässt_den_alten_bis_morgen_in_gebrauch(bmw):
    bmw.add("GET", CONTAINERS, body=[])
    bmw.add("POST", CONTAINERS, status=400)
    wahl = _bereitstellen(bmw, "b-alt", "alte-signatur")
    assert wahl.container_id == "b-alt" and "abgelehnt" in wahl.note
    assert not any(r.method == "DELETE" for r in bmw.requests)
    anzahl = len(bmw.requests)
    assert _bereitstellen(bmw, "b-alt", wahl.signature).container_id == "b-alt"
    assert len(bmw.requests) == anzahl
    _bereitstellen(bmw, "b-alt", wahl.signature, heute="2026-11-01")
    assert len(bmw.requests) > anzahl


def test_abgelehnter_container_ohne_alten_ist_ein_fehler(bmw):
    bmw.add("GET", CONTAINERS, body=[])
    bmw.add("POST", CONTAINERS, status=400)
    with pytest.raises(ApiError):
        _bereitstellen(bmw)


def test_tageslimit_beim_anlegen_wird_gemeldet(bmw):
    bmw.add("GET", CONTAINERS, body=[])
    bmw.add("POST", CONTAINERS, status=429)
    with pytest.raises(RateLimitError):
        _bereitstellen(bmw, "b-alt", "alt")


@pytest.mark.parametrize("status", [500, 429])
def test_fehler_beim_aufräumen_halten_nicht_auf(bmw, status):
    bmw.add("GET", CONTAINERS, body=[])
    bmw.add("POST", CONTAINERS, status=201, body={"containerId": "b-neu"})
    bmw.add("DELETE", f"{CONTAINERS}/b-alt", status=status)
    assert _bereitstellen(bmw, "b-alt", "alt").container_id == "b-neu"


@pytest.mark.parametrize("status, code, weg", [(404, None, True), (403, "CU-105", True), (403, None, False), (400, "CU-400", False)])
def test_verschwundener_container_wird_erkannt(status, code, weg):
    assert container_gone(ApiError("x", status, code)) is weg
