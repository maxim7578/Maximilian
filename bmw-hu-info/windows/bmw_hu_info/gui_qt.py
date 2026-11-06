"""Moderne Qt-Oberflaeche (PySide6) im Liquid-Glass-Stil (iOS 26).

Ersetzt die Tkinter-GUI fuer die Windows-.exe. Die gesamte Logik
(Katalog, SSH, Sicherheit, Verbindungstest, Auswertung) wird
unveraendert wiederverwendet; hier ist nur die Darstellung neu.
"""

from __future__ import annotations

import sys
import threading
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QIcon, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from .catalog import Befehl, lade_katalog
from .connectivity import teste_verbindung
from .fehler_analyse import analysiere
from .ssh_client import HeadunitClient, SSHVerbindungsError, Verbindungsdaten

HEADUNITS = ["NBT", "NBTEVO", "ENAVEVO", "MGU"]


def _asset(name: str) -> Path:
    """Pfad zu einer Asset-Datei (dev und gebuendelte .exe)."""
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS")) / "assets" / name
    return Path(__file__).resolve().parent.parent / "assets" / name


def _port(text: str) -> int:
    """Port sicher parsen; bei ungueltiger Eingabe Standard 22."""
    text = (text or "").strip()
    return int(text) if text.isdigit() and 0 < int(text) < 65536 else 22

QSS = """
#bg {
  background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
      stop:0 #3b6bff, stop:0.55 #6a4bd0, stop:1 #ff6fb3);
}
#glass {
  background: rgba(255,255,255,0.14);
  border: 1px solid rgba(255,255,255,0.35);
  border-radius: 24px;
}
#title { color: #ffffff; font-size: 22px; font-weight: 800; }
#sub   { color: rgba(255,255,255,0.75); font-size: 12px; }
QLabel { color: #f3f6ff; font-size: 13px; }
QLineEdit, QComboBox {
  background: rgba(255,255,255,0.16);
  border: 1px solid rgba(255,255,255,0.28);
  border-radius: 12px; padding: 9px 11px; color: #ffffff; font-size: 13px;
  selection-background-color: #0a84ff;
}
QLineEdit::placeholder { color: rgba(255,255,255,0.6); }
QComboBox QAbstractItemView {
  background: #26314f; color: #ffffff; selection-background-color: #0a84ff;
  border-radius: 8px;
}
QPushButton {
  background: rgba(255,255,255,0.9); color: #10204a;
  border: none; border-radius: 12px; padding: 10px 14px;
  font-size: 13px; font-weight: 700;
}
QPushButton:hover { background: #ffffff; }
QPushButton#ghost {
  background: rgba(255,255,255,0.16); color: #ffffff;
  border: 1px solid rgba(255,255,255,0.3);
}
QPushButton#ghost:hover { background: rgba(255,255,255,0.28); }
QListWidget {
  background: rgba(255,255,255,0.10); border: 1px solid rgba(255,255,255,0.2);
  border-radius: 14px; color: #f3f6ff; font-size: 13px; padding: 6px;
  outline: none;
}
QListWidget::item { padding: 8px 10px; border-radius: 9px; }
QListWidget::item:selected { background: rgba(255,255,255,0.28); color: #fff; }
QTextEdit {
  background: rgba(10,15,32,0.5); border: 1px solid rgba(255,255,255,0.18);
  border-radius: 14px; color: #e7eeff; font-family: Consolas, monospace; font-size: 12px;
  padding: 8px;
}
#pill { border-radius: 13px; padding: 7px 14px; font-weight: 700; font-size: 12px; }
QScrollBar:vertical, QScrollBar:horizontal {
  background: transparent; width: 10px; height: 10px; margin: 2px;
}
QScrollBar::handle {
  background: rgba(255,255,255,0.35); border-radius: 5px; min-height: 24px; min-width: 24px;
}
QScrollBar::handle:hover { background: rgba(255,255,255,0.55); }
QScrollBar::add-line, QScrollBar::sub-line { height: 0; width: 0; }
QScrollBar::add-page, QScrollBar::sub-page { background: transparent; }
"""


class App(QWidget):
    """Hauptfenster im Liquid-Glass-Stil."""

    sig_append = Signal(str)
    sig_status = Signal(str, bool)
    sig_busy = Signal(bool)

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("bg")
        self.setWindowTitle("Vako-HU - Diagnose (nur Lesen)")
        icon = _asset("emblem.png")
        if icon.exists():
            self.setWindowIcon(QIcon(str(icon)))
        self.resize(1000, 680)
        self._katalog = lade_katalog()
        self._sichtbar: list[Befehl | None] = []
        self._laeuft = False

        self.sig_append.connect(self._append)
        self.sig_status.connect(self._status)
        self.sig_busy.connect(self._busy)

        self._baue_ui()
        self._fuelle_befehle()

    # -- Aufbau -----------------------------------------------------------
    def _baue_ui(self) -> None:
        aussen = QVBoxLayout(self)
        aussen.setContentsMargins(18, 18, 18, 18)

        glass = QFrame()
        glass.setObjectName("glass")
        aussen.addWidget(glass)
        root = QVBoxLayout(glass)
        root.setContentsMargins(22, 20, 22, 20)
        root.setSpacing(12)

        kopf = QHBoxLayout()
        kopf.setSpacing(12)
        emblem = _asset("emblem.png")
        if emblem.exists():
            logo = QLabel()
            logo.setPixmap(
                QPixmap(str(emblem)).scaled(
                    56, 56, Qt.KeepAspectRatio, Qt.SmoothTransformation
                )
            )
            kopf.addWidget(logo)
        texte = QVBoxLayout()
        texte.setSpacing(0)
        titel = QLabel("Vako-HU")
        titel.setObjectName("title")
        sub = QLabel("Diagnose - nur Lesen - BMW-Headunits")
        sub.setObjectName("sub")
        texte.addWidget(titel)
        texte.addWidget(sub)
        kopf.addLayout(texte)
        kopf.addStretch(1)
        root.addLayout(kopf)

        # Verbindungsfelder
        gitter = QGridLayout()
        gitter.setHorizontalSpacing(10)
        gitter.setVerticalSpacing(8)
        self.host = QLineEdit("169.254.199.99")
        self.port = QLineEdit("22")
        self.benutzer = QLineEdit("root")
        self.passwort = QLineEdit()
        self.passwort.setEchoMode(QLineEdit.Password)
        self.passwort.setPlaceholderText("Passwort")
        self.schluessel = QLineEdit()
        self.schluessel.setPlaceholderText("Privater Schluessel (Pfad, optional)")
        self.headunit = QComboBox()
        self.headunit.addItems(HEADUNITS)
        self.headunit.setCurrentText("ENAVEVO")
        self.headunit.currentTextChanged.connect(lambda _t: self._fuelle_befehle())

        gitter.addWidget(QLabel("IP"), 0, 0)
        gitter.addWidget(self.host, 0, 1)
        gitter.addWidget(QLabel("Port"), 0, 2)
        gitter.addWidget(self.port, 0, 3)
        gitter.addWidget(QLabel("Benutzer"), 0, 4)
        gitter.addWidget(self.benutzer, 0, 5)
        gitter.addWidget(QLabel("Passwort"), 1, 0)
        gitter.addWidget(self.passwort, 1, 1)
        gitter.addWidget(QLabel("Schluessel"), 1, 2)
        gitter.addWidget(self.schluessel, 1, 3, 1, 2)
        knopf_key = QPushButton("...")
        knopf_key.setObjectName("ghost")
        knopf_key.setFixedWidth(42)
        knopf_key.clicked.connect(self._waehle_schluessel)
        gitter.addWidget(knopf_key, 1, 5)
        gitter.addWidget(QLabel("Headunit"), 2, 0)
        gitter.addWidget(self.headunit, 2, 1)
        root.addLayout(gitter)

        # Status + Test
        statuszeile = QHBoxLayout()
        self.pill = QLabel("Nicht verbunden")
        self.pill.setObjectName("pill")
        self._setze_pill(False)
        test = QPushButton("Verbindung testen")
        test.clicked.connect(self._teste_verbindung)
        statuszeile.addWidget(self.pill)
        statuszeile.addStretch(1)
        statuszeile.addWidget(test)
        root.addLayout(statuszeile)

        # Aktionen
        aktionen = QHBoxLayout()
        for text, slot, ghost in [
            ("Alle lesen", self._alle_lesen, False),
            ("Fehlerspeicher auswerten", self._auswerten, True),
            ("Bericht speichern", self._speichern, True),
            ("Ausgabe leeren", lambda: self.ausgabe.clear(), True),
        ]:
            b = QPushButton(text)
            if ghost:
                b.setObjectName("ghost")
            b.clicked.connect(slot)
            aktionen.addWidget(b)
        aktionen.addStretch(1)
        root.addLayout(aktionen)

        # Liste + Ausgabe
        unten = QHBoxLayout()
        self.liste = QListWidget()
        self.liste.setFixedWidth(300)
        self.liste.itemDoubleClicked.connect(self._eintrag_lesen)
        self.ausgabe = QTextEdit()
        self.ausgabe.setReadOnly(True)
        unten.addWidget(self.liste)
        unten.addWidget(self.ausgabe, 1)
        root.addLayout(unten, 1)

    # -- Daten ------------------------------------------------------------
    def _fuelle_befehle(self) -> None:
        self.liste.clear()
        self._sichtbar = []
        katalog = self._katalog.fuer_headunit(self.headunit.currentText())
        for kategorie in katalog.kategorien:
            kopf = QListWidgetItem(f"-- {kategorie.titel} --")
            kopf.setFlags(Qt.NoItemFlags)
            kopf.setFont(QFont("", -1, QFont.Bold))
            self.liste.addItem(kopf)
            self._sichtbar.append(None)
            for befehl in kategorie.befehle:
                marke = "  [Platzhalter]" if befehl.hat_platzhalter else ""
                self.liste.addItem(QListWidgetItem(f"   {befehl.titel}{marke}"))
                self._sichtbar.append(befehl)

    def _verbindungsdaten(self) -> Verbindungsdaten:
        return Verbindungsdaten(
            host=self.host.text().strip(),
            port=_port(self.port.text()),
            benutzer=self.benutzer.text().strip() or "root",
            passwort=self.passwort.text() or None,
            schluesseldatei=self.schluessel.text().strip() or None,
        )

    # -- Slots (Hauptthread) ---------------------------------------------
    def _append(self, text: str) -> None:
        self.ausgabe.append(text)

    def _setze_pill(self, ok: bool) -> None:
        farbe = "rgba(48,209,88,0.3)" if ok else "rgba(255,69,58,0.25)"
        rand = "#5ef08a" if ok else "#ff8f88"
        self.pill.setStyleSheet(
            f"#pill{{background:{farbe};color:{rand};"
            f"border:1px solid {rand};border-radius:13px;padding:7px 14px;"
            "font-weight:700;font-size:12px;}"
        )

    def _status(self, text: str, ok: bool) -> None:
        self.pill.setText(("●  " if ok else "●  ") + text)
        self._setze_pill(ok)

    def _busy(self, busy: bool) -> None:
        self._laeuft = busy

    # -- Aktionen ---------------------------------------------------------
    def _waehle_schluessel(self) -> None:
        pfad, _ = QFileDialog.getOpenFileName(self, "Privaten Schluessel waehlen")
        if pfad:
            self.schluessel.setText(pfad)

    def _teste_verbindung(self) -> None:
        daten = self._verbindungsdaten()
        if not daten.host or self._laeuft:
            return
        self.sig_busy.emit(True)
        self._status("Verbinde ...", True)

        def arbeit() -> None:
            try:
                status = teste_verbindung(daten)
                self.sig_status.emit(status.meldung, status.verbunden)
            finally:
                self.sig_busy.emit(False)

        threading.Thread(target=arbeit, daemon=True).start()

    def _eintrag_lesen(self, item: QListWidgetItem) -> None:
        idx = self.liste.row(item)
        if 0 <= idx < len(self._sichtbar) and self._sichtbar[idx] is not None:
            self._starte([self._sichtbar[idx]])

    def _alle_lesen(self) -> None:
        self._starte([b for b in self._sichtbar if b is not None])

    def _starte(self, befehle: list[Befehl]) -> None:
        daten = self._verbindungsdaten()
        if not daten.host or self._laeuft:
            return
        self.sig_busy.emit(True)
        self._status("Verbinde ...", True)

        def arbeit() -> None:
            try:
                with HeadunitClient(daten) as client:
                    self.sig_status.emit(f"Verbunden mit {daten.host}", True)
                    self.sig_append.emit(f"\n>>> Verbunden mit {daten.host}\n")
                    for befehl in befehle:
                        if befehl.hat_platzhalter:
                            self.sig_append.emit(
                                f"# {befehl.titel}: uebersprungen (Platzhalter)"
                            )
                            continue
                        self.sig_append.emit(f"# {befehl.titel}  ($ {befehl.command})")
                        e = client.ausfuehren(befehl.command)
                        self.sig_append.emit(e.ausgabe.rstrip() or "(keine Ausgabe)")
                        if e.fehlerausgabe.strip():
                            self.sig_append.emit(f"[stderr] {e.fehlerausgabe.rstrip()}")
            except SSHVerbindungsError as fehler:
                self.sig_status.emit("Nicht verbunden", False)
                self.sig_append.emit(f"[FEHLER] {fehler}")
            except Exception as fehler:  # noqa: BLE001
                self.sig_status.emit("Nicht verbunden", False)
                self.sig_append.emit(f"[UNERWARTETER FEHLER] {fehler}")
            finally:
                self.sig_busy.emit(False)

        threading.Thread(target=arbeit, daemon=True).start()

    def _auswerten(self) -> None:
        daten = self._verbindungsdaten()
        if not daten.host or self._laeuft:
            return
        katalog = self._katalog.fuer_headunit(self.headunit.currentText())
        befehle = [
            b
            for k in katalog.kategorien
            if k.id == "fehlerspeicher"
            for b in k.befehle
            if not b.hat_platzhalter
        ]
        self.sig_busy.emit(True)
        self._status("Verbinde ...", True)

        def arbeit() -> None:
            try:
                with HeadunitClient(daten) as client:
                    self.sig_status.emit(f"Verbunden mit {daten.host}", True)
                    teile = [client.ausfuehren(b.command).ausgabe for b in befehle]
                self.sig_append.emit("\n" + analysiere("\n".join(teile)).als_text())
            except SSHVerbindungsError as fehler:
                self.sig_status.emit("Nicht verbunden", False)
                self.sig_append.emit(f"[FEHLER] {fehler}")
            finally:
                self.sig_busy.emit(False)

        threading.Thread(target=arbeit, daemon=True).start()

    def _speichern(self) -> None:
        inhalt = self.ausgabe.toPlainText().strip()
        if not inhalt:
            return
        pfad, _ = QFileDialog.getSaveFileName(
            self, "Bericht speichern", "vako-hu-bericht.txt", "Textdatei (*.txt)"
        )
        if not pfad:
            return
        try:
            with open(pfad, "w", encoding="utf-8") as datei:
                datei.write(inhalt + "\n")
            self.sig_append.emit(f"\nBericht gespeichert: {pfad}")
        except OSError as fehler:
            self.sig_append.emit(f"Speichern fehlgeschlagen: {fehler}")


def main() -> int:
    app = QApplication.instance() or QApplication([])
    app.setStyleSheet(QSS)
    fenster = App()
    fenster.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
