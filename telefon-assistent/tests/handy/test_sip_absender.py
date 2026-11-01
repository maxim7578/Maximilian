"""SIP: Nur Nachrichten der FRITZ!Box werden angenommen, nicht die anderer Geräte im WLAN."""

import asyncio

import pytest
import pytest_asyncio

from assistent.handy.sip import Nachricht, Telefon

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


@pytest.mark.asyncio
async def test_re_invite_uebernimmt_neue_medienadresse(monkeypatch):
    """Halten/Weiterleiten: Die FRITZ!Box schickt ein re-INVITE mit neuem RTP-Port."""
    from types import SimpleNamespace

    from assistent.handy.sip import RtpStrom

    t = Telefon(FRITZBOX, "620", "geheim")
    t.server, t.lokale_ip = FRITZBOX, "192.168.178.20"
    gesendet = []
    monkeypatch.setattr(t, "_senden", lambda nachricht, ziel=None: gesendet.append(nachricht))
    rtp = RtpStrom()
    rtp.verbinden(FRITZBOX, 7078, 8)
    t._gespraeche["laufend"] = SimpleNamespace(rtp=rtp)
    sdp = "v=0\r\nc=IN IP4 192.168.178.1\r\nm=audio 7090 RTP/AVP 8\r\n"
    reinvite = INVITE.replace(b"gefaelscht@192.168.178.66", b"laufend").replace(
        b"Content-Length: 0", f"Content-Length: {len(sdp)}".encode()
    ) + sdp.encode()
    await t._anfrage_erhalten(Nachricht.parsen(reinvite), (FRITZBOX, 5060))
    assert rtp.ziel == (FRITZBOX, 7090)
    assert gesendet and gesendet[0].bytes().startswith(b"SIP/2.0 200")
    rtp.schliessen()


# ---------- Gefälschte Absender-IP: Medienadresse im SDP muss die FRITZ!Box sein ----------
# Ein INVITE mit gefälschter Absender-IP der FRITZ!Box käme durch den Absenderfilter.
# Mit "c=" auf ein anderes Gerät würde der RTP-Filter dann dessen Ton durchlassen.

ANGREIFER = "192.168.178.66"


def _invite_mit_sdp(medien_ip: str, call_id: str = "gefaelscht@192.168.178.66") -> bytes:
    sdp = f"v=0\r\nc=IN IP4 {medien_ip}\r\nm=audio 7078 RTP/AVP 8 0\r\n"
    return INVITE.replace(b"gefaelscht@192.168.178.66", call_id.encode()).replace(
        b"Content-Length: 0", f"Content-Length: {len(sdp)}".encode()
    ) + sdp.encode()


@pytest_asyncio.fixture
async def annehmendes_telefon(monkeypatch):
    t = Telefon(FRITZBOX, "620", "geheim")
    t.server, t.lokale_ip = FRITZBOX, "127.0.0.1"
    t.gesendet = []
    t.angenommen = []
    monkeypatch.setattr(t, "_senden", lambda nachricht, ziel=None: t.gesendet.append(nachricht.status))

    async def annehmen(gespraech):
        t.angenommen.append(gespraech)

    t.bei_eingehendem_anruf = annehmen
    yield t
    for gespraech in t.angenommen:
        gespraech.rtp.schliessen()


@pytest.mark.asyncio
async def test_eingehender_anruf_mit_fremder_medienadresse_wird_abgelehnt(annehmendes_telefon):
    t = annehmendes_telefon
    await t._eingehender_anruf(Nachricht.parsen(_invite_mit_sdp(ANGREIFER)), (FRITZBOX, 5060))
    assert 488 in t.gesendet
    assert 180 not in t.gesendet and 200 not in t.gesendet
    assert t.angenommen == [] and t._eingehend_offen == {}


@pytest.mark.asyncio
async def test_eingehender_anruf_mit_fritzbox_medienadresse_wird_angenommen(annehmendes_telefon):
    t = annehmendes_telefon
    await t._eingehender_anruf(Nachricht.parsen(_invite_mit_sdp(FRITZBOX)), (FRITZBOX, 5060))
    assert t.gesendet[-1] == 200 and 488 not in t.gesendet
    assert len(t.angenommen) == 1
    assert t.angenommen[0].rtp.ziel == (FRITZBOX, 7078)


@pytest.mark.asyncio
async def test_re_invite_mit_fremder_medienadresse_wird_nicht_uebernommen(monkeypatch):
    from types import SimpleNamespace

    from assistent.handy.sip import RtpStrom

    t = Telefon(FRITZBOX, "620", "geheim")
    t.server, t.lokale_ip = FRITZBOX, "192.168.178.20"
    gesendet = []
    monkeypatch.setattr(t, "_senden", lambda nachricht, ziel=None: gesendet.append(nachricht))
    rtp = RtpStrom()
    rtp.verbinden(FRITZBOX, 7078, 8)
    t._gespraeche["laufend"] = SimpleNamespace(rtp=rtp)
    await t._anfrage_erhalten(Nachricht.parsen(_invite_mit_sdp(ANGREIFER, "laufend")), (FRITZBOX, 5060))
    assert rtp.ziel == (FRITZBOX, 7078), "Medienadresse des Angreifers übernommen"
    assert gesendet and gesendet[0].bytes().startswith(b"SIP/2.0 200")
    rtp.schliessen()


# ---------- Mengenlimit: über dem Limit nur klingeln lassen ----------


@pytest.mark.asyncio
async def test_eingehender_anruf_ueber_dem_limit_klingelt_nur(annehmendes_telefon):
    t = annehmendes_telefon
    gefragt = []

    def zulassen(nummer):
        gefragt.append(nummer)
        return False

    t.eingehend_zulassen = zulassen
    await t._eingehender_anruf(Nachricht.parsen(_invite_mit_sdp(FRITZBOX)), (FRITZBOX, 5060))
    assert gefragt == ["fritzbox"]
    assert t.gesendet == [100, 180]
    assert t.angenommen == []
    assert "gefaelscht@192.168.178.66" in t._eingehend_offen  # CANCEL beendet das Klingeln
