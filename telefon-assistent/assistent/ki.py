"""Aufrufe an Groq (kostenloses Kontingent): Sprache erkennen, Auftrag verstehen, Bericht.

Nutzt direkt die HTTP-Schnittstelle (OpenAI-kompatibel), damit es auch auf Android/Termux
ohne zusätzliche Pakete läuft.
"""

import json
import re
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime

import httpx

from . import texte

GROQ_URL = "https://api.groq.com/openai/v1"
SATZENDE = re.compile(r"[.!?…](?=\s)|[.!?…]$")


class KIFehler(Exception):
    pass


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


@dataclass
class Antwort:
    """Antwort der KI im Telefonat: gesprochener Text und ggf. ein Funktionsaufruf."""

    text: str
    werkzeug: str = ""
    argumente: dict | None = None
    werkzeug_id: str = ""
    roh: dict | None = None  # Assistenten-Nachricht für den Verlauf


class KI:
    def __init__(
        self,
        api_key: str,
        llm_modell: str,
        stt_modell: str,
        inhaber: str,
        wohnort: str,
        basis_url: str = GROQ_URL,
    ):
        self._client = httpx.AsyncClient(
            base_url=basis_url,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=httpx.Timeout(30, connect=10),
        )
        self._llm_modell = llm_modell
        self._stt_modell = stt_modell
        self._inhaber = inhaber
        self._wohnort = wohnort

    async def _post(self, pfad: str, **kwargs) -> dict:
        for versuch in range(3):
            try:
                antwort = await self._client.post(pfad, **kwargs)
            except httpx.HTTPError as fehler:
                if versuch == 2:
                    raise KIFehler(f"Groq nicht erreichbar: {fehler}") from fehler
                continue
            if antwort.status_code in (429, 500, 502, 503) and versuch < 2:
                continue
            if antwort.status_code >= 400:
                raise KIFehler(f"Groq-Fehler {antwort.status_code}: {antwort.text[:300]}")
            return antwort.json()
        raise KIFehler("Groq antwortet nicht.")

    async def transkribieren(self, audio: bytes, dateiname: str = "nachricht.ogg") -> str:
        daten = await self._post(
            "/audio/transcriptions",
            files={"file": (dateiname, audio)},
            data={"model": self._stt_modell, "language": "de", "response_format": "json"},
        )
        return str(daten.get("text", "")).strip()

    async def _chat(self, nachrichten: list[dict], **extra) -> dict:
        nutzlast = {"model": self._llm_modell, "messages": nachrichten, **extra}
        if self._llm_modell.startswith("openai/gpt-oss"):
            nutzlast.setdefault("reasoning_effort", "low")
        daten = await self._post("/chat/completions", json=nutzlast)
        return daten["choices"][0]["message"]

    async def auftrag_verstehen(self, text: str, jetzt: datetime) -> Auftrag:
        nachricht = await self._chat(
            [
                {"role": "system", "content": texte.befehl_verstehen(self._inhaber, self._wohnort, jetzt)},
                {"role": "user", "content": text},
            ],
            response_format={"type": "json_object"},
        )
        return Auftrag.aus_json(nachricht.get("content") or "")

    async def bericht_schreiben(self, richtung: str, details: str, protokoll: str) -> str:
        nachricht = await self._chat(
            [
                {"role": "system", "content": texte.bericht(self._inhaber, richtung)},
                {"role": "user", "content": f"{details}\n\nGesprächsprotokoll:\n{protokoll or '(leer)'}"},
            ]
        )
        return (nachricht.get("content") or "").strip()

    async def gespraech_antwort(self, nachrichten: list[dict], werkzeuge: list[dict]) -> Antwort:
        """Nächste Antwort im Telefonat (Handy-Version)."""
        nachricht = await self._chat(nachrichten, tools=werkzeuge, tool_choice="auto", max_tokens=400)
        roh = {"role": "assistant", "content": nachricht.get("content") or ""}
        antwort = Antwort(text=(nachricht.get("content") or "").strip(), roh=roh)
        aufrufe = nachricht.get("tool_calls") or []
        if aufrufe:
            aufruf = aufrufe[0]
            roh["tool_calls"] = [aufruf]
            antwort.werkzeug = aufruf.get("function", {}).get("name", "")
            antwort.werkzeug_id = aufruf.get("id", "")
            try:
                antwort.argumente = json.loads(aufruf.get("function", {}).get("arguments") or "{}")
            except json.JSONDecodeError:
                antwort.argumente = {}
        return antwort

    async def gespraech_antwort_strom(
        self, nachrichten: list[dict], werkzeuge: list[dict], bei_satz: Callable[[str], Awaitable[None]],
    ) -> Antwort:
        """Wie gespraech_antwort, aber gestreamt: jeder fertige Satz geht sofort an bei_satz,
        damit er schon gesprochen wird, während die KI noch weiterschreibt."""
        nutzlast = {"model": self._llm_modell, "messages": nachrichten, "tools": werkzeuge,
                    "tool_choice": "auto", "max_tokens": 400, "stream": True}
        if self._llm_modell.startswith("openai/gpt-oss"):
            nutzlast["reasoning_effort"] = "low"
        text, offen = "", ""
        aufrufe: dict[int, dict] = {}
        async with self._client.stream("POST", "/chat/completions", json=nutzlast) as antwort:
            if antwort.status_code >= 400:
                inhalt = (await antwort.aread()).decode(errors="replace")
                raise KIFehler(f"Groq-Fehler {antwort.status_code}: {inhalt[:300]}")
            async for zeile in antwort.aiter_lines():
                if not zeile.startswith("data:"):
                    continue
                daten = zeile[5:].strip()
                if daten == "[DONE]":
                    break
                try:
                    stueck = json.loads(daten)
                except json.JSONDecodeError:
                    continue
                if "error" in stueck:
                    raise KIFehler(f"Groq-Fehler: {str(stueck['error'])[:300]}")
                delta = (stueck.get("choices") or [{}])[0].get("delta") or {}
                for teil in delta.get("tool_calls") or []:
                    eintrag = aufrufe.setdefault(teil.get("index", 0), {
                        "id": "", "type": "function", "function": {"name": "", "arguments": ""}})
                    eintrag["id"] = teil.get("id") or eintrag["id"]
                    funktion = teil.get("function") or {}
                    eintrag["function"]["name"] += funktion.get("name") or ""
                    eintrag["function"]["arguments"] += funktion.get("arguments") or ""
                neu = delta.get("content") or ""
                if not neu:
                    continue
                text += neu
                offen += neu
                while (treffer := SATZENDE.search(offen)) is not None:
                    satz, offen = offen[:treffer.end()].strip(), offen[treffer.end():]
                    if satz:
                        await bei_satz(satz)
        if offen.strip():
            await bei_satz(offen.strip())
        roh = {"role": "assistant", "content": text}
        ergebnis = Antwort(text=text.strip(), roh=roh)
        if aufrufe:
            aufruf = aufrufe[min(aufrufe)]
            roh["tool_calls"] = [aufruf]
            ergebnis.werkzeug = aufruf["function"]["name"]
            ergebnis.werkzeug_id = aufruf["id"]
            try:
                ergebnis.argumente = json.loads(aufruf["function"]["arguments"] or "{}")
            except json.JSONDecodeError:
                ergebnis.argumente = {}
        return ergebnis
