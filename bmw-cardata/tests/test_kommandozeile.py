import io

import httpx
import pytest
from conftest import VIN, VIN2

from bmw_cardata import cli
from bmw_cardata.state import load_state, save_state

MAPPINGS = "/customers/vehicles/mappings"


def _starte(bmw, pfad, *argumente):
    aus, fehler = io.StringIO(), io.StringIO()
    code = cli.run(["--state", str(pfad), *argumente], out=aus, err=fehler, http_factory=bmw.client)
    return code, aus.getvalue(), fehler.getvalue()


@pytest.fixture
def angemeldet(tmp_path, make_state):
    pfad = tmp_path / "state.json"
    save_state(pfad, make_state(container_id="behaelter-1"))
    return pfad


def test_anmelden_zeigt_link_und_code_und_speichert_die_tokens(bmw, tmp_path, monkeypatch):
    pfad = tmp_path / "state.json"
    bmw.add("POST", "/gcdm/oauth/device/code", body={
        "device_code": "g", "user_code": "WXYZ-1234", "verification_uri": "https://bmw.example/geraet",
        "expires_in": 600, "interval": 1,
    })
    bmw.add("POST", "/gcdm/oauth/token", body={"access_token": "a", "refresh_token": "r", "expires_in": 3600})
    monkeypatch.setenv("BMW_CARDATA_CLIENT_ID", "client-1234-abcd")
    code, ausgabe, _ = _starte(bmw, pfad, "anmelden")
    assert code == 0
    assert "https://bmw.example/geraet" in ausgabe and "WXYZ-1234" in ausgabe
    zustand = load_state(pfad)
    assert zustand.client_id == "client-1234-abcd"
    assert zustand.tokens.access_token == "a"


def test_anmelden_mit_client_id_als_option(bmw, tmp_path, monkeypatch):
    monkeypatch.delenv("BMW_CARDATA_CLIENT_ID", raising=False)
    bmw.add("POST", "/gcdm/oauth/device/code", status=400, body={"error": "invalid_client"})
    code, _, fehler = _starte(bmw, tmp_path / "s.json", "anmelden", "--client-id", "client-9999-zzzz")
    assert code == 1
    assert bmw.form(0)["client_id"] == "client-9999-zzzz"
    assert fehler.startswith("Fehler: Gerätecode abgelehnt")


def test_anmelden_ohne_client_id_nennt_die_umgebungsvariable(bmw, tmp_path, monkeypatch):
    monkeypatch.delenv("BMW_CARDATA_CLIENT_ID", raising=False)
    code, _, fehler = _starte(bmw, tmp_path / "s.json", "anmelden")
    assert code == 1
    assert "BMW_CARDATA_CLIENT_ID" in fehler


def test_fahrzeuge_listet_die_fahrgestellnummern(bmw, angemeldet):
    bmw.add("GET", MAPPINGS, body=[{"vin": VIN, "mappingType": "PRIMARY"}])
    assert _starte(bmw, angemeldet, "fahrzeuge")[:2] == (0, f"{VIN}\n")


def test_fahrzeuge_ohne_treffer(bmw, angemeldet):
    bmw.add("GET", MAPPINGS, body=[])
    assert _starte(bmw, angemeldet, "fahrzeuge")[1] == "Keine Fahrzeuge gefunden.\n"


def test_basisdaten_werden_zeilenweise_ausgegeben(bmw, angemeldet):
    bmw.add("GET", f"/customers/vehicles/{VIN}/basicData", body={"brand": "BMW"})
    assert _starte(bmw, angemeldet, "basisdaten", VIN)[1] == "brand: BMW\n"


def test_status_des_einzigen_fahrzeugs(bmw, angemeldet):
    bmw.add("GET", MAPPINGS, body=[{"vin": VIN}])
    bmw.add("GET", f"/customers/vehicles/{VIN}/telematicData", body={"telematicData": {
        "vehicle.vehicle.travelledDistance": {"value": 1000, "unit": "km"}}})
    code, ausgabe, _ = _starte(bmw, angemeldet, "status")
    assert code == 0
    assert ausgabe == f"Fahrzeug {VIN}\nKilometerstand: 1000 km\n"


def test_status_mit_mehreren_fahrzeugen_verlangt_eine_auswahl(bmw, angemeldet):
    bmw.add("GET", MAPPINGS, body=[{"vin": VIN}, {"vin": VIN2}])
    code, _, fehler = _starte(bmw, angemeldet, "status")
    assert code == 1
    assert "Mehrere Fahrzeuge" in fehler and VIN2 in fehler


def test_status_mit_angegebener_fahrgestellnummer(bmw, angemeldet):
    bmw.add("GET", f"/customers/vehicles/{VIN}/telematicData", body={"telematicData": {}})
    code, ausgabe, _ = _starte(bmw, angemeldet, "status", VIN.lower())
    assert code == 0
    assert ausgabe.startswith(f"Fahrzeug {VIN}\nBMW hat noch keine Werte geliefert")


def test_ohne_anmeldung_kommt_ein_hinweis(bmw, tmp_path):
    code, _, fehler = _starte(bmw, tmp_path / "fehlt.json", "fahrzeuge")
    assert code == 1
    assert "anmelden" in fehler


def test_tageslimit_wird_verständlich_gemeldet(bmw, angemeldet):
    bmw.add("GET", MAPPINGS, status=429)
    code, _, fehler = _starte(bmw, angemeldet, "fahrzeuge")
    assert code == 1
    assert "Tageslimit" in fehler


def test_netzwerkfehler_zeigt_nur_die_art_des_fehlers(tmp_path, angemeldet):
    def kaputt(request):
        raise httpx.ConnectError("verbindung weg zu https://geheim", request=request)

    aus, fehler = io.StringIO(), io.StringIO()
    fabrik = lambda: httpx.Client(transport=httpx.MockTransport(kaputt))  # noqa: E731
    code = cli.run(["--state", str(angemeldet), "fahrzeuge"], out=aus, err=fehler, http_factory=fabrik)
    assert code == 1
    assert fehler.getvalue() == "Netzwerkfehler: ConnectError\n"


def test_abbruch_mit_strg_c_wird_sauber_gemeldet(tmp_path, angemeldet):
    def abbruch(request):
        raise KeyboardInterrupt

    fehler = io.StringIO()
    fabrik = lambda: httpx.Client(transport=httpx.MockTransport(abbruch))  # noqa: E731
    assert cli.run(["--state", str(angemeldet), "fahrzeuge"], out=io.StringIO(), err=fehler, http_factory=fabrik) == 1
    assert fehler.getvalue() == "Abgebrochen.\n"


def test_abmelden_löscht_die_anmeldung(bmw, angemeldet):
    assert _starte(bmw, angemeldet, "abmelden")[:2] == (0, "Abgemeldet.\n")
    assert not angemeldet.exists()
    assert _starte(bmw, angemeldet, "abmelden")[1] == "Es war keine Anmeldung gespeichert.\n"


def test_abgelaufene_tokens_werden_vor_dem_abruf_erneuert(bmw, tmp_path, make_state):
    pfad = tmp_path / "state.json"
    save_state(pfad, make_state(expires_at=1.0))
    bmw.add("POST", "/gcdm/oauth/token", body={"access_token": "frisch", "expires_in": 3600})
    bmw.add("GET", MAPPINGS, body=[])
    assert _starte(bmw, pfad, "fahrzeuge")[0] == 0
    assert bmw.requests[1].headers["Authorization"] == "Bearer frisch"
    assert load_state(pfad).tokens.refresh_token == "erneuerung-alt"


def test_hauptfunktion_beendet_mit_dem_rückgabewert(monkeypatch):
    monkeypatch.setattr(cli, "run", lambda: 3)
    with pytest.raises(SystemExit) as ende:
        cli.main()
    assert ende.value.code == 3

