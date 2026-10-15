"""Startet den Telefonassistenten: Telegram-Bot + Gesprächsserver für Asterisk."""

import asyncio
import sys

import uvicorn
from fastapi import FastAPI, WebSocket
from loguru import logger

from .anrufe import Anrufverwaltung
from .ari import Ari
from .einstellungen import Einstellungen, EinstellungsFehler
from .ki import KI
from .telegram_bot import TelegramBot


def app_bauen(anrufe: Anrufverwaltung, eingehend_erlaubt: bool) -> FastAPI:
    app = FastAPI()

    @app.websocket("/ws/raus")
    async def raus(websocket: WebSocket):
        await websocket.accept(subprotocol="media")
        await anrufe.ausgehend_verbunden(websocket)

    @app.websocket("/ws/rein")
    async def rein(websocket: WebSocket):
        if not eingehend_erlaubt:
            await websocket.close()
            return
        await websocket.accept(subprotocol="media")
        await anrufe.eingehend_verbunden(websocket)

    return app


async def main() -> None:
    try:
        einst = Einstellungen.laden()
    except EinstellungsFehler as fehler:
        logger.error(str(fehler))
        sys.exit(1)

    ki = KI(einst.groq_api_key, einst.llm_modell, einst.stt_modell, einst.inhaber, einst.wohnort)
    bot = TelegramBot(einst, ki)
    ari = Ari(einst.ari_url, einst.ari_benutzer, einst.ari_kennwort)
    anrufe = Anrufverwaltung(einst, ari, ki, bot.melden)
    bot.anrufe = anrufe

    server = uvicorn.Server(
        uvicorn.Config(
            app_bauen(anrufe, einst.eingehende_anrufe),
            host="127.0.0.1",
            port=einst.app_port,
            log_level="warning",
        )
    )

    async with bot.app:
        await bot.app.start()
        await bot.app.updater.start_polling()
        logger.info("Telefonassistent läuft. Schick deinem Bot eine Nachricht in Telegram.")
        if einst.telegram_chat_id is None:
            logger.warning("TELEGRAM_CHAT_ID fehlt: Schick deinem Bot /start, um deine Chat-ID zu erfahren.")
        else:
            await bot.melden("✅ Dein Telefonassistent ist gestartet.")
        try:
            await server.serve()
        finally:
            await bot.app.updater.stop()
            await bot.app.stop()


if __name__ == "__main__":
    asyncio.run(main())
