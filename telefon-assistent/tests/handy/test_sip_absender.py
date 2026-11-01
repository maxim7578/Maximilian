"""SIP: Nur Nachrichten der FRITZ!Box werden angenommen, nicht die anderer Geräte im WLAN."""

import asyncio

import pytest

from assistent.handy.sip import Telefon

FRITZBOX = "192.168.178.1"

INVITE = (
    "INVITE sip:620@192.168.178.20:5062 SIP/2.0\r\n"
    "Via: SIP/2.0/UDP 192.168.178.66:5060;branch=z9hG4bKangriff\r\n"
    "From: <sip:fritzbox@192.168.178.1>;tag=1\r\n"
    "To: <sip:620@192.168.178.20>\r\n"
    "Call-ID: gefaelscht@192.168.178.66\r\n"
    "CSeq: 1 INVITE\r\n"
    "Content-Length: 0\r\n\r\n"
).encode()


@pytest.fixture
def telefon(monkeypatch):
    t = Telefon(FRITZBOX, "620", "geheim")
    t.server = FRITZBOX
    t.erhalten = []

    async def merken(anfrage, adresse):
        t.erhalten.append(adresse)

    monkeypatch.setattr(t, "_anfrage_erhalten", merken)
    return t


@pytest.mark.asyncio
async def test_anfrage_von_fremdem_geraet_wird_verworfen(telefon):
    telefon.datagram_received(INVITE, ("192.168.178.66", 5060))
    await asyncio.sleep(0)
    assert telefon.erhalten == []


@pytest.mark.asyncio
async def test_anfrage_der_fritzbox_wird_angenommen(telefon):
    telefon.datagram_received(INVITE, (FRITZBOX, 5060))
    await asyncio.sleep(0)
    assert telefon.erhalten == [(FRITZBOX, 5060)]
