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


def _anzahl(name: str, standard: int) -> int:
    """Ganze Zahl ab 0 (0 = keine Grenze)."""
    wert = _optional(name) or str(standard)
    if not wert.isdigit():
        raise EinstellungsFehler(f"{name} muss eine ganze Zahl ab 0 sein (0 = keine Grenze).")
    return int(wert)


def _nutzer_ids(name: str) -> frozenset[int]:
    """Kommagetrennte Telegram-User-IDs, z. B. "123456789, 987654321"."""
    teile = [teil.strip() for teil in _optional(name).split(",") if teil.strip()]
    if not all(teil.isdigit() for teil in teile):
        raise EinstellungsFehler(f"{name}: bitte nur Telegram-User-IDs (Zahlen) mit Komma getrennt eintragen.")
    return frozenset(int(teil) for teil in teile)


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
    # Wenn gesetzt, dürfen nur diese Telegram-Nutzer den Bot steuern (Pflicht bei Gruppen-Chats).
    telegram_erlaubte_nutzer: frozenset[int] = frozenset()
    # Mengenlimit für eingehende KI-Gespräche (0 = keine Grenze)
    eingehend_pro_nummer_tag: int = 3
    eingehend_pro_stunde: int = 10

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
            telegram_erlaubte_nutzer=_nutzer_ids("TELEGRAM_ERLAUBTE_NUTZER"),
            eingehend_pro_nummer_tag=_anzahl("EINGEHEND_MAX_PRO_NUMMER_TAG", 3),
            eingehend_pro_stunde=_anzahl("EINGEHEND_MAX_PRO_STUNDE", 10),
        )
