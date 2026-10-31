import io
import json
import time

import pytest
from conftest import VIN
from test_live import FakeClient, empfangen, verbunden

from bmw_cardata import cli
from bmw_cardata.alert_store import load_settings, settings_path
from bmw_cardata.auth import Tokens
from bmw_cardata.maintenance import maintenance_path
from bmw_cardata.state import State, save_state

TELEMATIK = f"/customers/vehicles/{VIN}/telematicData"
HECK = "vehicle.body.trunk.isOpen"
OFFEN = {"telematicData": {HECK: {"value": True}}}


def _starte(bmw, pfad, *argumente):
    aus, fehler = io.StringIO(), io.StringIO()
    code = cli.run(["--state", str(pfad), *argumente], out=aus, err=fehler, http_factory=bmw.client)
    return code, aus.getvalue(), fehler.getvalue()


@pytest.fixture
def angemeldet(tmp_path, make_state):
    pfad = tmp_path / "state.json"
    save_state(pfad, make_state(container_id="behaelter-1"))
    maintenance_path(pfad).write_text(json.dumps({"fahrzeuge": {VIN: {"versucht": time.time(), "werte": {}}}}))
    return pfad


def _mit_push(pfad, thema="bmw-test"):
    settings_path(pfad).write_text(json.dumps({"ntfy_thema": thema}))


def test_einstellen_ohne_angaben_zeigt_die_einstellungen(bmw, tmp_path):
    code, ausgabe, _ = _starte(bmw, tmp_path / "s.json", "warnungen", "einstellen")
    assert code == 0 and "Push über ntfy: aus" in ausgabe
    assert not settings_path(tmp_path / "s.json").exists()


def test_einstellen_speichert_grenzen_und_neues_thema(bmw, tmp_path):
    pfad = tmp_path / "s.json"
    code, ausgabe, _ = _starte(bmw, pfad, "warnungen", "einstellen", "--ntfy-thema", "neu", "--ladestand", "30",
                               "--batterie-12v", "40", "--reifendruck-toleranz", "0.3", "--verriegelt", "locked, secured,")
    assert code == 0
    einstellungen = load_settings(settings_path(pfad))
    assert einstellungen.ntfy_topic.startswith("bmw-") and einstellungen.min_soc == 30
    assert einstellungen.locked_values == ("LOCKED", "SECURED")
    assert "Neues Thema" in ausgabe and "nicht weitergeben" in ausgabe


def test_einstellen_aus_und_ungültige_werte(bmw, tmp_path):
    pfad = tmp_path / "s.json"
    _mit_push(pfad)
    _starte(bmw, pfad, "warnungen", "einstellen", "--ntfy-thema", "aus", "--ntfy-server", "https://push.example")
    assert load_settings(settings_path(pfad)).ntfy_topic is None
    for argumente in (["--ladestand", "200"], ["--ntfy-server", "http://x"], ["--verriegelt", " , "]):
        code, _, fehler = _starte(bmw, pfad, "warnungen", "einstellen", *argumente)
        assert code == 1 and fehler.startswith("Fehler:")


def test_test_push(bmw, tmp_path):
    pfad = tmp_path / "s.json"
    _mit_push(pfad)
    bmw.add("POST", "/", body={"id": "1"})
    code, ausgabe, _ = _starte(bmw, pfad, "warnungen", "test")
    assert code == 0 and "Test-Push gesendet an https://ntfy.sh/bmw-test" in ausgabe
    assert json.loads(bmw.requests[0].content)["topic"] == "bmw-test"


def test_test_push_ohne_thema_meldet_einen_fehler(bmw, tmp_path):
    code, _, fehler = _starte(bmw, tmp_path / "s.json", "warnungen", "test")
    assert code == 1 and "kein ntfy-Thema" in fehler


def test_pruefen_meldet_und_pusht_neue_warnungen_nur_einmal(bmw, angemeldet):
    _mit_push(angemeldet)
    bmw.add("GET", TELEMATIK, body=OFFEN)
    bmw.add("POST", "/", body={"id": "1"})
    code, ausgabe, _ = _starte(bmw, angemeldet, "warnungen", "pruefen", VIN)
    assert code == 0 and "Warnung: Heckklappe offen" in ausgabe
    pushes = [r for r in bmw.requests if r.method == "POST"]
    assert json.loads(pushes[0].content)["title"] == "BMW …1234: 1 Warnung"
    ausgabe = _starte(bmw, angemeldet, "warnungen", "pruefen", VIN)[1]
    assert "Keine neuen Warnungen." in ausgabe
    assert len([r for r in bmw.requests if r.method == "POST"]) == 1


def test_pruefen_alle_zeigt_auch_bekannte_warnungen(bmw, angemeldet):
    bmw.add("GET", TELEMATIK, body=OFFEN)
    _starte(bmw, angemeldet, "warnungen", "pruefen", VIN)
    ausgabe = _starte(bmw, angemeldet, "warnungen", "pruefen", VIN, "--alle")[1]
    assert "Warnung: Heckklappe offen" in ausgabe


def test_pruefen_alle_ohne_warnungen(bmw, angemeldet):
    bmw.add("GET", TELEMATIK, body={"telematicData": {HECK: {"value": False}}})
    assert "Keine Warnungen." in _starte(bmw, angemeldet, "warnungen", "pruefen", VIN, "--alle")[1]


def test_pruefen_alle_zeigt_ereignisse_zusätzlich(bmw, angemeldet):
    laden = "vehicle.drivetrain.electricEngine.charging.status"
    bmw.add("GET", TELEMATIK, body={"telematicData": {laden: {"value": "CHARGINGACTIVE"}}})
    bmw.add("GET", TELEMATIK, body={"telematicData": {laden: {"value": "NOCHARGING"}}})
    _starte(bmw, angemeldet, "warnungen", "pruefen", VIN)
    ausgabe = _starte(bmw, angemeldet, "warnungen", "pruefen", VIN, "--alle")[1]
    assert "Laden beendet" in ausgabe and "Keine Warnungen." not in ausgabe


def test_status_zeigt_geltende_warnungen_ohne_push(bmw, angemeldet):
    _mit_push(angemeldet)
    bmw.add("GET", TELEMATIK, body=OFFEN)
    ausgabe = _starte(bmw, angemeldet, "status", VIN)[1]
    assert "Warnungen\n  Heckklappe offen" in ausgabe
    assert not any(r.method == "POST" for r in bmw.requests)


@pytest.fixture(autouse=True)
def ohne_warten(monkeypatch):
    monkeypatch.setattr(time, "sleep", lambda sekunden: None)


@pytest.fixture
def mit_stream(tmp_path):
    pfad = tmp_path / "state.json"
    scope = "authenticate_user openid cardata:api:read cardata:streaming:read"
    save_state(pfad, State("client-1234-abcd", Tokens("z", "e", 10_000_000_000.0, scope, "idt", "gcid-1"), "b"))
    return pfad


def _live_client(monkeypatch, *schritte):
    fake = FakeClient(*schritte, am_ende=KeyboardInterrupt())
    monkeypatch.setattr(cli, "create_stream_client", lambda gcid: fake)
    return fake


def test_live_mit_warnungen_meldet_und_pusht(bmw, mit_stream, monkeypatch):
    _mit_push(mit_stream)
    bmw.add("POST", "/", body={"id": "1"})
    nachricht = json.dumps({"vin": VIN, "data": {HECK: {"value": True}}}).encode()
    _live_client(monkeypatch, verbunden, empfangen(nachricht), empfangen(nachricht))
    code, ausgabe, _ = _starte(bmw, mit_stream, "live", "--warnungen")
    assert code == 0 and ausgabe.count("Warnung: Heckklappe offen") == 1
    assert len([r for r in bmw.requests if r.method == "POST"]) == 1


def test_live_json_schreibt_warnungen_auf_stderr(bmw, mit_stream, monkeypatch):
    nachricht = json.dumps({"vin": VIN, "data": {HECK: {"value": True}}}).encode()
    _live_client(monkeypatch, verbunden, empfangen(nachricht))
    _, ausgabe, fehler = _starte(bmw, mit_stream, "live", "--json", "--warnungen")
    assert "Warnung: Heckklappe offen" in fehler
    assert all(json.loads(zeile) for zeile in ausgabe.splitlines())
