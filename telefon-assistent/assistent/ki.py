"""Aufrufe an Groq (kostenloses Kontingent): Sprache erkennen, Auftrag verstehen, Bericht."""

import json
from dataclasses import dataclass
from datetime import datetime

from groq import AsyncGroq

from . import texte


@dataclass
class Auftrag:
    typ: str
    ziel: str = ""
    ort: str = ""
    telefonnummer: str = ""
    auftrag: str = ""
    spielraum: str = ""
    rueckfrage: str = ""
    antwort: str = ""

    @classmethod
    def aus_json(cls, roh: str) -> "Auftrag":
        try:
            daten = json.loads(roh)
        except json.JSONDecodeError:
            return cls(typ="sonstiges", antwort="Das habe ich leider nicht verstanden.")
        if not isinstance(daten, dict):
            return cls(typ="sonstiges", antwort="Das habe ich leider nicht verstanden.")
        felder = {k: str(daten.get(k) or "").strip() for k in cls.__dataclass_fields__}
        if felder["typ"] not in ("anruf", "rueckfrage", "sonstiges"):
            felder["typ"] = "sonstiges"
        if felder["typ"] == "anruf" and not (felder["ziel"] or felder["telefonnummer"]):
            felder["typ"] = "rueckfrage"
            felder["rueckfrage"] = felder["rueckfrage"] or "Wen soll ich anrufen?"
        if felder["typ"] == "anruf" and not felder["auftrag"]:
            felder["typ"] = "rueckfrage"
            felder["rueckfrage"] = felder["rueckfrage"] or "Was soll ich am Telefon erledigen?"
        if felder["typ"] == "sonstiges" and not felder["antwort"]:
            felder["antwort"] = "Ich kann im Moment nur Anrufe für dich erledigen."
        return cls(**felder)


class KI:
    def __init__(self, api_key: str, llm_modell: str, stt_modell: str, inhaber: str, wohnort: str):
        self._client = AsyncGroq(api_key=api_key)
        self._llm_modell = llm_modell
        self._stt_modell = stt_modell
        self._inhaber = inhaber
        self._wohnort = wohnort

    async def transkribieren(self, audio: bytes, dateiname: str = "nachricht.ogg") -> str:
        ergebnis = await self._client.audio.transcriptions.create(
            file=(dateiname, audio),
            model=self._stt_modell,
            language="de",
        )
        return ergebnis.text.strip()

    async def auftrag_verstehen(self, text: str, jetzt: datetime) -> Auftrag:
        antwort = await self._client.chat.completions.create(
            model=self._llm_modell,
            messages=[
                {"role": "system", "content": texte.befehl_verstehen(self._inhaber, self._wohnort, jetzt)},
                {"role": "user", "content": text},
            ],
            response_format={"type": "json_object"},
        )
        return Auftrag.aus_json(antwort.choices[0].message.content or "")

    async def bericht_schreiben(self, richtung: str, details: str, protokoll: str) -> str:
        antwort = await self._client.chat.completions.create(
            model=self._llm_modell,
            messages=[
                {"role": "system", "content": texte.bericht(self._inhaber, richtung)},
                {"role": "user", "content": f"{details}\n\nGesprächsprotokoll:\n{protokoll or '(leer)'}"},
            ],
        )
        return (antwort.choices[0].message.content or "").strip()
