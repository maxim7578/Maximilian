"""Startet den Telefonassistenten auf dem Android-Handy (Termux).

Aufruf: python -m assistent.handy   (liest die Datei .env im aktuellen Ordner)
"""

import asyncio
import os
import sys
from pathlib import Path

from loguru import logger

from ..einstellungen import Einstellungen, EinstellungsFehler
from ..ki import KI
from ..telegram_bot import TelegramBot
from .anrufe import GeminiEinstellungen, HandyAnrufverwaltung
from .gemini import GEMINI_URL
from .sip import Telefon
from .stimme import stimmen_laden


def env_laden(datei: Path) -> None:
    """Liest KEY=WERT-Zeilen aus .env (ohne vorhandene Umgebungsvariablen zu überschreiben)."""
    if not datei.exists():
        return
    for zeile in datei.read_text(encoding="utf-8").splitlines():
        zeile = zeile.strip()
        if not zeile or zeile.startswith("#") or "=" not in zeile:
            continue
        name, wert = zeile.split("=", 1)
        wert = wert.strip()
        if len(wert) >= 2 and wert[0] == wert[-1] and wert[0] in "\"'":
            wert = wert[1:-1]
        os.environ.setdefault(name.strip(), wert)


def _pflicht(name: str) -> str:
    wert = os.getenv(name, "").strip()
    if not wert or wert.startswith("HIER_"):
        raise EinstellungsFehler(f"Bitte {name} in der Datei .env eintragen.")
    return wert


async def main() -> None:
    env_laden(Path.cwd() / ".env")
    os.environ.setdefault("DATEN_ORDNER", str(Path.home() / "telefon-daten"))
    try:
        einst = Einstellungen.laden()
        fritzbox = (_pflicht("FRITZBOX_ADRESSE"), _pflicht("FRITZBOX_BENUTZER"), _pflicht("FRITZBOX_KENNWORT"))
    except EinstellungsFehler as fehler:
        logger.error(str(fehler))
        sys.exit(1)

    daten = Path(einst.daten_ordner)
    daten.mkdir(parents=True, exist_ok=True)
    piper = Path(os.getenv("PIPER_MODELL", str(daten / "piper" / f"{einst.piper_stimme}.onnx")))
    gewaehlt = daten / "stimme.txt"  # per Telegram (/stimme) ausgewählte Stimme
    microsoft = gewaehlt.read_text(encoding="utf-8").strip() if gewaehlt.exists() else ""
    stimme = stimmen_laden(
        os.getenv("STIMME", "microsoft").lower(),
        microsoft or os.getenv("MICROSOFT_STIMME", "de-DE-SeraphinaMultilingualNeural"), piper,
        os.getenv("MICROSOFT_TEMPO", "+8%"),  # Sprechtempo, z. B. "+15%" schneller, "-5%" langsamer
    )
    logger.info(f"Stimmen: {', '.join(s.name for s in stimme.stimmen)}")

    ki = KI(einst.groq_api_key, einst.llm_modell, einst.stt_modell, einst.inhaber, einst.wohnort,
            os.getenv("GROQ_URL", "https://api.groq.com/openai/v1"))
    bot = TelegramBot(einst, ki)
    adresse, _, port = fritzbox[0].partition(":")  # z. B. 192.168.178.1 oder 192.168.178.1:5060
    telefon = Telefon(adresse, fritzbox[1], fritzbox[2], server_port=int(port or 5060),
                      lokaler_port=int(os.getenv("SIP_PORT", "5062")))
    await telefon.starten()
    gemini = None
    if os.getenv("GESPRAECH", "klassisch").lower() == "gemini":
        try:
            gemini = GeminiEinstellungen(
                api_key=_pflicht("GEMINI_API_KEY"),
                modell=os.getenv("GEMINI_MODELL", "gemini-3.8-live"),
                stimme=os.getenv("GEMINI_STIMME", "Kore"),
                url=os.getenv("GEMINI_URL", GEMINI_URL),
            )
        except EinstellungsFehler as fehler:
            logger.error(str(fehler))
            sys.exit(1)
    bot.anrufe = HandyAnrufverwaltung(einst, telefon, ki, stimme, bot.melden, gemini)

    async with bot.app:
        await bot.app.start()
        await bot.app.updater.start_polling()
        for _ in range(50):
            if telefon.angemeldet:
                break
            await asyncio.sleep(0.2)
        if gemini is None:
            try:  # einmal ausprobieren, damit /status und die Startmeldung zeigen, ob Microsoft geht
                await stimme.sprechen("Test.")
            except Exception as fehler:
                logger.warning(f"Keine Stimme funktioniert: {fehler}")
        logger.info(f"Telefonassistent läuft. {await bot.anrufe.status()}")
        if einst.telegram_chat_id is None:
            logger.warning("TELEGRAM_CHAT_ID fehlt: Schick deinem Bot /start, um deine Chat-ID zu erfahren.")
        else:
            await bot.melden(f"✅ Dein Telefonassistent ist gestartet.\n{await bot.anrufe.status()}")
        try:
            await asyncio.Event().wait()
        finally:
            await telefon.stoppen()
            await bot.app.updater.stop()
            await bot.app.stop()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
