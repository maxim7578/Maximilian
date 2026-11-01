"""Tests der Verbindungspruefung gegen die simulierte Headunit."""

import pytest

from bmw_hu_info import connectivity
from bmw_hu_info.connectivity import ist_erreichbar
from bmw_hu_info.mock_server import MockHeadunit
from bmw_hu_info.ssh_client import Verbindungsdaten


@pytest.fixture()
def headunit():
    server = MockHeadunit(port=0, passwort="test").start()
    yield server
    server.stop()


def test_erreichbar_bei_laufendem_server(headunit):
    assert ist_erreichbar("127.0.0.1", headunit.port)


def test_nicht_erreichbar_bei_geschlossenem_port():
    # Port 1 ist praktisch nie offen.
    assert not ist_erreichbar("127.0.0.1", 1, zeitlimit=1.0)


def test_leerer_host_ist_nicht_erreichbar():
    assert not ist_erreichbar("", 22)


def test_teste_verbindung_erfolg(headunit):
    daten = Verbindungsdaten(host="127.0.0.1", port=headunit.port, passwort="test")
    status = connectivity.teste_verbindung(daten)
    assert status.verbunden
    assert status.erreichbar
    assert "bmw-nbtevo" in status.meldung


def test_teste_verbindung_falsches_passwort(headunit):
    daten = Verbindungsdaten(host="127.0.0.1", port=headunit.port, passwort="falsch")
    status = connectivity.teste_verbindung(daten)
    assert not status.verbunden
    assert status.erreichbar  # erreichbar, aber Anmeldung scheitert


def test_teste_verbindung_nicht_erreichbar():
    daten = Verbindungsdaten(host="127.0.0.1", port=1, passwort="x", zeitlimit=1.0)
    status = connectivity.teste_verbindung(daten)
    assert not status.verbunden
    assert not status.erreichbar
    assert "nicht erreichbar" in status.meldung.lower()
