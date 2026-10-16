"""Einstellungen aus Umgebungsvariablen (Datei .env)."""

import os
from dataclasses import dataclass


class EinstellungsFehler(Exception):
    pass


def _pflicht(name: str) -> str:
    wert = os.getenv(name, "").strip()
    if not wert or wert.startswith("HIER_"):
        raise EinstellungsFehler(f"Bitte {name} in der Datei .env eintragen.")
    return wert


def _optional(name: str, standard: str = "") -> str:
    return os.getenv(name, standard).strip()


@dataclass(frozen=True)
class Einstellungen:
    telegram_token: str
    telegram_chat_id: int | None
    groq_api_key: str
    inhaber: str
    wohnort: str
    rueckrufnummer: str
    eingehende_anrufe: bool
    llm_modell: str
    stt_modell: str
    piper_stimme: str
    max_gespraech_sekunden: int
    ari_url: str
    ari_benutzer: str
    ari_kennwort: str
    app_port: int
    daten_ordner: str

    @classmethod
    def laden(cls) -> "Einstellungen":
        chat_id = _optional("TELEGRAM_CHAT_ID")
        return cls(
            telegram_token=_pflicht("TELEGRAM_BOT_TOKEN"),
            telegram_chat_id=int(chat_id) if chat_id else None,
            groq_api_key=_pflicht("GROQ_API_KEY"),
            inhaber=_pflicht("INHABER_NAME"),
            wohnort=_optional("WOHNORT"),
            rueckrufnummer=_optional("RUECKRUFNUMMER"),
            eingehende_anrufe=_optional("EINGEHENDE_ANRUFE", "aus").lower() in ("an", "ja", "1"),
            llm_modell=_optional("LLM_MODELL", "openai/gpt-oss-120b"),
            stt_modell=_optional("STT_MODELL", "whisper-large-v3-turbo"),
            piper_stimme=_optional("PIPER_STIMME", "de_DE-thorsten-medium"),
            max_gespraech_sekunden=int(_optional("MAX_GESPRAECH_SEKUNDEN", "300")),
            ari_url=_optional("ARI_URL", "http://127.0.0.1:8088/ari"),
            ari_benutzer="assistent",
            ari_kennwort=_optional("ARI_KENNWORT"),  # nur PC-Version; dort prüft konfig.py
            app_port=int(_optional("APP_PORT", "8765")),
            daten_ordner=_optional("DATEN_ORDNER", "/daten"),
        )
