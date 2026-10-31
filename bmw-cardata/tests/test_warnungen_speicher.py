import json

import httpx
import pytest
from conftest import VIN, ist_privat

from bmw_cardata.alert_store import (
    load_alert_state,
    load_settings,
    new_topic,
    save_alert_state,
    save_settings,
    settings_lines,
    settings_path,
    state_path_for,
)
from bmw_cardata.alerts import Alert, AlertSettings
from bmw_cardata.ntfy import NtfyError, mask_vin, send_push


def test_einstellungen_liegen_neben_der_anmeldedatei(tmp_path):
    assert settings_path(tmp_path / "state.json") == tmp_path / "warnungen.json"
    assert state_path_for(tmp_path / "state.json") == tmp_path / "warnungen-zustand.json"


def test_einstellungen_werden_gespeichert_und_geladen(tmp_path):
    pfad = tmp_path / "warnungen.json"
    einstellungen = AlertSettings(ntfy_topic="bmw-x", min_soc=30, min_12v=45, tire_tolerance_bar=0.3,
                                  locked_values=("LOCKED",))
    save_settings(pfad, einstellungen)
    assert load_settings(pfad) == einstellungen
    assert ist_privat(pfad)
    assert json.loads(pfad.read_text())["ladestand_min"] == 30


def test_fehlende_oder_beschädigte_einstellungen_ergeben_die_standardwerte(tmp_path):
    pfad = tmp_path / "warnungen.json"
    assert load_settings(pfad) == AlertSettings()
    for inhalt in ["kein json", "[]", json.dumps({"ladestand_min": 500}), json.dumps({"verriegelt": 5})]:
        pfad.write_text(inhalt)
        assert load_settings(pfad) == AlertSettings()


def test_zufälliges_thema_ist_lang_und_gültig():
    erstes, zweites = new_topic(), new_topic()
    assert erstes != zweites and erstes.startswith("bmw-") and len(erstes) >= 20
    assert AlertSettings(ntfy_topic=erstes).ntfy_topic == erstes


def test_einstellungen_als_text():
    zeilen = settings_lines(AlertSettings(ntfy_topic="bmw-x"))
    assert "Push über ntfy: https://ntfy.sh/bmw-x" in zeilen
    assert any("Ladestand unter 20 %" in z for z in zeilen)
    assert "Push über ntfy: aus" in settings_lines(AlertSettings())


def test_zustand_je_fahrzeug(tmp_path):
    pfad = tmp_path / "warnungen-zustand.json"
    assert load_alert_state(pfad, VIN) == {}
    save_alert_state(pfad, VIN, (Alert("a", "x"),), "CHARGINGACTIVE")
    assert load_alert_state(pfad, VIN) == {"aktiv": ["a"], "ladestatus": "CHARGINGACTIVE"}
    save_alert_state(pfad, "WBY98765432109876", (), None)
    assert load_alert_state(pfad, VIN)["aktiv"] == ["a"]
    pfad.write_text("kaputt")
    assert load_alert_state(pfad, VIN) == {}


def test_zustand_behält_den_letzten_ladestatus_wenn_keiner_kommt(tmp_path):
    pfad = tmp_path / "warnungen-zustand.json"
    save_alert_state(pfad, VIN, (), "CHARGINGACTIVE")
    save_alert_state(pfad, VIN, (), None)
    assert load_alert_state(pfad, VIN)["ladestatus"] == "CHARGINGACTIVE"


def test_nicht_schreibbarer_zustand_bricht_nichts_ab(tmp_path, monkeypatch):
    import bmw_cardata.alert_store as speicher

    def kaputt(*args):
        raise PermissionError("nein")

    monkeypatch.setattr(speicher, "write_private", kaputt)
    save_alert_state(tmp_path / "z.json", VIN, (), None)


def test_fahrgestellnummer_wird_für_den_push_gekürzt():
    assert mask_vin(VIN) == "…1234"


def _sender(antworten):
    gesendet = []

    def handler(request):
        gesendet.append(request)
        return antworten.pop(0) if antworten else httpx.Response(200, json={"id": "1"})

    return httpx.Client(transport=httpx.MockTransport(handler)), gesendet


def test_push_wird_als_json_an_den_server_geschickt():
    client, gesendet = _sender([])
    send_push(client, AlertSettings(ntfy_topic="bmw-x"), "BMW …1234: 1 Warnung", ["Heckklappe offen"])
    anfrage = gesendet[0]
    assert str(anfrage.url) == "https://ntfy.sh/"
    inhalt = json.loads(anfrage.content)
    assert inhalt["topic"] == "bmw-x" and inhalt["title"] == "BMW …1234: 1 Warnung"
    assert inhalt["message"] == "Heckklappe offen" and inhalt["priority"] == 4


def test_push_ohne_thema_ist_ein_fehler():
    client, gesendet = _sender([])
    with pytest.raises(NtfyError, match="kein ntfy-Thema"):
        send_push(client, AlertSettings(), "t", ["x"])
    assert gesendet == []


@pytest.mark.parametrize("antwort, text", [(httpx.Response(429), "HTTP 429"), (httpx.Response(500), "HTTP 500")])
def test_fehler_beim_push(antwort, text):
    client, _ = _sender([antwort])
    with pytest.raises(NtfyError, match=text):
        send_push(client, AlertSettings(ntfy_topic="bmw-x"), "t", ["x"])


def test_netzfehler_beim_push():
    def kaputt(request):
        raise httpx.ConnectError("weg", request=request)

    client = httpx.Client(transport=httpx.MockTransport(kaputt))
    with pytest.raises(NtfyError, match="ConnectError"):
        send_push(client, AlertSettings(ntfy_topic="bmw-x"), "t", ["x"])


def test_ungültige_url_und_weiterleitung_beim_push():
    client, _ = _sender([httpx.Response(301, headers={"location": "https://anders.example/"})])
    with pytest.raises(NtfyError, match="HTTP 301"):
        send_push(client, AlertSettings(ntfy_topic="bmw-x"), "t", ["x"])

    def kaputt(request):
        raise httpx.InvalidURL("kaputt")

    fehlerhaft = httpx.Client(transport=httpx.MockTransport(kaputt))
    with pytest.raises(NtfyError):
        send_push(fehlerhaft, AlertSettings(ntfy_topic="bmw-x"), "t", ["x"])


def test_push_hat_ein_kurzes_zeitlimit():
    client, gesendet = _sender([])
    send_push(client, AlertSettings(ntfy_topic="bmw-x"), "t", ["x"])
    assert gesendet[0].extensions["timeout"]["read"] == 10


def test_beschädigte_einstellungen_werden_erkannt(tmp_path):
    from bmw_cardata.alert_store import settings_problem

    pfad = tmp_path / "warnungen.json"
    assert settings_problem(pfad) is None
    save_settings(pfad, AlertSettings())
    assert settings_problem(pfad) is None
    pfad.write_text("{kaputt")
    assert "beschädigt" in settings_problem(pfad)
