"""Telegram-Bot: nimmt Sprach- und Textnachrichten entgegen und fragt vor jedem Anruf nach."""

from dataclasses import dataclass
from pathlib import Path

from loguru import logger
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from .auftrag import Anruf, jetzt
from .einstellungen import Einstellungen
from .ki import KI, Auftrag
from .telefonbuch import Kontakte, NummernFehler, openstreetmap_suchen, pruefen

HILFE = (
    "Schick mir eine Sprachnachricht oder Text, zum Beispiel:\n"
    "„Ruf beim Restaurant Da Mario in Köln an und reservier einen Tisch für zwei "
    "Personen heute um 17 Uhr.“\n\n"
    "Ich frage vor jedem Anruf nach, ob ich wirklich wählen soll.\n\n"
    "Befehle:\n"
    "/merken Name: Nummer – Nummer speichern, z. B. /merken Da Mario: 0221 123456\n"
    "/auflegen – laufenden Anruf beenden\n"
    "/status – prüfen, ob alles läuft\n"
    "/stimmen – Stimmen anhören und auswählen\n"
    "/abbrechen – offene Rückfrage verwerfen"
)


@dataclass
class Offen:
    """Was der Bot gerade von dir wissen will."""

    text: str = ""  # bisheriger Auftragstext (bei Rückfragen)
    auftrag: Auftrag | None = None  # verstandener Auftrag, wartet auf Nummer
    anruf: Anruf | None = None  # wartet auf Bestätigung


class TelegramBot:
    def __init__(self, einst: Einstellungen, ki: KI):
        self.einst = einst
        self.ki = ki
        self.kontakte = Kontakte(Path(einst.daten_ordner) / "kontakte.json")
        self.offen = Offen()
        self.anrufe = None  # Anrufverwaltung der PC- oder Handy-Version
        self.app = Application.builder().token(einst.telegram_token).build()
        self.app.add_handler(CommandHandler("start", self._start))
        self.app.add_handler(CommandHandler("hilfe", self._start))
        self.app.add_handler(CommandHandler("merken", self._merken))
        self.app.add_handler(CommandHandler("auflegen", self._auflegen))
        self.app.add_handler(CommandHandler("status", self._status))
        self.app.add_handler(CommandHandler("abbrechen", self._abbrechen))
        self.app.add_handler(CommandHandler(["stimmen", "stimme"], self._stimmen))
        self.app.add_handler(CallbackQueryHandler(self._knopf))
        self.app.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, self._sprachnachricht))
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self._textnachricht))

    async def melden(self, text: str) -> None:
        if self.einst.telegram_chat_id is None:
            logger.warning(f"Keine TELEGRAM_CHAT_ID – Nachricht nicht gesendet: {text}")
            return
        await self.app.bot.send_message(self.einst.telegram_chat_id, text)

    def _erlaubt(self, update: Update) -> bool:
        chat = update.effective_chat
        return chat is not None and chat.id == self.einst.telegram_chat_id

    async def _start(self, update: Update, _: ContextTypes.DEFAULT_TYPE):
        if self.einst.telegram_chat_id is None:
            await update.effective_message.reply_text(
                f"Hallo! Deine Chat-ID ist: {update.effective_chat.id}\n\n"
                "Trag sie in der Datei .env bei TELEGRAM_CHAT_ID ein und starte den Assistenten neu. "
                "Danach höre ich nur noch auf dich."
            )
            return
        if not self._erlaubt(update):
            return
        await update.effective_message.reply_text("Hallo! Ich bin dein Telefonassistent.\n\n" + HILFE)

    async def _status(self, update: Update, _):
        if not self._erlaubt(update):
            return
        await update.effective_message.reply_text(
            f"Telegram: ✅\n{await self.anrufe.status()}\n"
            f"Gerade ein Anruf aktiv: {'ja' if self.anrufe.beschaeftigt else 'nein'}\n"
            f"Eingehende Anrufe annehmen: {'an' if self.einst.eingehende_anrufe else 'aus'}"
        )

    async def _merken(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._erlaubt(update):
            return
        text = " ".join(context.args or [])
        if ":" not in text:
            await update.effective_message.reply_text("So geht's: /merken Da Mario: 0221 123456")
            return
        name, nummer = text.split(":", 1)
        try:
            n = self.kontakte.speichern(name, nummer)
        except NummernFehler as fehler:
            await update.effective_message.reply_text(str(fehler))
            return
        await update.effective_message.reply_text(f"Gespeichert: {name.strip()} → {n}")

    async def _auflegen(self, update: Update, _):
        if not self._erlaubt(update):
            return
        ok = await self.anrufe.auflegen()
        await update.effective_message.reply_text("Aufgelegt." if ok else "Es läuft gerade kein Anruf.")

    async def _abbrechen(self, update: Update, _):
        if not self._erlaubt(update):
            return
        self.offen = Offen()
        await update.effective_message.reply_text("Alles klar, verworfen.")

    async def _stimmen(self, update: Update, _):
        """Schickt von jeder Stimme eine Hörprobe in Telefonqualität, mit Knopf zum Auswählen."""
        if not self._erlaubt(update):
            return
        nachricht = update.effective_message
        if not hasattr(self.anrufe, "stimmprobe"):
            await nachricht.reply_text("Die Stimmauswahl gibt es nur in der Handy-Version.")
            return
        await nachricht.reply_text(
            f"{await self.anrufe.status()}\n\nHier sind die Stimmen zum Anhören – so klingen sie am Telefon. "
            "Tipp unter deiner Lieblingsstimme auf „Diese nehmen“."
        )
        for i, (kurzname, vorname, weiblich) in enumerate(self.anrufe.stimmen_liste()):
            knopf = InlineKeyboardMarkup([[InlineKeyboardButton(f"✅ {vorname} nehmen", callback_data=f"stimme:{i}")]])
            try:
                ogg = await self.anrufe.stimmprobe(kurzname)
            except Exception as fehler:
                logger.warning(f"Hörprobe {kurzname} fehlgeschlagen: {fehler!r}")
                await nachricht.reply_text(
                    f"❌ {vorname}: Microsoft-Stimme nicht erreichbar ({fehler.__class__.__name__}: {fehler})"[:500])
                continue
            await nachricht.reply_voice(ogg, caption=f"{vorname} ({'weiblich' if weiblich else 'männlich'})",
                                        reply_markup=knopf)

    async def _stimme_gewaehlt(self, abfrage, nummer: str) -> None:
        liste = self.anrufe.stimmen_liste()
        if not nummer.isdigit() or int(nummer) >= len(liste):
            return
        kurzname, vorname, _ = liste[int(nummer)]
        beschreibung = self.anrufe.stimme_waehlen(kurzname)
        await abfrage.message.reply_text(f"✅ Ab jetzt spricht {vorname}. ({beschreibung})")

    async def _sprachnachricht(self, update: Update, _):
        if not self._erlaubt(update):
            return
        nachricht = update.effective_message
        datei = await (nachricht.voice or nachricht.audio).get_file()
        audio = bytes(await datei.download_as_bytearray())
        try:
            text = await self.ki.transkribieren(audio)
        except Exception as fehler:
            logger.exception("Spracherkennung fehlgeschlagen")
            await nachricht.reply_text(f"Ich konnte die Sprachnachricht nicht verstehen ({fehler}).")
            return
        await nachricht.reply_text(f"🎙️ Verstanden: „{text}“")
        await self._verarbeiten(update, text)

    async def _textnachricht(self, update: Update, _):
        if not self._erlaubt(update):
            return
        await self._verarbeiten(update, update.effective_message.text)

    async def _verarbeiten(self, update: Update, text: str) -> None:
        antwort = update.effective_message.reply_text

        # Wartet der Bot gerade auf eine Telefonnummer?
        if self.offen.auftrag is not None:
            try:
                nummer = pruefen(text)
            except NummernFehler:
                await antwort("Das ist keine gültige Nummer. Schick mir die Nummer oder tippe /abbrechen.")
                return
            auftrag, self.offen = self.offen.auftrag, Offen()
            await self._bestaetigen_lassen(update, auftrag, nummer, "von dir")
            return

        # Antwort auf eine Rückfrage → mit dem ursprünglichen Auftrag zusammenführen.
        if self.offen.text:
            text = f"{self.offen.text}\nErgänzung: {text}"
        self.offen = Offen()

        try:
            auftrag = await self.ki.auftrag_verstehen(text, jetzt())
        except Exception as fehler:
            logger.exception("Auftrag nicht verstanden")
            await antwort(f"Die KI ist gerade nicht erreichbar ({fehler}). Versuch es gleich noch einmal.")
            return

        if auftrag.typ == "sonstiges":
            await antwort(auftrag.antwort)
            return
        if auftrag.typ == "rueckfrage":
            self.offen = Offen(text=text)
            await antwort(f"❓ {auftrag.rueckfrage}")
            return

        if auftrag.telefonnummer:
            try:
                await self._bestaetigen_lassen(update, auftrag, pruefen(auftrag.telefonnummer), "aus deiner Nachricht")
            except NummernFehler as fehler:
                await antwort(str(fehler))
            return

        kontakt = self.kontakte.suchen(auftrag.ziel)
        if kontakt:
            await self._bestaetigen_lassen(update, auftrag, kontakt.nummer, kontakt.quelle)
            return

        await antwort(f"🔎 Ich suche die Nummer von {auftrag.ziel} …")
        try:
            treffer = await openstreetmap_suchen(auftrag.ziel, auftrag.ort or self.einst.wohnort)
        except Exception as fehler:
            logger.warning(f"Suche fehlgeschlagen: {fehler}")
            treffer = []
        if treffer:
            t = treffer[0]
            quelle = f"{t.quelle}: {t.name}, {t.adresse}"
            await self._bestaetigen_lassen(update, auftrag, t.nummer, quelle)
            return

        self.offen = Offen(auftrag=auftrag)
        await antwort(
            f"Ich habe keine Nummer für {auftrag.ziel} gefunden. Schick mir bitte die Telefonnummer "
            "(z. B. von Google Maps), dann rufe ich an."
        )

    async def _bestaetigen_lassen(self, update: Update, auftrag: Auftrag, nummer: str, quelle: str) -> None:
        anruf = Anruf(ziel=auftrag.ziel or nummer, nummer=nummer, auftrag=auftrag.auftrag, spielraum=auftrag.spielraum)
        self.offen = Offen(anruf=anruf)
        knoepfe = InlineKeyboardMarkup(
            [[
                InlineKeyboardButton("📞 Anrufen", callback_data=f"anrufen:{anruf.id}"),
                InlineKeyboardButton("❌ Abbrechen", callback_data=f"abbrechen:{anruf.id}"),
            ]]
        )
        spielraum = f"\nSpielraum: {auftrag.spielraum}" if auftrag.spielraum else ""
        await update.effective_message.reply_text(
            f"Soll ich anrufen?\n\n👤 {anruf.ziel}\n📞 {nummer}\n(Nummer {quelle})\n\n"
            f"Auftrag: {anruf.auftrag}{spielraum}\n\n"
            "Falsche Nummer? Tippe Abbrechen und schick mir die richtige mit im Auftrag.",
            reply_markup=knoepfe,
        )

    async def _knopf(self, update: Update, _):
        abfrage = update.callback_query
        await abfrage.answer()
        if not self._erlaubt(update):
            return
        aktion, _, anruf_id = (abfrage.data or "").partition(":")
        if aktion == "stimme":
            await self._stimme_gewaehlt(abfrage, anruf_id)
            return
        anruf = self.offen.anruf
        if anruf is None or anruf.id != anruf_id:
            await abfrage.edit_message_reply_markup(None)
            await abfrage.message.reply_text("Dieser Auftrag ist nicht mehr aktuell.")
            return
        self.offen = Offen()
        await abfrage.edit_message_reply_markup(None)
        if aktion != "anrufen":
            await abfrage.message.reply_text("Abgebrochen, ich rufe nicht an.")
            return
        try:
            await self.anrufe.starten(anruf)
        except Exception as fehler:
            await abfrage.message.reply_text(f"❌ Anruf nicht möglich: {fehler}")
            return
        await abfrage.message.reply_text(f"📞 Ich rufe {anruf.ziel} an ({anruf.nummer}) …")
