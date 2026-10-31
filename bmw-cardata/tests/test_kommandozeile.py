import io
import json
import time

import httpx
import pytest
from conftest import VIN, VIN2

from bmw_cardata import cli
from bmw_cardata.history import Entry, append_entry, history_path
from bmw_cardata.state import load_state, save_state
from bmw_cardata.usage import Usage, save_usage, usage_path

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



TELEMATIK = f"/customers/vehicles/{VIN}/telematicData"
KM_DATEN = {"telematicData": {"vehicle.vehicle.travelledDistance": {"value": 1000, "unit": "km"}}}


def test_status_merkt_sich_das_einzige_fahrzeug_für_den_nächsten_abruf(bmw, angemeldet):
    bmw.add("GET", MAPPINGS, body=[{"vin": VIN}])
    bmw.add("GET", TELEMATIK, body=KM_DATEN)
    assert _starte(bmw, angemeldet, "status")[0] == 0
    assert _starte(bmw, angemeldet, "status")[0] == 0
    pfade = [r.url.path for r in bmw.requests]
    assert pfade == [MAPPINGS, TELEMATIK, TELEMATIK]
    assert load_state(angemeldet).vin == VIN


def test_fahrzeuge_aktualisiert_das_gemerkte_fahrzeug(bmw, angemeldet):
    save_state(angemeldet, load_state(angemeldet).with_vin(VIN2))
    bmw.add("GET", MAPPINGS, body=[{"vin": VIN}])
    _starte(bmw, angemeldet, "fahrzeuge")
    assert load_state(angemeldet).vin == VIN


def test_kontingent_zählt_die_abrufe_dieses_programms(bmw, angemeldet):
    bmw.add("GET", MAPPINGS, body=[{"vin": VIN}])
    bmw.add("GET", TELEMATIK, body=KM_DATEN)
    _starte(bmw, angemeldet, "status")
    code, ausgabe, _ = _starte(bmw, angemeldet, "kontingent")
    assert code == 0
    assert "Abrufe in den letzten 24 Stunden: 2 von 50" in ausgabe
    assert "Noch frei: 48" in ausgabe
    assert len(bmw.requests) == 2


def test_kontingent_nennt_den_nächsten_freien_abruf_wenn_alles_verbraucht_ist(bmw, angemeldet):
    jetzt = time.time()
    save_usage(usage_path(angemeldet), Usage(tuple(jetzt - 60 + i for i in range(50))))
    code, ausgabe, _ = _starte(bmw, angemeldet, "kontingent")
    assert code == 0
    assert "Noch frei: 0" in ausgabe
    assert "Nächster Abruf frei ab:" in ausgabe


def test_kontingent_ohne_anmeldung_funktioniert(bmw, tmp_path):
    code, ausgabe, _ = _starte(bmw, tmp_path / "state.json", "kontingent")
    assert code == 0
    assert "0 von 50" in ausgabe


def test_status_als_json(bmw, angemeldet):
    bmw.add("GET", TELEMATIK, body=KM_DATEN)
    code, ausgabe, _ = _starte(bmw, angemeldet, "status", VIN, "--json")
    assert code == 0
    daten = json.loads(ausgabe)
    assert daten["fahrgestellnummer"] == VIN
    assert daten["werte"]["vehicle.vehicle.travelledDistance"]["value"] == 1000
    assert daten["abgerufen"].endswith("Z")


def test_status_speichern_und_verlauf_anzeigen(bmw, angemeldet):
    bmw.add("GET", TELEMATIK, body=KM_DATEN)
    bmw.add("GET", TELEMATIK, body={"telematicData": {
        "vehicle.vehicle.travelledDistance": {"value": 1080, "unit": "km"}}})
    _starte(bmw, angemeldet, "status", VIN, "--speichern")
    code, ausgabe, _ = _starte(bmw, angemeldet, "status", VIN, "--speichern")
    assert code == 0
    assert "Im Verlauf gespeichert." in ausgabe
    code, ausgabe, _ = _starte(bmw, angemeldet, "verlauf")
    assert code == 0
    zeilen = ausgabe.splitlines()
    assert len(zeilen) == 2
    assert zeilen[1].endswith("Kilometerstand: 1080 km  (+80 km)")
    assert len(bmw.requests) == 2


def test_status_ohne_speichern_legt_keinen_verlauf_an(bmw, angemeldet):
    bmw.add("GET", TELEMATIK, body=KM_DATEN)
    _starte(bmw, angemeldet, "status", VIN)
    assert not history_path(angemeldet).exists()


def test_verlauf_mit_anzahl_und_als_csv(bmw, angemeldet):
    for tag in (1, 2, 3):
        append_entry(history_path(angemeldet), Entry(f"2026-10-0{tag}T10:00:00Z", VIN, {}))
    assert len(_starte(bmw, angemeldet, "verlauf", "--anzahl", "2")[1].splitlines()) == 2
    code, ausgabe, _ = _starte(bmw, angemeldet, "verlauf", "--csv")
    assert code == 0
    assert ausgabe.splitlines()[0].startswith("zeit;fahrgestellnummer;")
    assert len(ausgabe.splitlines()) == 4


def test_leerer_verlauf_gibt_einen_hinweis(bmw, tmp_path):
    code, ausgabe, _ = _starte(bmw, tmp_path / "state.json", "verlauf")
    assert code == 0
    assert "status --speichern" in ausgabe


@pytest.mark.parametrize("anzahl", ["0", "-3", "abc", "100000"])
def test_ungültige_anzahl_wird_abgelehnt(bmw, tmp_path, anzahl):
    with pytest.raises(SystemExit):
        _starte(bmw, tmp_path / "state.json", "verlauf", "--anzahl", anzahl)


def test_abmelden_weist_auf_den_verbleibenden_verlauf_hin(bmw, angemeldet):
    append_entry(history_path(angemeldet), Entry("2026-10-30T10:00:00Z", VIN, {}))
    ausgabe = _starte(bmw, angemeldet, "abmelden")[1]
    assert "Abgemeldet." in ausgabe and "verlauf.jsonl" in ausgabe
    assert history_path(angemeldet).exists()


def test_nicht_speicherbarer_verlauf_zeigt_trotzdem_den_status(bmw, angemeldet, monkeypatch):
    def kaputt(*args):
        raise PermissionError("kein Zugriff")

    monkeypatch.setattr(cli, "append_entry", kaputt)
    bmw.add("GET", TELEMATIK, body=KM_DATEN)
    code, ausgabe, _ = _starte(bmw, angemeldet, "status", VIN, "--speichern")
    assert code == 0
    assert "Kilometerstand: 1000 km" in ausgabe
    assert "Verlauf konnte nicht gespeichert werden" in ausgabe


def test_unlesbare_datei_ergibt_eine_fehlermeldung_statt_absturz(bmw, angemeldet, monkeypatch):
    def kaputt(*args):
        raise PermissionError("kein Zugriff")

    monkeypatch.setattr(cli, "load_entries", kaputt)
    code, _, fehler = _starte(bmw, angemeldet, "verlauf")
    assert code == 1
    assert fehler.startswith("Dateifehler:")
