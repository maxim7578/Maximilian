"""RTP: Ton von vor dem Abheben (Freizeichen) darf nicht ins Gespräch gelangen."""

import numpy as np
import pytest

from assistent.handy import audio
from assistent.handy.sip import RtpStrom


def paket(wert: int) -> bytes:
    kopf = bytes([0x80, audio.PCMA]) + (1).to_bytes(2, "big") + (0).to_bytes(4, "big") + (1).to_bytes(4, "big")
    return kopf + audio.kodieren(np.full(audio.RAHMEN, wert, dtype=np.int16), audio.PCMA)


@pytest.mark.asyncio
async def test_freizeichen_vor_dem_abheben_wird_verworfen():
    rtp = RtpStrom()
    rtp.datagram_received(paket(5000), ("192.168.178.1", 7078))
    assert rtp.eingang.empty()
    rtp.verbinden("192.168.178.1", 7078, audio.PCMA)
    rtp.datagram_received(paket(5000), ("192.168.178.1", 7078))
    assert rtp.eingang.qsize() == 1
    rtp.schliessen()


@pytest.mark.asyncio
async def test_takt_bleibt_echtzeit_auch_wenn_die_schleife_blockiert():
    """Auch wenn das Programm kurz hängt, kommen pro Sekunde 50 Pakete an (Sprache nicht langsamer)."""
    import asyncio
    import socket
    import time

    empfaenger = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    empfaenger.bind(("127.0.0.1", 0))
    empfaenger.setblocking(False)
    rtp = RtpStrom()
    await rtp.starten("127.0.0.1")
    rtp.verbinden("127.0.0.1", empfaenger.getsockname()[1], audio.PCMA)
    start = time.perf_counter()
    for _ in range(4):
        time.sleep(0.25)  # blockiert absichtlich die asyncio-Schleife
        await asyncio.sleep(0)
    dauer = time.perf_counter() - start
    anzahl = 0
    while True:
        try:
            empfaenger.recv(2048)
            anzahl += 1
        except BlockingIOError:
            break
    rtp.schliessen()
    empfaenger.close()
    assert abs(anzahl - dauer / 0.02) <= 3
