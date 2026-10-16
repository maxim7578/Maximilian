"""Anrufe starten, verfolgen und Berichte verschicken."""

import asyncio
from collections.abc import Awaitable, Callable
from pathlib import Path

from fastapi import WebSocket
from loguru import logger

from . import texte
from .ari import Ari
from .auftrag import Anruf, jetzt
from .einstellungen import Einstellungen
from .gespraech import Gespraechsergebnis, gespraech_fuehren
from .ki import KI

Melden = Callable[[str], Awaitable[None]]


class Anrufverwaltung:
    """Es läuft immer höchstens ein ausgehender Anruf gleichzeitig."""

    def __init__(self, einst: Einstellungen, ari: Ari, ki: KI, melden: Melden):
        self.einst = einst
        self.ari = ari
        self.ki = ki
        self.melden = melden
        self.aktuell: Anruf | None = None
        self._piper_ordner = Path(einst.daten_ordner) / "piper"

    @property
    def beschaeftigt(self) -> bool:
        return self.aktuell is not None

    async def starten(self, anruf: Anruf) -> None:
        if self.aktuell:
            raise RuntimeError("Es läuft schon ein Anruf. Warte, bis er fertig ist, oder tippe /auflegen.")
        self.aktuell = anruf
        try:
            anruf.kanal_id = await self.ari.anrufen(anruf.nummer, anruf.id)
        except Exception:
            self.aktuell = None
            raise
        asyncio.create_task(self._ueberwachen(anruf))

    async def status(self) -> str:
        ok = await self.ari.erreichbar()
        return f"Telefonanlage (Asterisk): {'✅' if ok else '❌ nicht erreichbar'}"

    async def auflegen(self) -> bool:
        anruf = self.aktuell
        if not anruf or not anruf.kanal_id:
            return False
        await self.ari.auflegen(anruf.kanal_id)
        return True

    async def _ueberwachen(self, anruf: Anruf) -> None:
        """Meldet, wenn niemand abnimmt oder besetzt ist."""
        for _ in range(60):
            if anruf.verbunden.is_set():
                return
            await asyncio.sleep(1)
            try:
                aktiv = await self.ari.kanal_aktiv(anruf.kanal_id)
            except Exception as fehler:
                logger.warning(f"Kanalstatus nicht abfragbar: {fehler}")
                continue
            if not aktiv and not anruf.verbunden.is_set():
                break
        if not anruf.verbunden.is_set():
            if self.aktuell is anruf:
                self.aktuell = None
            await self.melden(
                f"📵 Bei {anruf.ziel} ({anruf.nummer}) hat niemand abgenommen, oder es war besetzt. "
                "Soll ich es später noch einmal versuchen? Schick mir einfach den Auftrag erneut."
            )

    def _gespraechs_optionen(self) -> dict:
        e = self.einst
        return dict(
            groq_api_key=e.groq_api_key,
            llm_modell=e.llm_modell,
            stt_modell=e.stt_modell,
            piper_stimme=e.piper_stimme,
            piper_ordner=self._piper_ordner,
            max_sekunden=e.max_gespraech_sekunden,
        )

    async def ausgehend_verbunden(self, websocket: WebSocket) -> None:
        anruf = self.aktuell
        if anruf is None:
            logger.warning("Ausgehende Verbindung ohne offenen Auftrag – wird getrennt.")
            await websocket.close()
            return
        anruf.verbunden.set()
        await self.melden(f"☎️ {anruf.ziel} hat abgenommen, ich spreche gerade …")
        try:
            ergebnis = await gespraech_fuehren(
                websocket,
                systemtext=texte.gespraech_raus(
                    self.einst.inhaber,
                    anruf.ziel,
                    anruf.auftrag,
                    anruf.spielraum,
                    self.einst.rueckrufnummer,
                    jetzt(),
                ),
                selbst_beginnen=False,
                **self._gespraechs_optionen(),
            )
        finally:
            self.aktuell = None
        details = (
            f"Angerufen: {anruf.ziel} ({anruf.nummer})\nAuftrag: {anruf.auftrag}\n"
            f"Ergebnis laut Assistent: {ergebnis.ergebnis or 'nicht festgehalten'}\n"
            f"Erledigt: {'ja' if ergebnis.erfolgreich else 'nein oder unklar'}"
        )
        await self._bericht_senden("raus", f"📋 Bericht – Anruf bei {anruf.ziel}", details, ergebnis)

    async def eingehend_verbunden(self, websocket: WebSocket) -> None:
        ergebnis = await gespraech_fuehren(
            websocket,
            systemtext=texte.gespraech_rein(self.einst.inhaber, jetzt()),
            selbst_beginnen=True,
            **self._gespraechs_optionen(),
        )
        details = (
            f"Anrufer-Nummer: {ergebnis.anrufer or 'unterdrückt'}\n"
            f"Notiz des Assistenten: {ergebnis.ergebnis or 'keine'}"
        )
        await self._bericht_senden(
            "rein", f"📥 Anruf von {ergebnis.anrufer or 'unbekannt'}", details, ergebnis
        )

    async def _bericht_senden(
        self, richtung: str, titel: str, details: str, ergebnis: Gespraechsergebnis
    ) -> None:
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
