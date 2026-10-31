"""Tkinter-Oberflaeche fuer die Windows-Software.

Tkinter ist Teil der Standard-Python-Installation unter Windows, es wird
also keine zusaetzliche GUI-Bibliothek benoetigt. Netzwerkaufrufe laufen
in einem Hintergrund-Thread, damit die Oberflaeche nicht einfriert.
"""

from __future__ import annotations

import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from .catalog import Befehl, lade_katalog
from .ssh_client import HeadunitClient, SSHVerbindungsError, Verbindungsdaten

HEADUNITS = ["NBT", "NBTEVO", "ENAVEVO", "MGU"]


class App(ttk.Frame):
    """Hauptfenster der Diagnose-Software."""

    def __init__(self, master: tk.Tk) -> None:
        super().__init__(master, padding=8)
        self.master.title("BMW HU Info - Diagnose (nur Lesen)")
        self.master.geometry("900x640")
        self._katalog = lade_katalog()
        self._baue_verbindungsleiste()
        self._baue_hauptbereich()
        self.grid(sticky="nsew")
        master.columnconfigure(0, weight=1)
        master.rowconfigure(0, weight=1)
        self._fuelle_befehle()

    # -- Aufbau -----------------------------------------------------------
    def _baue_verbindungsleiste(self) -> None:
        rahmen = ttk.LabelFrame(self, text="Verbindung", padding=6)
        rahmen.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 8))

        self.host = tk.StringVar(value="169.254.199.99")
        self.port = tk.StringVar(value="22")
        self.benutzer = tk.StringVar(value="root")
        self.passwort = tk.StringVar()
        self.schluessel = tk.StringVar()
        self.headunit = tk.StringVar(value=HEADUNITS[1])

        ttk.Label(rahmen, text="IP").grid(row=0, column=0, sticky="w")
        ttk.Entry(rahmen, textvariable=self.host, width=18).grid(row=0, column=1)
        ttk.Label(rahmen, text="Port").grid(row=0, column=2, sticky="w")
        ttk.Entry(rahmen, textvariable=self.port, width=6).grid(row=0, column=3)
        ttk.Label(rahmen, text="Benutzer").grid(row=0, column=4, sticky="w")
        ttk.Entry(rahmen, textvariable=self.benutzer, width=10).grid(row=0, column=5)

        ttk.Label(rahmen, text="Passwort").grid(row=1, column=0, sticky="w")
        ttk.Entry(rahmen, textvariable=self.passwort, show="*", width=18).grid(
            row=1, column=1
        )
        ttk.Label(rahmen, text="Schluessel").grid(row=1, column=2, sticky="w")
        ttk.Entry(rahmen, textvariable=self.schluessel, width=24).grid(
            row=1, column=3, columnspan=2, sticky="ew"
        )
        ttk.Button(rahmen, text="...", width=3, command=self._waehle_schluessel).grid(
            row=1, column=5, sticky="w"
        )

        ttk.Label(rahmen, text="Headunit").grid(row=2, column=0, sticky="w")
        auswahl = ttk.Combobox(
            rahmen, textvariable=self.headunit, values=HEADUNITS, width=10,
            state="readonly",
        )
        auswahl.grid(row=2, column=1, sticky="w")
        auswahl.bind("<<ComboboxSelected>>", lambda _e: self._fuelle_befehle())

    def _baue_hauptbereich(self) -> None:
        self.liste = tk.Listbox(self, width=36, exportselection=False)
        self.liste.grid(row=1, column=0, sticky="nsw", padx=(0, 8))
        self.liste.bind("<Double-Button-1>", lambda _e: self._fuehre_aus())

        rechts = ttk.Frame(self)
        rechts.grid(row=1, column=1, sticky="nsew")
        self.ausgabe = tk.Text(rechts, wrap="none", height=28)
        self.ausgabe.grid(row=0, column=0, sticky="nsew")
        rollbalken = ttk.Scrollbar(rechts, command=self.ausgabe.yview)
        rollbalken.grid(row=0, column=1, sticky="ns")
        self.ausgabe.configure(yscrollcommand=rollbalken.set)

        knopfleiste = ttk.Frame(self)
        knopfleiste.grid(row=2, column=0, columnspan=2, sticky="ew", pady=6)
        ttk.Button(knopfleiste, text="Ausgewaehlten lesen", command=self._fuehre_aus).pack(
            side="left"
        )
        ttk.Button(knopfleiste, text="Alle lesen", command=self._fuehre_alle_aus).pack(
            side="left", padx=6
        )
        ttk.Button(knopfleiste, text="Ausgabe leeren", command=self._leeren).pack(
            side="left"
        )

        self.columnconfigure(1, weight=1)
        self.rowconfigure(1, weight=1)
        rechts.columnconfigure(0, weight=1)
        rechts.rowconfigure(0, weight=1)

    # -- Daten ------------------------------------------------------------
    def _fuelle_befehle(self) -> None:
        self.liste.delete(0, tk.END)
        self._sichtbar: list[Befehl] = []
        katalog = self._katalog.fuer_headunit(self.headunit.get())
        for kategorie in katalog.kategorien:
            self.liste.insert(tk.END, f"-- {kategorie.titel} --")
            self._sichtbar.append(None)  # type: ignore[arg-type]
            for befehl in kategorie.befehle:
                markierung = " [Platzhalter]" if befehl.hat_platzhalter else ""
                self.liste.insert(tk.END, f"   {befehl.titel}{markierung}")
                self._sichtbar.append(befehl)

    def _verbindungsdaten(self) -> Verbindungsdaten:
        return Verbindungsdaten(
            host=self.host.get().strip(),
            port=int(self.port.get() or 22),
            benutzer=self.benutzer.get().strip() or "root",
            passwort=self.passwort.get() or None,
            schluesseldatei=self.schluessel.get().strip() or None,
        )

    # -- Aktionen ---------------------------------------------------------
    def _waehle_schluessel(self) -> None:
        pfad = filedialog.askopenfilename(title="Privaten Schluessel waehlen")
        if pfad:
            self.schluessel.set(pfad)

    def _leeren(self) -> None:
        self.ausgabe.delete("1.0", tk.END)

    def _schreibe(self, text: str) -> None:
        self.ausgabe.insert(tk.END, text + "\n")
        self.ausgabe.see(tk.END)

    def _fuehre_aus(self) -> None:
        auswahl = self.liste.curselection()
        if not auswahl:
            return
        befehl = self._sichtbar[auswahl[0]]
        if befehl is None:
            return
        self._starte([befehl])

    def _fuehre_alle_aus(self) -> None:
        befehle = [b for b in self._sichtbar if b is not None]
        self._starte(befehle)

    def _starte(self, befehle: list[Befehl]) -> None:
        daten = self._verbindungsdaten()
        if not daten.host:
            messagebox.showwarning("Hinweis", "Bitte eine IP eingeben.")
            return
        threading.Thread(
            target=self._arbeit, args=(daten, befehle), daemon=True
        ).start()

    def _arbeit(self, daten: Verbindungsdaten, befehle: list[Befehl]) -> None:
        try:
            with HeadunitClient(daten) as client:
                self._schreibe(f"\n>>> Verbunden mit {daten.host}\n")
                for befehl in befehle:
                    if befehl.hat_platzhalter:
                        self._schreibe(
                            f"# {befehl.titel}: uebersprungen (Platzhalter "
                            f"'{befehl.command}' zuerst im Katalog ersetzen)"
                        )
                        continue
                    self._schreibe(f"# {befehl.titel}  ($ {befehl.command})")
                    ergebnis = client.ausfuehren(befehl.command)
                    self._schreibe(ergebnis.ausgabe.rstrip() or "(keine Ausgabe)")
                    if ergebnis.fehlerausgabe.strip():
                        self._schreibe(f"[stderr] {ergebnis.fehlerausgabe.rstrip()}")
        except SSHVerbindungsError as fehler:
            self._schreibe(f"[FEHLER] {fehler}")
        except Exception as fehler:  # noqa: BLE001 - GUI soll nie abstuerzen
            self._schreibe(f"[UNERWARTETER FEHLER] {fehler}")


def main() -> int:
    wurzel = tk.Tk()
    App(wurzel)
    wurzel.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
