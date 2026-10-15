"""Schlankes IP-Telefon (SIP über UDP + RTP) für die Anmeldung an der FRITZ!Box.

Unterstützt: Anmeldung (REGISTER mit Digest), ausgehende und eingehende Anrufe mit
G.711 (A-law/µ-law), Auflegen in beide Richtungen, Abbrechen (CANCEL), Besetzt usw.
"""

import asyncio
import hashlib
import random
import re
import socket
import uuid
from collections import deque
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field

import numpy as np
from loguru import logger

from . import audio

T1 = 0.5
KURZFORMEN = {
    "i": "call-id", "f": "from", "t": "to", "v": "via", "m": "contact",
    "l": "content-length", "c": "content-type", "k": "supported", "s": "subject",
}
GRUENDE = {
    486: "besetzt", 600: "besetzt", 603: "abgelehnt", 480: "nicht erreichbar",
    404: "Nummer nicht vergeben", 484: "Nummer unvollständig", 408: "keine Antwort",
    487: "abgebrochen", 503: "Leitung nicht verfügbar",
}


class SipFehler(Exception):
    pass


class AnrufFehler(Exception):
    """Anruf kam nicht zustande (besetzt, keiner nimmt ab …)."""


def _zufall(n: int = 10) -> str:
    return uuid.uuid4().hex[:n]


def _md5(text: str) -> str:
    return hashlib.md5(text.encode()).hexdigest()


@dataclass
class Nachricht:
    erste_zeile: str
    kopf: list[tuple[str, str]]
    rumpf: bytes = b""

    @property
    def ist_antwort(self) -> bool:
        return self.erste_zeile.startswith("SIP/2.0")

    @property
    def status(self) -> int:
        return int(self.erste_zeile.split()[1]) if self.ist_antwort else 0

    @property
    def methode(self) -> str:
        if self.ist_antwort:
            return self.cseq[1]
        return self.erste_zeile.split()[0].upper()

    def get(self, name: str, standard: str = "") -> str:
        werte = self.alle(name)
        return werte[0] if werte else standard

    def alle(self, name: str) -> list[str]:
        name = name.lower()
        return [w for n, w in self.kopf if KURZFORMEN.get(n.lower(), n.lower()) == name]

    @property
    def cseq(self) -> tuple[int, str]:
        nummer, methode = self.get("cseq", "0 X").split()
        return int(nummer), methode.upper()

    @property
    def zweig(self) -> str:
        treffer = re.search(r"branch=([^;,\s]+)", self.get("via"))
        return treffer.group(1) if treffer else ""

    @staticmethod
    def parsen(daten: bytes) -> "Nachricht":
        kopf_teil, _, rumpf = daten.partition(b"\r\n\r\n")
        zeilen = kopf_teil.decode("utf-8", "replace").split("\r\n")
        kopf: list[tuple[str, str]] = []
        for zeile in zeilen[1:]:
            if zeile[:1] in (" ", "\t") and kopf:  # Fortsetzungszeile
                n, w = kopf[-1]
                kopf[-1] = (n, w + " " + zeile.strip())
            elif ":" in zeile:
                n, w = zeile.split(":", 1)
                kopf.append((n.strip(), w.strip()))
        return Nachricht(zeilen[0], kopf, rumpf)

    def bytes(self) -> bytes:
        kopf = [(n, w) for n, w in self.kopf if n.lower() not in ("content-length", "l")]
        kopf.append(("Content-Length", str(len(self.rumpf))))
        text = self.erste_zeile + "\r\n" + "".join(f"{n}: {w}\r\n" for n, w in kopf) + "\r\n"
        return text.encode() + self.rumpf


def _tag(kopfwert: str) -> str:
    treffer = re.search(r";\s*tag=([^;>\s]+)", kopfwert)
    return treffer.group(1) if treffer else ""


def _uri(kopfwert: str) -> str:
    treffer = re.search(r"<([^>]+)>", kopfwert)
    return treffer.group(1) if treffer else kopfwert.split(";")[0].strip()


def nummer_aus(kopfwert: str) -> str:
    treffer = re.search(r"sips?:([^@;>]+)", kopfwert)
    return treffer.group(1) if treffer else ""


def digest_antwort(methode: str, uri: str, benutzer: str, kennwort: str, herausforderung: str) -> str:
    werte = dict(re.findall(r'(\w+)="?([^",]*)"?', herausforderung))
    realm, nonce = werte.get("realm", ""), werte.get("nonce", "")
    ha1 = _md5(f"{benutzer}:{realm}:{kennwort}")
    ha2 = _md5(f"{methode}:{uri}")
    teile = [
        f'username="{benutzer}"', f'realm="{realm}"', f'nonce="{nonce}"', f'uri="{uri}"',
    ]
    if "auth" in [q.strip() for q in werte.get("qop", "").split(",")]:
        cnonce, nc = _zufall(16), "00000001"
        antwort = _md5(f"{ha1}:{nonce}:{nc}:{cnonce}:auth:{ha2}")
        teile += [f'response="{antwort}"', "qop=auth", f"nc={nc}", f'cnonce="{cnonce}"']
    else:
        teile.append(f'response="{_md5(f"{ha1}:{nonce}:{ha2}")}"')
    teile.append("algorithm=MD5")
    if "opaque" in werte:
        teile.append(f'opaque="{werte["opaque"]}"')
    return "Digest " + ", ".join(teile)


def sdp_bauen(ip: str, port: int, nutzlasten: list[int]) -> bytes:
    sitzung = random.randint(100000, 999999)
    namen = {audio.PCMA: "PCMA/8000", audio.PCMU: "PCMU/8000"}
    zeilen = [
        "v=0", f"o=- {sitzung} {sitzung} IN IP4 {ip}", "s=KI-Assistent", f"c=IN IP4 {ip}", "t=0 0",
        f"m=audio {port} RTP/AVP {' '.join(map(str, nutzlasten))} 101",
        *[f"a=rtpmap:{n} {namen[n]}" for n in nutzlasten],
        "a=rtpmap:101 telephone-event/8000", "a=fmtp:101 0-16", "a=ptime:20", "a=sendrecv",
    ]
    return ("\r\n".join(zeilen) + "\r\n").encode()


def sdp_lesen(rumpf: bytes) -> tuple[str, int, list[int]]:
    text = rumpf.decode("utf-8", "replace")
    ip = re.search(r"^c=IN IP4 (\S+)", text, re.M)
    medien = re.search(r"^m=audio (\d+) RTP/AVP ([\d ]+)", text, re.M)
    if not (ip and medien):
        raise SipFehler("Ungültige Medienbeschreibung (SDP)")
    return ip.group(1), int(medien.group(1)), [int(n) for n in medien.group(2).split()]


class RtpStrom(asyncio.DatagramProtocol):
    """Sendet und empfängt Sprache als RTP-Pakete im 20-ms-Takt."""

    def __init__(self):
        self.ziel: tuple[str, int] | None = None
        self.nutzlast = audio.PCMA
        self.eingang: asyncio.Queue[np.ndarray] = asyncio.Queue(maxsize=500)
        self._ausgang: deque[np.ndarray] = deque()
        self._transport: asyncio.DatagramTransport | None = None
        self._sender: asyncio.Task | None = None
        self._seq = random.randint(0, 65535)
        self._zeit = random.randint(0, 2**31)
        self._ssrc = random.randint(0, 2**31)
        self._leer = asyncio.Event()
        self._leer.set()
        self.port = 0

    async def starten(self, ip: str) -> int:
        loop = asyncio.get_running_loop()
        for _ in range(50):
            port = random.randrange(10000, 20000, 2)
            try:
                self._transport, _ = await loop.create_datagram_endpoint(lambda: self, local_addr=(ip, port))
                self.port = port
                return port
            except OSError:
                continue
        raise SipFehler("Kein freier RTP-Port")

    def verbinden(self, ip: str, port: int, nutzlast: int) -> None:
        self.ziel, self.nutzlast = (ip, port), nutzlast
        if self._sender is None:
            self._sender = asyncio.create_task(self._senden_im_takt())

    def datagram_received(self, daten: bytes, adresse) -> None:
        if len(daten) < 12 or daten[0] >> 6 != 2:
            return
        nutzlast = daten[1] & 0x7F
        if nutzlast not in (audio.PCMA, audio.PCMU):
            return  # z. B. Tastentöne oder Komfortrauschen
        start = 12 + 4 * (daten[0] & 0x0F)
        if daten[0] & 0x10 and len(daten) >= start + 4:  # Erweiterungskopf
            start += 4 + 4 * int.from_bytes(daten[start + 2:start + 4], "big")
        ende = len(daten) - (daten[-1] if daten[0] & 0x20 else 0)
        if self.ziel and adresse != self.ziel:
            self.ziel = adresse  # symmetrisches RTP: dorthin antworten, woher es kommt
        try:
            self.eingang.put_nowait(audio.dekodieren(daten[start:ende], nutzlast))
        except asyncio.QueueFull:
            pass

    def senden(self, pcm: np.ndarray) -> None:
        pcm = audio.als_int16(pcm)
        for i in range(0, len(pcm), audio.RAHMEN):
            stueck = pcm[i:i + audio.RAHMEN]
            if len(stueck) < audio.RAHMEN:
                stueck = np.pad(stueck, (0, audio.RAHMEN - len(stueck)))
            self._ausgang.append(stueck)
        if self._ausgang:
            self._leer.clear()

    def leeren(self) -> None:
        self._ausgang.clear()
        self._leer.set()

    @property
    def spielt(self) -> bool:
        return bool(self._ausgang)

    async def warte_bis_ausgegeben(self) -> None:
        await self._leer.wait()

    async def _senden_im_takt(self) -> None:
        loop = asyncio.get_running_loop()
        stille = np.zeros(audio.RAHMEN, dtype=np.int16)
        naechster = loop.time()
        while True:
            rahmen = self._ausgang.popleft() if self._ausgang else stille
            if not self._ausgang:
                self._leer.set()
            if self._transport and self.ziel:
                kopf = bytes([0x80, self.nutzlast]) + self._seq.to_bytes(2, "big")
                kopf += self._zeit.to_bytes(4, "big") + self._ssrc.to_bytes(4, "big")
                self._transport.sendto(kopf + audio.kodieren(rahmen, self.nutzlast), self.ziel)
            self._seq = (self._seq + 1) % 65536
            self._zeit = (self._zeit + audio.RAHMEN) % 2**32
            naechster += 0.02
            warten = naechster - loop.time()
            if warten < -0.2:  # zu weit hinterher (z. B. Handy war kurz ausgelastet)
                naechster = loop.time()
                warten = 0
            await asyncio.sleep(max(0.0, warten))

    def schliessen(self) -> None:
        if self._sender:
            self._sender.cancel()
        if self._transport:
            self._transport.close()


@dataclass
class Telefonat:
    """Ein laufendes Gespräch – Schnittstelle für die Gesprächssteuerung."""

    telefon: "Telefon"
    call_id: str
    lokal_tag: str
    lokal_kopf: str  # From (ausgehend) bzw. To (eingehend) aus unserer Sicht
    fern_kopf: str
    fern_ziel: str
    rtp: RtpStrom
    richtung: str  # "raus" oder "rein"
    fern_nummer: str = ""
    cseq: int = 1
    beendet: asyncio.Event = field(default_factory=asyncio.Event)
    grund: str = ""

    async def empfangen(self) -> np.ndarray | None:
        """Nächstes Stück Ton vom Gegenüber; None, wenn das Gespräch vorbei ist.

        Kommt 100 ms lang nichts an (z. B. Stillepausen), wird entsprechend Stille geliefert,
        damit die Sprecherkennung im richtigen Takt bleibt.
        """
        if self.beendet.is_set():
            return None
        try:
            return await asyncio.wait_for(self.rtp.eingang.get(), 0.1)
        except TimeoutError:
            return None if self.beendet.is_set() else np.zeros(5 * audio.RAHMEN, dtype=np.int16)

    def senden(self, pcm: np.ndarray) -> None:
        self.rtp.senden(pcm)

    def leeren(self) -> None:
        self.rtp.leeren()

    @property
    def spielt(self) -> bool:
        return self.rtp.spielt

    async def warte_bis_ausgegeben(self) -> None:
        await self.rtp.warte_bis_ausgegeben()

    async def auflegen(self) -> None:
        if self.beendet.is_set():
            return
        await self.telefon._bye(self)
        self._ende("aufgelegt")

    def _ende(self, grund: str) -> None:
        if not self.beendet.is_set():
            self.grund = grund
            self.beendet.set()
            self.rtp.schliessen()
            self.telefon._gespraeche.pop(self.call_id, None)


EingehendRueckruf = Callable[[Telefonat], Awaitable[None]]


class Telefon(asyncio.DatagramProtocol):
    """IP-Telefon, das sich an der FRITZ!Box (oder einer anderen SIP-Anlage) anmeldet."""

    def __init__(
        self,
        server: str,
        benutzer: str,
        kennwort: str,
        server_port: int = 5060,
        lokaler_port: int = 5062,
        ablauf: int = 300,
    ):
        self.server_host = server
        self.server_port = server_port
        self.benutzer = benutzer
        self.kennwort = kennwort
        self.lokaler_port = lokaler_port
        self.ablauf = ablauf
        self.server = ""
        self.lokale_ip = ""
        self.angemeldet = False
        self.letzter_fehler = ""
        self.bei_eingehendem_anruf: EingehendRueckruf | None = None
        self._transport: asyncio.DatagramTransport | None = None
        self._offen: dict[str, tuple[asyncio.Future, Callable | None, asyncio.Event]] = {}
        self._gespraeche: dict[str, Telefonat] = {}
        self._eingehend_offen: dict[str, Nachricht] = {}
        self._anmelde_aufgabe: asyncio.Task | None = None
        self._reg_call_id = _zufall(16)
        self._reg_cseq = 0
        self._reg_tag = _zufall(8)

    # ---------- Start / Anmeldung ----------

    async def starten(self) -> None:
        loop = asyncio.get_running_loop()
        infos = await loop.getaddrinfo(self.server_host, self.server_port, family=socket.AF_INET)
        self.server = infos[0][4][0]
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect((self.server, self.server_port))
            self.lokale_ip = s.getsockname()[0]
        self._transport, _ = await loop.create_datagram_endpoint(
            lambda: self, local_addr=(self.lokale_ip, self.lokaler_port)
        )
        self.lokaler_port = self._transport.get_extra_info("sockname")[1]
        self._anmelde_aufgabe = asyncio.create_task(self._anmelden_dauerhaft())

    async def stoppen(self) -> None:
        if self._anmelde_aufgabe:
            self._anmelde_aufgabe.cancel()
        for g in list(self._gespraeche.values()):
            await g.auflegen()
        if self.angemeldet:
            try:
                await self._register(ablauf=0)
            except Exception:
                pass
        if self._transport:
            self._transport.close()

    @property
    def _kontakt(self) -> str:
        return f"<sip:{self.benutzer}@{self.lokale_ip}:{self.lokaler_port}>"

    @property
    def _ich(self) -> str:
        return f"<sip:{self.benutzer}@{self.server}>"

    async def _anmelden_dauerhaft(self) -> None:
        while True:
            try:
                await self._register(self.ablauf)
                self.angemeldet, self.letzter_fehler = True, ""
                await asyncio.sleep(self.ablauf * 0.8)
            except asyncio.CancelledError:
                raise
            except Exception as fehler:
                self.angemeldet, self.letzter_fehler = False, str(fehler)
                logger.warning(f"Anmeldung an {self.server} fehlgeschlagen: {fehler}")
                await asyncio.sleep(30)

    async def _register(self, ablauf: int) -> None:
        uri = f"sip:{self.server}"
        autorisierung: tuple[str, str] | None = None
        for _ in range(3):
            self._reg_cseq += 1
            kopf = [
                ("From", f"{self._ich};tag={self._reg_tag}"), ("To", self._ich),
                ("Call-ID", self._reg_call_id), ("CSeq", f"{self._reg_cseq} REGISTER"),
                ("Contact", self._kontakt), ("Expires", str(ablauf)),
            ]
            if autorisierung:
                kopf.append(autorisierung)
            antwort = await self._anfrage("REGISTER", uri, kopf)
            if antwort.status in (401, 407):
                autorisierung = self._auth_kopf(antwort, "REGISTER", uri)
                continue
            if 200 <= antwort.status < 300:
                return
            raise SipFehler(f"Anmeldung abgelehnt: {antwort.erste_zeile}")
        raise SipFehler("Anmeldung abgelehnt: Benutzername oder Kennwort falsch?")

    def _auth_kopf(self, antwort: Nachricht, methode: str, uri: str) -> tuple[str, str]:
        if antwort.status == 407:
            return ("Proxy-Authorization", digest_antwort(
                methode, uri, self.benutzer, self.kennwort, antwort.get("proxy-authenticate")))
        return ("Authorization", digest_antwort(
            methode, uri, self.benutzer, self.kennwort, antwort.get("www-authenticate")))

    # ---------- Senden / Transaktionen ----------

    def _senden(self, nachricht: Nachricht, ziel: tuple[str, int] | None = None) -> None:
        if self._transport:
            self._transport.sendto(nachricht.bytes(), ziel or (self.server, self.server_port))

    def _via(self, zweig: str) -> tuple[str, str]:
        return ("Via", f"SIP/2.0/UDP {self.lokale_ip}:{self.lokaler_port};branch=z9hG4bK{zweig};rport")

    async def _anfrage(
        self,
        methode: str,
        uri: str,
        kopf: list[tuple[str, str]],
        rumpf: bytes = b"",
        zweig: str | None = None,
        vorlaeufig: Callable[[Nachricht], None] | None = None,
        gesamt_timeout: float = 32.0,
    ) -> Nachricht:
        """Sendet eine Anfrage (mit Wiederholungen über UDP) und wartet auf die endgültige Antwort."""
        zweig = zweig or _zufall(16)
        nachricht = Nachricht(
            f"{methode} {uri} SIP/2.0",
            [self._via(zweig), ("Max-Forwards", "70"), *kopf,
             ("User-Agent", "KI-Telefonassistent")]
            + ([("Content-Type", "application/sdp")] if rumpf else []),
            rumpf,
        )
        loop = asyncio.get_running_loop()
        fertig: asyncio.Future = loop.create_future()
        geantwortet = asyncio.Event()
        schluessel = f"z9hG4bK{zweig}|{methode}"
        self._offen[schluessel] = (fertig, vorlaeufig, geantwortet)
        try:
            ende = loop.time() + gesamt_timeout
            warte = T1
            while not geantwortet.is_set():
                self._senden(nachricht)
                rest = ende - loop.time()
                if rest <= 0:
                    raise SipFehler(f"Keine Antwort auf {methode}")
                try:
                    await asyncio.wait_for(geantwortet.wait(), min(warte, rest))
                except TimeoutError:
                    warte = min(warte * 2, 4.0)
            rest = max(0.1, ende - loop.time()) if methode != "INVITE" else None
            return await asyncio.wait_for(asyncio.shield(fertig), rest)
        except TimeoutError as fehler:
            raise SipFehler(f"Keine endgültige Antwort auf {methode}") from fehler
        finally:
            self._offen.pop(schluessel, None)

    # ---------- Empfang ----------

    def datagram_received(self, daten: bytes, adresse) -> None:
        if not daten.strip():
            return  # Keep-alive
        try:
            nachricht = Nachricht.parsen(daten)
        except Exception:
            return
        if nachricht.ist_antwort:
            self._antwort_erhalten(nachricht)
        else:
            asyncio.create_task(self._anfrage_erhalten(nachricht, adresse))

    def _antwort_erhalten(self, antwort: Nachricht) -> None:
        eintrag = self._offen.get(f"{antwort.zweig}|{antwort.methode}")
        if eintrag is None:
            # Wiederholtes 200 OK auf INVITE → ACK erneut senden
            gespraech = self._gespraeche.get(antwort.get("call-id"))
            if gespraech and antwort.methode == "INVITE" and 200 <= antwort.status < 300:
                self._ack(gespraech, antwort.cseq[0])
            return
        fertig, vorlaeufig, geantwortet = eintrag
        geantwortet.set()
        if antwort.status < 200:
            if vorlaeufig:
                vorlaeufig(antwort)
        elif not fertig.done():
            fertig.set_result(antwort)

    def _antwort_auf(self, anfrage: Nachricht, status: int, text: str, extra=(), rumpf=b"", to_tag="") -> Nachricht:
        to = anfrage.get("to")
        if to_tag and not _tag(to):
            to = f"{to};tag={to_tag}"
        kopf = [("Via", v) for v in anfrage.alle("via")]
        kopf += [("From", anfrage.get("from")), ("To", to), ("Call-ID", anfrage.get("call-id")),
                 ("CSeq", anfrage.get("cseq")), *extra]
        if rumpf:
            kopf.append(("Content-Type", "application/sdp"))
        return Nachricht(f"SIP/2.0 {status} {text}", kopf, rumpf)

    async def _anfrage_erhalten(self, anfrage: Nachricht, adresse) -> None:
        methode = anfrage.methode
        call_id = anfrage.get("call-id")
        gespraech = self._gespraeche.get(call_id)
        if methode == "BYE":
            self._senden(self._antwort_auf(anfrage, 200, "OK"), adresse)
            if gespraech:
                gespraech._ende("Gegenseite hat aufgelegt")
        elif methode == "CANCEL":
            self._senden(self._antwort_auf(anfrage, 200, "OK"), adresse)
            invite = self._eingehend_offen.pop(call_id, None)
            if invite:
                self._senden(self._antwort_auf(invite, 487, "Request Terminated", to_tag=_zufall(8)), adresse)
        elif methode == "ACK":
            pass
        elif methode == "INVITE" and gespraech:
            # Sitzungsauffrischung (re-INVITE): mit unserer Medienbeschreibung bestätigen
            sdp = sdp_bauen(self.lokale_ip, gespraech.rtp.port, [gespraech.rtp.nutzlast])
            self._senden(self._antwort_auf(anfrage, 200, "OK", [("Contact", self._kontakt)], sdp), adresse)
        elif methode == "INVITE":
            await self._eingehender_anruf(anfrage, adresse)
        elif methode in ("OPTIONS", "NOTIFY", "UPDATE", "INFO"):
            self._senden(self._antwort_auf(anfrage, 200, "OK", [("Allow", "INVITE, ACK, CANCEL, BYE, OPTIONS")]), adresse)
        else:
            self._senden(self._antwort_auf(anfrage, 405, "Method Not Allowed"), adresse)

    # ---------- Eingehende Anrufe ----------

    async def _eingehender_anruf(self, invite: Nachricht, adresse) -> None:
        call_id = invite.get("call-id")
        lokal_tag = _zufall(8)
        self._senden(self._antwort_auf(invite, 100, "Trying"), adresse)
        if self.bei_eingehendem_anruf is None:
            # Nicht annehmen: nur "klingeln", damit andere Telefone normal funktionieren.
            self._eingehend_offen[call_id] = invite
            self._senden(self._antwort_auf(invite, 180, "Ringing", to_tag=lokal_tag), adresse)
            return
        if self._gespraeche:
            self._senden(self._antwort_auf(invite, 486, "Busy Here", to_tag=lokal_tag), adresse)
            return
        try:
            fern_ip, fern_port, angebot = sdp_lesen(invite.rumpf)
        except SipFehler:
            self._senden(self._antwort_auf(invite, 488, "Not Acceptable Here", to_tag=lokal_tag), adresse)
            return
        nutzlast = next((n for n in (audio.PCMA, audio.PCMU) if n in angebot), None)
        if nutzlast is None:
            self._senden(self._antwort_auf(invite, 488, "Not Acceptable Here", to_tag=lokal_tag), adresse)
            return
        self._eingehend_offen[call_id] = invite
        self._senden(self._antwort_auf(invite, 180, "Ringing", to_tag=lokal_tag), adresse)
        await asyncio.sleep(1.5)  # kurz klingeln lassen
        if call_id not in self._eingehend_offen:
            return  # Anrufer hat aufgelegt
        del self._eingehend_offen[call_id]
        rtp = RtpStrom()
        port = await rtp.starten(self.lokale_ip)
        to_kopf = f"{invite.get('to')};tag={lokal_tag}" if not _tag(invite.get("to")) else invite.get("to")
        gespraech = Telefonat(
            telefon=self, call_id=call_id, lokal_tag=lokal_tag, lokal_kopf=to_kopf,
            fern_kopf=invite.get("from"), fern_ziel=_uri(invite.get("contact")) or _uri(invite.get("from")),
            rtp=rtp, richtung="rein", fern_nummer=nummer_aus(invite.get("from")),
        )
        self._gespraeche[call_id] = gespraech
        self._senden(self._antwort_auf(
            invite, 200, "OK", [("Contact", self._kontakt)], sdp_bauen(self.lokale_ip, port, [nutzlast]),
            to_tag=lokal_tag), adresse)
        rtp.verbinden(fern_ip, fern_port, nutzlast)
        await self.bei_eingehendem_anruf(gespraech)

    # ---------- Ausgehende Anrufe ----------

    async def anrufen(self, nummer: str, klingeldauer: float = 45) -> Telefonat:
        if not self.angemeldet:
            raise AnrufFehler(f"Nicht an der FRITZ!Box angemeldet ({self.letzter_fehler or 'noch nicht verbunden'}).")
        call_id, lokal_tag = _zufall(16), _zufall(8)
        uri = f"sip:{nummer}@{self.server}"
        rtp = RtpStrom()
        port = await rtp.starten(self.lokale_ip)
        sdp = sdp_bauen(self.lokale_ip, port, [audio.PCMA, audio.PCMU])
        from_kopf, to_kopf = f"{self._ich};tag={lokal_tag}", f"<{uri}>"
        cseq, autorisierung = 0, None
        try:
            for _ in range(3):
                cseq += 1
                zweig = _zufall(16)
                kopf = [("From", from_kopf), ("To", to_kopf), ("Call-ID", call_id),
                        ("CSeq", f"{cseq} INVITE"), ("Contact", self._kontakt),
                        ("Allow", "INVITE, ACK, CANCEL, BYE, OPTIONS")]
                if autorisierung:
                    kopf.append(autorisierung)
                aufgabe = asyncio.create_task(self._anfrage("INVITE", uri, kopf, sdp, zweig=zweig))
                try:
                    antwort = await asyncio.wait_for(asyncio.shield(aufgabe), klingeldauer)
                except TimeoutError:
                    await self._cancel(uri, zweig, from_kopf, to_kopf, call_id, cseq)
                    try:
                        antwort = await asyncio.wait_for(aufgabe, 5)
                        self._ack_fehler(uri, zweig, from_kopf, antwort, call_id, cseq)
                    except Exception:
                        aufgabe.cancel()
                    raise AnrufFehler("niemand hat abgenommen")
                if antwort.status in (401, 407):
                    self._ack_fehler(uri, zweig, from_kopf, antwort, call_id, cseq)
                    autorisierung = self._auth_kopf(antwort, "INVITE", uri)
                    continue
                if antwort.status >= 300:
                    self._ack_fehler(uri, zweig, from_kopf, antwort, call_id, cseq)
                    raise AnrufFehler(GRUENDE.get(antwort.status, antwort.erste_zeile.split(" ", 2)[-1]))
                fern_ip, fern_port, gewaehlt = sdp_lesen(antwort.rumpf)
                nutzlast = next((n for n in gewaehlt if n in (audio.PCMA, audio.PCMU)), audio.PCMA)
                gespraech = Telefonat(
                    telefon=self, call_id=call_id, lokal_tag=lokal_tag, lokal_kopf=from_kopf,
                    fern_kopf=antwort.get("to"), fern_ziel=_uri(antwort.get("contact")) or uri,
                    rtp=rtp, richtung="raus", fern_nummer=nummer, cseq=cseq,
                )
                self._gespraeche[call_id] = gespraech
                self._ack(gespraech, cseq)
                rtp.verbinden(fern_ip, fern_port, nutzlast)
                return gespraech
            raise AnrufFehler("FRITZ!Box hat den Anruf nicht erlaubt (Anmeldedaten?)")
        except BaseException:
            if call_id not in self._gespraeche:
                rtp.schliessen()
            raise

    def _ack(self, gespraech: Telefonat, cseq: int) -> None:
        self._senden(Nachricht(f"ACK {gespraech.fern_ziel} SIP/2.0", [
            self._via(_zufall(16)), ("Max-Forwards", "70"), ("From", gespraech.lokal_kopf),
            ("To", gespraech.fern_kopf), ("Call-ID", gespraech.call_id), ("CSeq", f"{cseq} ACK"),
        ]))

    def _ack_fehler(self, uri, zweig, from_kopf, antwort: Nachricht, call_id, cseq) -> None:
        self._senden(Nachricht(f"ACK {uri} SIP/2.0", [
            self._via(zweig), ("Max-Forwards", "70"), ("From", from_kopf), ("To", antwort.get("to")),
            ("Call-ID", call_id), ("CSeq", f"{cseq} ACK"),
        ]))

    async def _cancel(self, uri, zweig, from_kopf, to_kopf, call_id, cseq) -> None:
        kopf = [("From", from_kopf), ("To", to_kopf), ("Call-ID", call_id), ("CSeq", f"{cseq} CANCEL")]
        try:
            # CANCEL nutzt denselben Zweig wie das abzubrechende INVITE
            await self._anfrage("CANCEL", uri, kopf, zweig=zweig, gesamt_timeout=5)
        except SipFehler:
            pass

    async def _bye(self, gespraech: Telefonat) -> None:
        autorisierung = None
        for _ in range(2):
            gespraech.cseq += 1
            kopf = [("From", gespraech.lokal_kopf), ("To", gespraech.fern_kopf),
                    ("Call-ID", gespraech.call_id), ("CSeq", f"{gespraech.cseq} BYE")]
            if autorisierung:
                kopf.append(autorisierung)
            try:
                antwort = await self._anfrage("BYE", gespraech.fern_ziel, kopf, gesamt_timeout=8)
            except SipFehler:
                return
            if antwort.status in (401, 407):
                autorisierung = self._auth_kopf(antwort, "BYE", gespraech.fern_ziel)
                continue
            return
