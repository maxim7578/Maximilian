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
