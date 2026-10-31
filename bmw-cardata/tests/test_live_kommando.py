import io
import json

import pytest
from conftest import VIN, VIN2
from test_live import KM, FakeClient, abgelehnt, empfangen, verbunden

from bmw_cardata import cli
from bmw_cardata.auth import Tokens
from bmw_cardata.history import history_path, load_entries
from bmw_cardata.state import State, load_state, save_state

STREAM_SCOPE = "authenticate_user openid cardata:api:read cardata:streaming:read"


@pytest.fixture(autouse=True)
def ohne_warten(monkeypatch):
    """Pausen zwischen Verbindungsversuchen in den Tests überspringen."""
    import time

    monkeypatch.setattr(time, "sleep", lambda sekunden: None)


def _starte(bmw, pfad, *argumente):
    aus, fehler = io.StringIO(), io.StringIO()
    code = cli.run(["--state", str(pfad), *argumente], out=aus, err=fehler, http_factory=bmw.client)
    return code, aus.getvalue(), fehler.getvalue()


@pytest.fixture
def mit_stream(tmp_path):
    pfad = tmp_path / "state.json"
    tokens = Tokens("zugang", "erneuerung", 10_000_000_000.0, STREAM_SCOPE, "id-token", "gcid-1")
    save_state(pfad, State("client-1234-abcd", tokens, "behaelter-1"))
    return pfad


@pytest.fixture
def client(monkeypatch):
    erzeugt = {}

    def fabrik(*schritte):
        fake = FakeClient(*schritte, am_ende=KeyboardInterrupt())

        def erzeugen(gcid):
            erzeugt["gcid"] = gcid
            return fake

        monkeypatch.setattr(cli, "create_stream_client", erzeugen)
        return fake

    fabrik.erzeugt = erzeugt
    return fabrik


def test_live_zeigt_nachrichten_bis_strg_c(bmw, mit_stream, client):
    fake = client(verbunden, empfangen())
    code, ausgabe, fehler = _starte(bmw, mit_stream, "live")
    assert code == 0
    assert ausgabe.splitlines()[0] == f"Fahrzeug {VIN}"
    assert ausgabe.splitlines()[1].endswith("  Kilometerstand: 42063 km")
    assert "Verbunden" in fehler and "beendet" in fehler
    assert client.erzeugt["gcid"] == "gcid-1"
    assert ("anmeldung", "gcid-1", "id-token") in fake.aufrufe
    assert bmw.requests == []


def test_fahrzeug_wird_nur_beim_wechsel_genannt(bmw, mit_stream, client):
    zweite = json.dumps({"vin": VIN2, "data": {KM: {"value": 7}}}).encode()
    client(verbunden, empfangen(), empfangen(), empfangen(zweite))
    ausgabe = _starte(bmw, mit_stream, "live")[1]
    assert ausgabe.count(f"Fahrzeug {VIN}") == 1 and ausgabe.count(f"Fahrzeug {VIN2}") == 1


def test_live_mit_fahrgestellnummer_filtert_andere_fahrzeuge(bmw, mit_stream, client):
    zweite = json.dumps({"vin": VIN2, "data": {KM: {"value": 7}}}).encode()
    client(verbunden, empfangen(zweite), empfangen())
    _, ausgabe, fehler = _starte(bmw, mit_stream, "live", VIN.lower())
    assert VIN2 not in ausgabe and "42063" in ausgabe
    assert f"Nachrichten für {VIN2} werden übergangen" in fehler


def test_live_als_json_eine_zeile_pro_nachricht(bmw, mit_stream, client):
    client(verbunden, empfangen(), empfangen())
    zeilen = _starte(bmw, mit_stream, "live", "--json")[1].splitlines()
    assert len(zeilen) == 2
    daten = json.loads(zeilen[0])
    assert daten["fahrgestellnummer"] == VIN
    assert daten["werte"][KM]["value"] == 42063
    assert daten["empfangen"].endswith("Z")


def test_live_speichern_legt_nachrichten_im_verlauf_ab(bmw, mit_stream, client):
    client(verbunden, empfangen())
    _starte(bmw, mit_stream, "live", "--speichern")
    eintraege = load_entries(history_path(mit_stream))
    assert [(e.vin, e.data[KM]["value"]) for e in eintraege] == [(VIN, 42063)]


def test_live_meldet_einen_nicht_speicherbaren_verlauf_ohne_abbruch(bmw, mit_stream, client, monkeypatch):
    def kaputt(*args):
        raise PermissionError("kein Zugriff")

    monkeypatch.setattr(cli, "append_entry", kaputt)
    client(verbunden, empfangen())
    code, ausgabe, fehler = _starte(bmw, mit_stream, "live", "--speichern")
    assert code == 0 and "42063" in ausgabe
    assert "Verlauf konnte nicht gespeichert werden" in fehler


def test_live_ohne_streaming_anmeldung_verlangt_neu_anmelden(bmw, tmp_path, make_state, client):
    pfad = tmp_path / "state.json"
    save_state(pfad, make_state())
    client(verbunden)
    code, _, fehler = _starte(bmw, pfad, "live")
    assert code == 1
    assert "neu anmelden" in fehler


def test_live_erneuert_ein_abgelaufenes_token_vor_dem_verbinden(bmw, mit_stream, client):
    zustand = load_state(mit_stream)
    save_state(mit_stream, zustand.with_tokens(Tokens("z", "erneuerung", 1.0, STREAM_SCOPE, "alt", "gcid-1")))
    bmw.add("POST", "/gcdm/oauth/token", body={"access_token": "z2", "id_token": "neu", "expires_in": 3600})
    fake = client(verbunden)
    assert _starte(bmw, mit_stream, "live")[0] == 0
    assert ("anmeldung", "gcid-1", "neu") in fake.aufrufe
    gespeichert = load_state(mit_stream).tokens
    assert gespeichert.id_token == "neu" and gespeichert.gcid == "gcid-1"


def test_live_mit_dauerhafter_ablehnung_endet_mit_hinweis(bmw, mit_stream, client):
    bmw.add("POST", "/gcdm/oauth/token", body={"access_token": "z2", "id_token": "neu", "expires_in": 3600})
    client(*[abgelehnt("Not authorized")] * 3)
    code, _, fehler = _starte(bmw, mit_stream, "live")
    assert code == 1
    assert "Home Assistant" in fehler


def test_anmelden_fragt_standardmäßig_auch_streaming_an(bmw, tmp_path, monkeypatch):
    monkeypatch.setenv("BMW_CARDATA_CLIENT_ID", "client-1234-abcd")
    bmw.add("POST", "/gcdm/oauth/device/code", status=400, body={"error": "x"})
    _starte(bmw, tmp_path / "s.json", "anmelden")
    assert "cardata:streaming:read" in bmw.form(0)["scope"].split()


def test_anmelden_nur_api_lässt_streaming_weg(bmw, tmp_path, monkeypatch):
    monkeypatch.setenv("BMW_CARDATA_CLIENT_ID", "client-1234-abcd")
    bmw.add("POST", "/gcdm/oauth/device/code", status=400, body={"error": "x"})
    _starte(bmw, tmp_path / "s.json", "anmelden", "--nur-api")
    scope = bmw.form(0)["scope"].split()
    assert "cardata:streaming:read" not in scope and "cardata:api:read" in scope


def test_anmelden_speichert_gcid_und_id_token(bmw, tmp_path, monkeypatch):
    monkeypatch.setenv("BMW_CARDATA_CLIENT_ID", "client-1234-abcd")
    bmw.add("POST", "/gcdm/oauth/device/code", body={
        "device_code": "g", "user_code": "C", "verification_uri": "https://bmw.example/g", "interval": 1})
    bmw.add("POST", "/gcdm/oauth/token", body={
        "access_token": "a", "refresh_token": "r", "id_token": "idt", "gcid": "g-9", "expires_in": 3600})
    assert _starte(bmw, tmp_path / "s.json", "anmelden")[0] == 0
    tokens = load_state(tmp_path / "s.json").tokens
    assert (tokens.id_token, tokens.gcid) == ("idt", "g-9")


def test_hilfstext_nennt_den_live_befehl(capsys):
    with pytest.raises(SystemExit):
        cli.run(["--help"])
    assert "live" in capsys.readouterr().out


def test_nachricht_ohne_werte_erzeugt_keine_ausgabe(bmw, mit_stream, client):
    leer = json.dumps({"vin": VIN, "data": {KM: {"value": None}}}).encode()
    client(verbunden, empfangen(leer))
    assert _starte(bmw, mit_stream, "live")[1] == ""


def test_json_ausgabe_maskiert_steuerzeichen(bmw, mit_stream, client):
    roh = json.dumps({"vin": VIN, "data": {KM: {"value": "a\u009b31m\u202e"}}}).encode()
    client(verbunden, empfangen(roh))
    ausgabe = _starte(bmw, mit_stream, "live", "--json")[1]
    assert "\u009b" not in ausgabe and "\u202e" not in ausgabe
    assert json.loads(ausgabe)["werte"][KM]["value"] == "a\u009b31m\u202e"


def test_abgelehnter_gerätecode_weist_auf_nur_api_hin(bmw, tmp_path, monkeypatch):
    monkeypatch.setenv("BMW_CARDATA_CLIENT_ID", "client-1234-abcd")
    bmw.add("POST", "/gcdm/oauth/device/code", status=400, body={"error": "invalid_scope"})
    fehler = _starte(bmw, tmp_path / "s.json", "anmelden")[2]
    assert "--nur-api" in fehler


def test_nur_api_ohne_zusätzlichen_hinweis(bmw, tmp_path, monkeypatch):
    monkeypatch.setenv("BMW_CARDATA_CLIENT_ID", "client-1234-abcd")
    bmw.add("POST", "/gcdm/oauth/device/code", status=400, body={"error": "x"})
    assert "--nur-api" not in _starte(bmw, tmp_path / "s.json", "anmelden", "--nur-api")[2]
