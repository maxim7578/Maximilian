import json
import ssl

import httpx
from datetime import datetime, timezone

import paho.mqtt.client as mqtt
import pytest
from conftest import VIN, VIN2

from bmw_cardata.auth import Tokens
from bmw_cardata.stream import (
    STREAM_HOST,
    STREAM_PORT,
    Credentials,
    StreamError,
    create_client,
    message_lines,
    parse_message,
    run_stream,
    stream_credentials,
    tls_context,
    topic_for,
)

KM = "vehicle.vehicle.travelledDistance"
NACHRICHT = json.dumps({"vin": VIN, "data": {KM: {"value": 42063, "unit": "km"}}}).encode()


class Code:
    """Nachgebauter paho-ReasonCode."""

    def __init__(self, name="Success"):
        self.name = name
        self.is_failure = name != "Success"

    def __str__(self):
        return self.name


class Nachricht:
    def __init__(self, payload):
        self.payload = payload


def verbunden(client):
    client.on_connect(client, None, {}, Code(), None)
    return 0


def abgelehnt(name):
    def schritt(client):
        client.on_connect(client, None, {}, Code(name), None)
        return 0

    return schritt


def empfangen(payload=NACHRICHT):
    def schritt(client):
        client.on_message(client, None, Nachricht(payload))
        return 0

    return schritt


def getrennt(client):
    client.on_disconnect(client, None, {}, Code("Unspecified error"), None)
    return mqtt.MQTT_ERR_CONN_LOST


class FakeClient:
    """Spielt eine feste Abfolge von loop()-Ergebnissen ab und protokolliert die Aufrufe."""

    def __init__(self, *schritte, reconnect_fehler=0, am_ende=None, abo_abgelehnt=False):
        self.schritte = list(schritte)
        self.aufrufe = []
        self.reconnect_fehler = reconnect_fehler
        self.am_ende = am_ende
        self.abo_abgelehnt = abo_abgelehnt
        self.on_connect = self.on_message = self.on_disconnect = self.on_subscribe = None

    def username_pw_set(self, username, password):
        self.aufrufe.append(("anmeldung", username, password))

    def connect(self, host, port, keepalive):
        self.aufrufe.append(("verbinden", host, port))

    def reconnect(self):
        self.aufrufe.append(("neu",))
        if self.reconnect_fehler:
            self.reconnect_fehler -= 1
            raise ConnectionRefusedError("keine Verbindung")

    def subscribe(self, topic):
        self.aufrufe.append(("abonnieren", topic))
        if self.on_subscribe and self.abo_abgelehnt:
            self.on_subscribe(self, None, 1, [Code("Unspecified error")], None)
        return (0, 1)

    def disconnect(self):
        self.aufrufe.append(("trennen",))

    def loop(self, timeout):
        if not self.schritte:
            if self.am_ende:
                raise self.am_ende
            return 0
        schritt = self.schritte.pop(0)
        return schritt(self) if callable(schritt) else schritt

    def arten(self):
        return [aufruf[0] for aufruf in self.aufrufe]


class Zugang:
    """Liefert Zugangsdaten und zählt, wie oft eine Erneuerung erzwungen wurde."""

    def __init__(self, *ablaufzeiten, netzfehler=0, gleiches_token=False):
        self.ablaufzeiten = list(ablaufzeiten) or [10_000.0]
        self.erzwungen = 0
        self.netzfehler = netzfehler
        self.gleiches_token = gleiches_token

    def __call__(self, force):
        if force and self.netzfehler:
            self.netzfehler -= 1
            raise httpx.ConnectError("kein Netz")
        if force and not self.gleiches_token:
            self.erzwungen += 1
        index = min(self.erzwungen, len(self.ablaufzeiten) - 1)
        return Credentials("gcid-1", f"id-token-{self.erzwungen}", self.ablaufzeiten[index])


def _uhr(*zeiten):
    """Uhr, die die angegebenen Zeiten liefert und danach bei der letzten stehen bleibt."""
    folge = list(zeiten)
    return lambda: folge.pop(0) if len(folge) > 1 else folge[0]


def _laufen(client, zugang=None, uhr=lambda: 0.0):
    erhalten, hinweise, pausen = [], [], []
    run_stream(
        client,
        zugang or Zugang(),
        lambda vin, daten: erhalten.append((vin, daten)),
        hinweise.append,
        clock=uhr,
        sleep=pausen.append,
        stop=lambda: not client.schritte,
    )
    return erhalten, hinweise, pausen


def _tokens(**felder):
    werte = {"access_token": "a", "refresh_token": "r", "expires_at": 100.0,
             "scope": "openid cardata:api:read cardata:streaming:read", "id_token": "idt", "gcid": "g-1"}
    return Tokens(**{**werte, **felder})


def test_topic_umfasst_alle_fahrzeuge_des_kontos():
    assert topic_for("gcid-1") == "gcid-1/+"


def test_zugangsdaten_kommen_aus_der_anmeldung():
    assert stream_credentials(_tokens()) == Credentials("g-1", "idt", 100.0)


@pytest.mark.parametrize("felder", [{"gcid": ""}, {"id_token": ""}, {"scope": "openid cardata:api:read"}])
def test_ohne_streaming_berechtigung_wird_neu_anmelden_verlangt(felder):
    with pytest.raises(StreamError, match="neu anmelden"):
        stream_credentials(_tokens(**felder))


def test_ohne_angegebenen_scope_genügen_gcid_und_id_token():
    assert stream_credentials(_tokens(scope="")).gcid == "g-1"


def test_gültige_nachricht_wird_gelesen():
    assert parse_message(NACHRICHT) == (VIN, {KM: {"value": 42063, "unit": "km"}})


def test_fahrgestellnummer_wird_vereinheitlicht_und_kaputte_einträge_verworfen():
    roh = json.dumps({"vin": VIN.lower(), "data": {KM: {"value": 1}, "kaputt": 5}}).encode()
    assert parse_message(roh) == (VIN, {KM: {"value": 1}})


@pytest.mark.parametrize("roh", [
    b"kein json", b"\xff\xfe", b"[1, 2]", json.dumps({"data": {}}).encode(),
    json.dumps({"vin": "../x", "data": {}}).encode(), json.dumps({"vin": VIN, "data": [1]}).encode(),
    json.dumps({"vin": 5, "data": {}}).encode(),
])
def test_ungültige_nachrichten_werden_ignoriert(roh):
    assert parse_message(roh) is None


def test_nachrichtenzeilen_mit_bekannten_und_unbekannten_datenpunkten():
    daten = {KM: {"value": 42063, "unit": "km"}, "vehicle.cabin.hvac.temp": {"value": 21, "unit": "°C"},
             "leer": {"value": None}}
    zeit = datetime(2026, 10, 31, 15, 12, 4, tzinfo=timezone.utc)
    assert message_lines(daten, zeit) == [
        "15:12:04  Kilometerstand: 42063 km",
        "15:12:04  vehicle.cabin.hvac.temp: 21 °C",
    ]


def test_steuerzeichen_aus_dem_netz_erreichen_das_terminal_nicht():
    daten = {"vehicle.\x1b[2Jx": {"value": "a\x1b]0;titel\x07b\nc"}}
    zeile = message_lines(daten, datetime(2026, 1, 1, tzinfo=timezone.utc))[0]
    assert "\x1b" not in zeile and "\x07" not in zeile and "\n" not in zeile


def test_verbindung_anmeldung_abonnement_und_nachrichten():
    client = FakeClient(verbunden, empfangen(), 0)
    erhalten, hinweise, _ = _laufen(client)
    assert client.aufrufe[:2] == [("anmeldung", "gcid-1", "id-token-0"), ("verbinden", STREAM_HOST, STREAM_PORT)]
    assert ("abonnieren", "gcid-1/+") in client.aufrufe
    assert erhalten == [(VIN, {KM: {"value": 42063, "unit": "km"}})]
    assert any("Verbunden" in h for h in hinweise)
    assert client.arten()[-1] == "trennen"


def test_unlesbare_nachrichten_werden_still_übergangen():
    client = FakeClient(verbunden, empfangen(b"kein json"))
    assert _laufen(client)[0] == []


def test_zugang_wird_vor_dem_ablauf_erneuert_und_neu_verbunden():
    zeit = iter([0.0, 9_800.0, 9_800.0, 9_800.0, 9_800.0])
    client = FakeClient(verbunden, 0, verbunden)
    zugang = Zugang(10_000.0, 20_000.0)
    _, _, pausen = _laufen(client, zugang, uhr=lambda: next(zeit, 9_800.0))
    assert zugang.erzwungen == 1
    assert pausen == [2]
    assert ("anmeldung", "gcid-1", "id-token-1") in client.aufrufe
    assert client.arten().count("neu") == 1


def test_erneuerung_ohne_längere_gültigkeit_bricht_ab():
    client = FakeClient(verbunden, 0, 0)
    with pytest.raises(StreamError, match="neu anmelden"):
        _laufen(client, Zugang(100.0, 100.0), uhr=lambda: 99.0)
    assert client.arten()[-1] == "trennen"


def test_einmalige_ablehnung_wird_nach_kurzer_pause_wiederholt():
    client = FakeClient(abgelehnt("Not authorized"), verbunden, empfangen())
    zugang = Zugang()
    erhalten, _, pausen = _laufen(client, zugang)
    assert zugang.erzwungen == 0
    assert pausen == [3]
    assert len(erhalten) == 1


def test_zweite_ablehnung_erneuert_den_zugang():
    client = FakeClient(abgelehnt("Not authorized"), abgelehnt("Not authorized"), verbunden)
    zugang = Zugang()
    _, _, pausen = _laufen(client, zugang)
    assert zugang.erzwungen == 1
    assert pausen == [3, 3]
    assert ("anmeldung", "gcid-1", "id-token-1") in client.aufrufe


def test_dritte_ablehnung_in_folge_erklärt_die_üblichen_ursachen():
    client = FakeClient(*[abgelehnt("Not authorized")] * 3)
    with pytest.raises(StreamError) as fehler:
        _laufen(client)
    assert "Home Assistant" in str(fehler.value) and "CarData Stream" in str(fehler.value)


def test_ablehnung_nach_erfolgreicher_verbindung_beginnt_wieder_von_vorn():
    client = FakeClient(abgelehnt("Not authorized"), verbunden, abgelehnt("Not authorized"), verbunden)
    zugang = Zugang()
    _laufen(client, zugang)
    assert zugang.erzwungen == 0


def test_erneuerung_ohne_neues_id_token_verlangt_neu_anmelden():
    client = FakeClient(abgelehnt("Not authorized"), abgelehnt("Not authorized"))
    with pytest.raises(StreamError, match="neu anmelden"):
        _laufen(client, Zugang(gleiches_token=True))


def test_netzfehler_bei_der_erneuerung_wird_später_wiederholt():
    client = FakeClient(verbunden, 0, 0, verbunden)
    zugang = Zugang(10_000.0, 20_000.0, netzfehler=1)
    _, hinweise, pausen = _laufen(client, zugang, uhr=_uhr(0.0, 9_800.0))
    assert zugang.erzwungen == 1
    assert pausen == [5, 2]
    assert any("ConnectError" in h for h in hinweise)


def test_verbindungsabbruch_wartet_immer_länger_und_verbindet_neu():
    client = FakeClient(verbunden, getrennt, mqtt.MQTT_ERR_NO_CONN, mqtt.MQTT_ERR_NO_CONN, verbunden,
                        reconnect_fehler=1)
    _, hinweise, pausen = _laufen(client)
    assert pausen == [5, 10, 30]
    assert client.arten().count("neu") == 3
    assert sum("neuer Versuch" in h for h in hinweise) == 3


def test_nach_stabiler_verbindung_beginnt_die_wartezeit_von_vorn():
    client = FakeClient(getrennt, verbunden, 0, getrennt)
    assert _laufen(client, uhr=_uhr(0.0, 0.0, 100.0, 100.0, 100.0))[2] == [5, 5]


def test_nach_der_ersten_nachricht_gilt_die_verbindung_als_stabil():
    client = FakeClient(getrennt, verbunden, empfangen(), getrennt)
    assert _laufen(client)[2] == [5, 5]


def test_kurze_verbindungen_steigern_die_wartezeit_weiter():
    client = FakeClient(getrennt, verbunden, getrennt)
    assert _laufen(client)[2] == [5, 10]


def test_ständiges_hinauswerfen_deutet_auf_eine_zweite_verbindung():
    client = FakeClient(*[verbunden, getrennt] * 3)
    with pytest.raises(StreamError, match="Home Assistant"):
        _laufen(client)


def test_abgelehntes_abo_verweist_auf_das_portal():
    client = FakeClient(verbunden, 0, abo_abgelehnt=True)
    with pytest.raises(StreamError, match="Portal"):
        _laufen(client)


def test_zertifikatsfehler_bricht_sofort_ab():
    class FalschesZertifikat(FakeClient):
        def connect(self, host, port, keepalive):
            raise ssl.SSLCertVerificationError("certificate verify failed")

    with pytest.raises(StreamError, match="Zertifikat"):
        _laufen(FalschesZertifikat(0))


def test_tls_fehler_bricht_mit_hinweis_auf_tls_13_ab():
    class AltesTls(FakeClient):
        def connect(self, host, port, keepalive):
            raise ssl.SSLError("unsupported protocol")

    with pytest.raises(StreamError, match="TLS 1.3"):
        _laufen(AltesTls(0))


def test_verbindungsfehler_nennt_die_art_des_fehlers():
    client = FakeClient(mqtt.MQTT_ERR_NO_CONN, verbunden, reconnect_fehler=1)
    hinweise = _laufen(client)[1]
    assert any("ConnectionRefusedError" in h for h in hinweise)


def test_server_nicht_verfügbar_ist_kein_abbruchgrund():
    client = FakeClient(abgelehnt("Server unavailable"), mqtt.MQTT_ERR_CONN_REFUSED, verbunden)
    _, _, pausen = _laufen(client)
    assert pausen == [5]


def test_erste_verbindung_ohne_netz_wird_später_wiederholt():
    class OhneNetz(FakeClient):
        def connect(self, host, port, keepalive):
            super().connect(host, port, keepalive)
            raise OSError("kein Netz")

    client = OhneNetz(mqtt.MQTT_ERR_NO_CONN, verbunden)
    assert _laufen(client)[2] == [5]


def test_abbruch_mit_strg_c_trennt_die_verbindung():
    client = FakeClient(verbunden, am_ende=KeyboardInterrupt())
    with pytest.raises(KeyboardInterrupt):
        run_stream(client, Zugang(), lambda v, d: None, lambda h: None, clock=lambda: 0.0, sleep=lambda s: None)
    assert client.arten()[-1] == "trennen"


def test_echter_client_nutzt_mqtt_311_und_tls():
    client = create_client("gcid-1")
    assert isinstance(client, mqtt.Client)
    assert client.protocol == mqtt.MQTTv311


def test_tls_prüft_das_zertifikat():
    kontext = tls_context()
    assert kontext.verify_mode == ssl.CERT_REQUIRED
    assert kontext.check_hostname is True
    assert kontext.minimum_version == ssl.TLSVersion.TLSv1_3


def test_mehrere_fahrzeuge_kommen_über_ein_abonnement():
    zweite = json.dumps({"vin": VIN2, "data": {KM: {"value": 7}}}).encode()
    client = FakeClient(verbunden, empfangen(), empfangen(zweite))
    assert [vin for vin, _ in _laufen(client)[0]] == [VIN, VIN2]


def test_netzfehler_bei_der_erneuerung_nach_ablehnung_wartet_und_versucht_es_erneut():
    client = FakeClient(abgelehnt("Not authorized"), abgelehnt("Not authorized"), mqtt.MQTT_ERR_NO_CONN, verbunden)
    zugang = Zugang(netzfehler=1)
    _, _, pausen = _laufen(client, zugang)
    assert pausen == [3, 5, 10]
    assert zugang.erzwungen == 0
