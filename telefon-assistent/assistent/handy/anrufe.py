"""Anrufe für die Handy-Version: wählen über die FRITZ!Box, Gespräch führen, Bericht schicken."""

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

import aiohttp
from loguru import logger

from .. import texte
from ..auftrag import Anruf, jetzt
from ..einstellungen import Einstellungen
from .gemini import GEMINI_URL, GeminiFehler, GeminiGespraech
from .gespraech import Gespraech, Gespraechsergebnis
from .sip import AnrufFehler, Telefon, Telefonat

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
        if self.telefon.angemeldet:
            return f"FRITZ!Box-Anmeldung: ✅ ({self.telefon.lokale_ip})\n{art}"
        return f"FRITZ!Box-Anmeldung: ❌ {self.telefon.letzter_fehler or 'noch nicht verbunden'}\n{art}"

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
                         gemini: GeminiGespraech | None) -> Gespraechsergebnis:
        if gemini is not None:
            gemini.leitung = telefonat
            gemini.ergebnis.anrufer = getattr(telefonat, "fern_nummer", "")
            return await gemini.fuehren(self._sitzung)
        return await Gespraech(
            telefonat, self.ki, self.stimme, systemtext,
            selbst_beginnen=selbst_beginnen, max_sekunden=self.einst.max_gespraech_sekunden,
        ).fuehren()

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
        systemtext = texte.gespraech_raus(self.einst.inhaber, anruf.ziel, anruf.auftrag, anruf.spielraum,
                                          self.einst.rueckrufnummer, jetzt())
        gemini = None
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
            ergebnis = await self._gespraech(self._telefonat, systemtext, False, gemini)
            gemini = None
            details = (
                f"Angerufen: {anruf.ziel} ({anruf.nummer})\nAuftrag: {anruf.auftrag}\n"
                f"Ergebnis laut Assistent: {ergebnis.ergebnis or 'nicht festgehalten'}\n"
                f"Erledigt: {'ja' if ergebnis.erfolgreich else 'nein oder unklar'}"
            )
            await self._bericht_senden("raus", f"📋 Bericht – Anruf bei {anruf.ziel}", details, ergebnis)
        finally:
            if gemini is not None and gemini._ws is not None:
                await gemini._ws.close()  # Anruf kam nicht zustande
            self.aktuell = None
            self._telefonat = None

    async def _eingehend(self, telefonat: Telefonat) -> None:
        if self.beschaeftigt:
            await telefonat.auflegen()
            return
        self._telefonat = telefonat
        systemtext = texte.gespraech_rein(self.einst.inhaber, jetzt())
        try:
            gemini = await self._gemini_vorbereiten(telefonat, systemtext, selbst_beginnen=True)
            ergebnis = await self._gespraech(telefonat, systemtext, True, gemini)
        finally:
            self._telefonat = None
        details = (
            f"Anrufer-Nummer: {ergebnis.anrufer or 'unterdrückt'}\n"
            f"Notiz des Assistenten: {ergebnis.ergebnis or 'keine'}"
        )
        await self._bericht_senden("rein", f"📥 Anruf von {ergebnis.anrufer or 'unbekannt'}", details, ergebnis)

    async def _bericht_senden(self, richtung: str, titel: str, details: str, ergebnis: Gespraechsergebnis) -> None:
        protokoll = ergebnis.protokoll_text()
        try:
            bericht = await self.ki.bericht_schreiben(richtung, details, protokoll)
        except Exception as fehler:
            logger.warning(f"Bericht konnte nicht erstellt werden: {fehler}")
            bericht = details
        text = f"{titel}\n\n{bericht}"
        if protokoll:
            text += f"\n\n— Protokoll —\n{protokoll}"
        await self.melden(text[:4000])
