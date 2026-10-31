"""Integrationstest: echter SSH-Weg gegen die simulierte Headunit."""

import pytest

from bmw_hu_info.mock_server import MockHeadunit
from bmw_hu_info.ssh_client import (
    HeadunitClient,
    SSHVerbindungsError,
    Verbindungsdaten,
)


@pytest.fixture()
def headunit():
    server = MockHeadunit(port=0, passwort="test").start()
    yield server
    server.stop()


def _daten(server: MockHeadunit, passwort: str = "test") -> Verbindungsdaten:
    return Verbindungsdaten(
        host="127.0.0.1",
        port=server.port,
        benutzer="root",
        passwort=passwort,
    )


def test_verbindet_und_liest_hostname(headunit):
    with HeadunitClient(_daten(headunit)) as client:
        ergebnis = client.ausfuehren("hostname")
    assert ergebnis.erfolgreich
    assert "bmw-nbtevo" in ergebnis.ausgabe


def test_liest_fehlerspeicher_gefiltert(headunit):
    with HeadunitClient(_daten(headunit)) as client:
        ergebnis = client.ausfuehren("dmesg | grep -i -E 'error|fail|warn'")
    assert ergebnis.erfolgreich
    assert "error" in ergebnis.ausgabe.lower()


def test_liest_speicherbelegung(headunit):
    with HeadunitClient(_daten(headunit)) as client:
        ergebnis = client.ausfuehren("df -h")
    assert "/opt/bmw/data" in ergebnis.ausgabe


def test_falsches_passwort_wird_abgelehnt(headunit):
    with pytest.raises(SSHVerbindungsError):
        with HeadunitClient(_daten(headunit, passwort="falsch")):
            pass


def test_schreibbefehl_wird_vom_client_blockiert(headunit):
    from bmw_hu_info.safety import UnsichererBefehlError

    with HeadunitClient(_daten(headunit)) as client:
        with pytest.raises(UnsichererBefehlError):
            client.ausfuehren("rm -rf /")
