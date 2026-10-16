"""Anrufe für die Handy-Version: wählen über die FRITZ!Box, Gespräch führen, Bericht schicken."""

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from pathlib import Path

import aiohttp
from loguru import logger

from .. import texte
from ..auftrag import Anruf, jetzt
from ..einstellungen import Einstellungen
from .gemini import GEMINI_URL, GeminiFehler, GeminiGespraech
from .gespraech import Gespraech, Gespraechsergebnis
from .sip import AnrufFehler, Telefon, Telefonat
from .stimme import MICROSOFT_STIMMEN, PROBESATZ, EdgeStimme, pcm_zu_ogg

Melden = Callable[[str], Awaitable[None]]


@dataclass
class GeminiEinstellungen:
    api_key: str
    modell: str = "gemini-3.8-live"
    stimme: str = "Kore"
    url: str = GEMINI_URL


class HandyAnrufverwaltung:
    """Es läuft immer höchstens ein Gespräch gleichzeitig."""

    def __init__(
        self, einst: Einstellungen, telefon: Telefon, ki, stimme, melden: Melden,
        gemini: GeminiEinstellungen | None = None,
    ):
        self.einst = einst
        self.gemini = gemini
        self._sitzung: aiohttp.ClientSession | None = None
        self.telefon = telefon
        self.ki = ki
        self.stimme = stimme
        self.melden = melden
        self.aktuell: Anruf | None = None
        self._telefonat: Telefonat | None = None
        if einst.eingehende_anrufe:
            telefon.bei_eingehendem_anruf = self._eingehend

    @property
    def beschaeftigt(self) -> bool:
        return self.aktuell is not None or self._telefonat is not None

    async def status(self) -> str:
        art = f"Gesprächs-KI: {'Gemini Live (' + self.gemini.modell + ')' if self.gemini else 'Groq + Stimme'}"
        if not self.gemini and hasattr(self.stimme, "beschreibung"):
            art += f"\n{self.stimme.beschreibung()}"
        if self.telefon.angemeldet:
            return f"FRITZ!Box-Anmeldung: ✅ ({self.telefon.lokale_ip})\n{art}"
        return f"FRITZ!Box-Anmeldung: ❌ {self.telefon.letzter_fehler or 'noch nicht verbunden'}\n{art}"

    # ---------- Stimme auswählen ----------

    @property
    def _stimm_datei(self) -> Path:
        return Path(self.einst.daten_ordner) / "stimme.txt"

    def _vorstellung(self) -> tuple[str, bool]:
        if self.gemini or not hasattr(self.stimme, "vorstellung"):
            return "", True
        return self.stimme.vorstellung()

    async def stimmprobe(self, kurzname: str) -> bytes:
        """Probesatz mit einer Microsoft-Stimme als Telegram-Sprachnachricht (Telefonqualität)."""
        aktuell = getattr(self.stimme, "microsoft", None)
        probe = EdgeStimme(kurzname, aktuell.tempo) if aktuell else EdgeStimme(kurzname)
        rolle = "eine KI-Assistentin" if probe.weiblich else "ein KI-Assistent"
        text = PROBESATZ.format(name=probe.vorname, rolle=rolle, inhaber=self.einst.inhaber)
        return await pcm_zu_ogg(await asyncio.wait_for(probe.sprechen(text), 20))

    def stimme_waehlen(self, kurzname: str) -> str:
        self.stimme.microsoft_waehlen(kurzname)
        self._stimm_datei.write_text(kurzname, encoding="utf-8")
        return self.stimme.beschreibung()

    @staticmethod
    def stimmen_liste() -> list[tuple[str, str, bool]]:
        return MICROSOFT_STIMMEN

    async def _gemini_vorbereiten(self, telefonat, systemtext: str, selbst_beginnen: bool) -> GeminiGespraech | None:
        """Verbindet mit Gemini Live; klappt das nicht, wird die klassische Variante genutzt."""
        if not self.gemini:
            return None
        if self._sitzung is None or self._sitzung.closed:
            self._sitzung = aiohttp.ClientSession(trust_env=True)
        gespraech = GeminiGespraech(
            telefonat, self.gemini.api_key, systemtext, selbst_beginnen, self.einst.max_gespraech_sekunden,
            modell=self.gemini.modell, stimme=self.gemini.stimme, url=self.gemini.url,
        )
        try:
            await gespraech.verbinden(self._sitzung)
            return gespraech
        except GeminiFehler as fehler:
            logger.warning(f"Gemini Live nicht verfügbar, nutze klassische Variante: {fehler}")
            await self.melden(f"ℹ️ Gemini Live ist gerade nicht verfügbar ({fehler}). Ich nutze diesmal die klassische Stimme.")
            return None

    async def _gespraech(self, telefonat, systemtext: str, selbst_beginnen: bool,
                         gemini: GeminiGespraech | None, begruessung: str = "",
                         gruss_ton: asyncio.Task | None = None) -> Gespraechsergebnis:
        if gemini is not None:
            gemini.leitung = telefonat
            gemini.ergebnis.anrufer = getattr(telefonat, "fern_nummer", "")
            return await gemini.fuehren(self._sitzung)
        return await Gespraech(
            telefonat, self.ki, self.stimme, systemtext,
            selbst_beginnen=selbst_beginnen, max_sekunden=self.einst.max_gespraech_sekunden,
            begruessung=begruessung, gruss_ton=gruss_ton,
        ).fuehren()

    def _gruss_vorbereiten(self, text: str) -> asyncio.Task | None:
        """Erzeugt den ersten Satz schon vorab (z. B. während es klingelt), damit er sofort kommt."""
        if self.gemini:
            return None
        aufgabe = asyncio.create_task(self.stimme.sprechen(text))
        aufgabe.add_done_callback(lambda a: a.cancelled() or a.exception())  # Fehler nicht "verlieren"
        return aufgabe

    async def starten(self, anruf: Anruf) -> None:
        if self.beschaeftigt:
            raise RuntimeError("Es läuft schon ein Anruf. Warte, bis er fertig ist, oder tippe /auflegen.")
        if not self.telefon.angemeldet:
            raise RuntimeError(await self.status())
        self.aktuell = anruf
        asyncio.create_task(self._ausgehend(anruf))

    async def auflegen(self) -> bool:
        if self._telefonat is None:
            return False
        await self._telefonat.auflegen()
        return True

    async def _ausgehend(self, anruf: Anruf) -> None:
        name, weiblich = self._vorstellung()
        begruessung = "" if self.gemini else texte.begruessung_raus(self.einst.inhaber, name, weiblich)
        systemtext = texte.gespraech_raus(self.einst.inhaber, anruf.ziel, anruf.auftrag, anruf.spielraum,
                                          self.einst.rueckrufnummer, jetzt(), name, weiblich, begruessung)
        gemini = None
        gruss_ton = self._gruss_vorbereiten(begruessung) if begruessung else None
        try:
            # Gemini schon vor dem Wählen verbinden, damit nach dem Abheben keine Zeit verloren geht
            gemini = await self._gemini_vorbereiten(None, systemtext, selbst_beginnen=False)
            try:
                self._telefonat = await self.telefon.anrufen(anruf.nummer)
            except AnrufFehler as fehler:
                await self.melden(
                    f"📵 {anruf.ziel} ({anruf.nummer}): {fehler}. "
                    "Soll ich es später noch einmal versuchen? Schick mir einfach den Auftrag erneut."
                )
                return
            except Exception as fehler:
                logger.exception("Anruf fehlgeschlagen")
                await self.melden(f"❌ Anruf bei {anruf.ziel} fehlgeschlagen: {fehler}")
                return
            anruf.verbunden.set()
            await self.melden(f"☎️ {anruf.ziel} hat abgenommen, ich spreche gerade …")
            ergebnis = await self._gespraech(self._telefonat, systemtext, False, gemini, begruessung, gruss_ton)
            gemini = None
            details = (
                f"Angerufen: {anruf.ziel} ({anruf.nummer})\nAuftrag: {anruf.auftrag}\n"
                f"Ergebnis laut Assistent: {ergebnis.ergebnis or 'nicht festgehalten'}\n"
                f"Erledigt: {'ja' if ergebnis.erfolgreich else 'nein oder unklar'}"
            )
            await self._bericht_senden("raus", f"📋 Bericht – Anruf bei {anruf.ziel}", details, ergebnis,
                                       self._ruckel_hinweis(self._telefonat))
        finally:
            if gruss_ton is not None and not gruss_ton.done():
                gruss_ton.cancel()
            if gemini is not None and gemini._ws is not None:
                await gemini._ws.close()  # Anruf kam nicht zustande
            self.aktuell = None
            self._telefonat = None

    async def _eingehend(self, telefonat: Telefonat) -> None:
        if self.beschaeftigt:
            await telefonat.auflegen()
            return
        self._telefonat = telefonat
        name, weiblich = self._vorstellung()
        begruessung = "" if self.gemini else texte.begruessung_rein(self.einst.inhaber, name, weiblich)
        systemtext = texte.gespraech_rein(self.einst.inhaber, jetzt(), name, weiblich, begruessung)
        try:
            gemini = await self._gemini_vorbereiten(telefonat, systemtext, selbst_beginnen=True)
            ergebnis = await self._gespraech(telefonat, systemtext, True, gemini, begruessung)
        finally:
            self._telefonat = None
        details = (
            f"Anrufer-Nummer: {ergebnis.anrufer or 'unterdrückt'}\n"
            f"Notiz des Assistenten: {ergebnis.ergebnis or 'keine'}"
        )
        await self._bericht_senden("rein", f"📥 Anruf von {ergebnis.anrufer or 'unbekannt'}", details, ergebnis,
                                   self._ruckel_hinweis(telefonat))

    @staticmethod
    def _ruckel_hinweis(telefonat) -> str:
        anzahl = getattr(getattr(telefonat, "rtp", None), "verspaetet", 0)
        if not anzahl:
            return ""
        return (f"\n\n⚠️ Der Ton hat während des Gesprächs {anzahl}× gestockt, weil das Samsung ausgebremst "
                "wurde. Das klingt am Telefon roboterhaft. Abhilfe: Entwickleroptionen → „Aktiv lassen“ "
                "und Termux beim Akku auf „Nicht eingeschränkt“.")

    async def _bericht_senden(self, richtung: str, titel: str, details: str, ergebnis: Gespraechsergebnis,
                              hinweis: str = "") -> None:
        protokoll = ergebnis.protokoll_text()
        try:
            bericht = await self.ki.bericht_schreiben(richtung, details, protokoll)
        except Exception as fehler:
            logger.warning(f"Bericht konnte nicht erstellt werden: {fehler}")
            bericht = details
        text = f"{titel}\n\n{bericht}"
        if protokoll:
            text += f"\n\n— Protokoll —\n{protokoll}"
        await self.melden(text[:4000 - len(hinweis)] + hinweis)
