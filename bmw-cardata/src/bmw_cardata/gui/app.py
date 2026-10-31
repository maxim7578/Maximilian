"""Das Fenster der Windows-App: alle Befehle von bmw-cardata per Knopfdruck."""

from __future__ import annotations

import queue
import re
import sys
import time
import tkinter as tk
import traceback
import webbrowser
from collections.abc import Callable
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from tkinter.scrolledtext import ScrolledText

from .. import __version__
from .alert_dialog import AlertDialog
from .runner import Event, Job, Runner, _cli_run, build_args, drain, export_csv, start_command

POLL_MS = 100
CRASH_LOG = Path.home() / ".config" / "bmw-cardata" / "app-fehler.log"
_LINK = re.compile(r"https://[^\s)\"']+")


class App:
    """Baut das Fenster und reicht Knopfdrücke als Befehle an den Runner weiter."""

    def __init__(self, root: tk.Tk, *, state: str | None = None, run: Runner = _cli_run,
                 open_link: Callable[[str], object] = webbrowser.open) -> None:
        self.root, self.state, self.run, self.open_link = root, state, run, open_link
        self.events: queue.Queue[Event] = queue.Queue()
        self.job: Job | None = None
        self.client_id = tk.StringVar()
        self.nur_api = tk.BooleanVar(value=False)
        self.vin = tk.StringVar()
        self.live_speichern = tk.BooleanVar(value=False)
        self.live_warnungen = tk.BooleanVar(value=True)
        self.anzahl = tk.IntVar(value=10)
        self.status = tk.StringVar(value="Bereit.")
        self.buttons: list[ttk.Button] = []
        root.title(f"BMW CarData {__version__}")
        root.minsize(760, 560)
        self._build()
        root.after(POLL_MS, self._poll)

    # ---- Aufbau -------------------------------------------------------------------------

    def _button(self, parent: tk.Misc, text: str, command: Callable[[], None], column: int) -> ttk.Button:
        button = ttk.Button(parent, text=text, command=command)
        button.grid(row=0, column=column, padx=3, pady=3, sticky="ew")
        self.buttons.append(button)
        return button

    def _build(self) -> None:
        frame = ttk.Frame(self.root, padding=8)
        frame.pack(fill="both", expand=True)
        self._build_login(frame)
        self._build_queries(frame)
        self._build_live_and_history(frame)
        self._build_output(frame)
        ttk.Label(frame, textvariable=self.status, anchor="w").pack(fill="x", pady=(4, 0))

    def _build_login(self, frame: ttk.Frame) -> None:
        box = ttk.LabelFrame(frame, text="Anmeldung", padding=6)
        box.pack(fill="x")
        ttk.Label(box, text="Client-ID:").grid(row=0, column=0, sticky="w")
        ttk.Entry(box, textvariable=self.client_id, width=40).grid(row=0, column=1, padx=4, sticky="ew")
        ttk.Checkbutton(box, text="Ohne Live-Daten (nur API)", variable=self.nur_api).grid(row=0, column=2, padx=4)
        row = ttk.Frame(box)
        row.grid(row=0, column=3, sticky="e")
        self._button(row, "Anmelden", lambda: self._start("anmelden"), 0)
        self._button(row, "Abmelden", lambda: self._start("abmelden"), 1)
        box.columnconfigure(1, weight=1)

    def _build_queries(self, frame: ttk.Frame) -> None:
        box = ttk.LabelFrame(frame, text="Fahrzeug abfragen (je 1 von 50 Abrufen pro Tag)", padding=6)
        box.pack(fill="x", pady=(6, 0))
        top = ttk.Frame(box)
        top.pack(fill="x")
        ttk.Label(top, text="Fahrgestellnummer (optional):").pack(side="left")
        ttk.Entry(top, textvariable=self.vin, width=22).pack(side="left", padx=4)
        row = ttk.Frame(box)
        row.pack(fill="x", pady=(4, 0))
        for column, (text, command) in enumerate((
            ("Fahrzeuge", lambda: self._start("fahrzeuge")),
            ("Status", lambda: self._start("status")),
            ("Status speichern", lambda: self._start("status", speichern=True)),
            ("Basisdaten", lambda: self._start("basisdaten")),
            ("Kontingent", lambda: self._start("kontingent")),
            ("Warnungen prüfen", lambda: self._start("warnungen-pruefen")),
            ("Warnungen einstellen …", self.open_alert_settings),
        )):
            self._button(row, text, command, column)

    def _build_live_and_history(self, frame: ttk.Frame) -> None:
        row = ttk.Frame(frame)
        row.pack(fill="x", pady=(6, 0))
        live = ttk.LabelFrame(row, text="Live-Daten (ohne Tageslimit)", padding=6)
        live.pack(side="left", fill="x", expand=True)
        self._button(live, "Live starten", lambda: self._start(
            "live", speichern=self.live_speichern.get(), warnungen=self.live_warnungen.get()), 0)
        self.stop_button = ttk.Button(live, text="Live stoppen", command=self.stop, state="disabled")
        self.stop_button.grid(row=0, column=1, padx=3, pady=3)
        ttk.Checkbutton(live, text="Speichern", variable=self.live_speichern).grid(row=0, column=2, padx=4)
        ttk.Checkbutton(live, text="Warnungen melden", variable=self.live_warnungen).grid(row=0, column=3, padx=4)
        history = ttk.LabelFrame(row, text="Verlauf (ohne Abruf)", padding=6)
        history.pack(side="left", fill="x", expand=True, padx=(6, 0))
        ttk.Spinbox(history, from_=1, to=1000, textvariable=self.anzahl, width=5).grid(row=0, column=0, padx=3)
        self._button(history, "Anzeigen", lambda: self._start("verlauf", anzahl=self._count()), 1)
        self._button(history, "Als CSV speichern …", self.save_csv, 2)

    def _build_output(self, frame: ttk.Frame) -> None:
        self.output = ScrolledText(frame, height=18, wrap="word", font=("Consolas", 10), state="disabled")
        self.output.pack(fill="both", expand=True, pady=(6, 0))
        self.output.tag_configure("err", foreground="#a33")
        self.output.tag_configure("warn", foreground="#b35900", font=("Consolas", 10, "bold"))
        self.output.tag_configure("link", foreground="#0645ad", underline=True)
        self.output.tag_bind("link", "<Button-1>", self._click_link)
        self.output.tag_bind("link", "<Enter>", lambda _e: self.output.configure(cursor="hand2"))
        self.output.tag_bind("link", "<Leave>", lambda _e: self.output.configure(cursor=""))
        clear = ttk.Button(frame, text="Ausgabe leeren", command=self.clear)
        clear.pack(anchor="e", pady=(4, 0))

    # ---- Abläufe ------------------------------------------------------------------------

    def _count(self) -> int:
        try:
            return min(max(int(self.anzahl.get()), 1), 1000)
        except (tk.TclError, ValueError):
            return 10

    def open_alert_settings(self) -> None:
        AlertDialog(self.root, self.state, self._start)

    def _start(self, command: str, *, speichern: bool = False, warnungen: bool = False,
               anzahl: int | None = None, einstellungen: dict[str, str] | None = None) -> bool:
        """Startet einen Befehl; False, wenn das nicht ging (läuft schon einer, Eingabe ungültig)."""
        if self.job and self.job.running:
            self.append("Bitte warten, bis der laufende Befehl fertig ist (Live zuerst stoppen).\n", "err")
            return False
        try:
            args = build_args(command, vin=self.vin.get(), client_id=self.client_id.get(),
                              nur_api=self.nur_api.get(), speichern=speichern, warnungen=warnungen,
                              anzahl=anzahl, einstellungen=einstellungen)
        except ValueError as error:
            self.append(f"{error}\n", "err")
            return False
        self.append(f"\n> bmw-cardata {' '.join(args[:2] if args[:2] == ['warnungen', 'einstellen'] else args)}\n")
        self.status.set(f"Läuft: {command} …")
        self._set_busy(True, live=command == "live")
        self.job = start_command(args, self.events, state=self.state, run=self.run)
        return True

    def stop(self) -> None:
        if self.job:
            self.job.stop()
            self.status.set("Live wird beendet …")

    def save_csv(self) -> None:
        target = filedialog.asksaveasfilename(
            parent=self.root, title="Verlauf als CSV speichern", defaultextension=".csv",
            initialfile="bmw-verlauf.csv", filetypes=[("CSV-Dateien", "*.csv"), ("Alle Dateien", "*.*")])
        if target:
            self.write_csv(Path(target))

    def write_csv(self, target: Path) -> None:
        try:
            code, errors = export_csv(target, state=self.state, run=self.run)
        except OSError as error:
            code, errors = 1, f"Datei konnte nicht geschrieben werden: {error.strerror or error}\n"
        if code == 0:
            self.append(f"Verlauf gespeichert: {target}\n")
        else:
            self.append(errors or "CSV-Export fehlgeschlagen.\n", "err")

    def _set_busy(self, busy: bool, *, live: bool = False) -> None:
        for button in self.buttons:
            button.configure(state="disabled" if busy else "normal")
        self.stop_button.configure(state="normal" if busy and live else "disabled")

    def _poll(self) -> None:
        for kind, payload in drain(self.events):
            if kind == "done":
                self._set_busy(False)
                self.status.set("Fertig." if payload == 0 else f"Beendet mit Fehler (Code {payload}).")
            else:
                self.append(str(payload), "err" if kind == "err" else None)
        self.root.after(POLL_MS, self._poll)

    # ---- Ausgabe ------------------------------------------------------------------------

    def append(self, text: str, tag: str | None = None) -> None:
        """Hängt Text an: Links werden anklickbar, Warnungen hervorgehoben (mit Signalton)."""
        self.output.configure(state="normal")
        warned = False
        for line in text.splitlines(keepends=True):
            is_warning = line.lstrip().startswith("Warnung:")
            warned = warned or is_warning
            self._insert_line(line, "warn" if is_warning else tag)
        self.output.configure(state="disabled")
        self.output.see("end")
        if warned:
            self.root.bell()

    def _insert_line(self, line: str, tag: str | None) -> None:
        position = 0
        for match in _LINK.finditer(line):
            self.output.insert("end", line[position:match.start()], tag or ())
            self.output.insert("end", match.group(0), ("link",))
            position = match.end()
        self.output.insert("end", line[position:], tag or ())

    def text(self) -> str:
        return self.output.get("1.0", "end-1c")

    def clear(self) -> None:
        self.output.configure(state="normal")
        self.output.delete("1.0", "end")
        self.output.configure(state="disabled")

    def _click_link(self, event: tk.Event) -> None:
        index = self.output.index(f"@{event.x},{event.y}")
        for start, end in zip(*[iter(self.output.tag_ranges("link"))] * 2):
            if self.output.compare(start, "<=", index) and self.output.compare(index, "<", end):
                self.open_link(self.output.get(start, end))
                return


def _self_test(report: Path, seconds: float = 2.0) -> int:
    """Öffnet das Fenster kurz und schreibt "OK" oder die Fehlermeldung in report.

    Für Prüfungen ohne Bildschirmausgabe, z. B. im Windows-Bau: Eine Fenster-App hat
    unter Windows keine Konsole, in der ein Fehler sichtbar würde.
    """
    try:
        root = tk.Tk()
        App(root)
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            root.update()
            time.sleep(0.05)
        root.destroy()
    except Exception:  # noqa: BLE001 - jeder Fehler gehört in den Bericht
        report.write_text(traceback.format_exc(), encoding="utf-8")
        return 1
    report.write_text("OK\n", encoding="utf-8")
    return 0


def _report_crash(details: str, log: Path) -> None:
    """Schreibt einen Absturz in eine Datei und nennt sie in einem Hinweisfenster."""
    try:
        log.parent.mkdir(parents=True, exist_ok=True)
        log.write_text(details, encoding="utf-8")
    except OSError:
        pass
    try:
        messagebox.showerror("BMW CarData", f"Die App ist auf einen Fehler gestoßen.\n\nDetails stehen in:\n{log}")
    except tk.TclError:
        pass


def main(argv: list[str] | None = None) -> None:
    args = sys.argv[1:] if argv is None else argv
    if args[:1] == ["--selbsttest"]:
        sys.exit(_self_test(Path(args[1] if len(args) > 1 else "selbsttest.txt")))
    try:
        root = tk.Tk()
        App(root)
        root.mainloop()
    except Exception:  # noqa: BLE001 - ohne Konsole wäre der Fehler sonst unsichtbar
        _report_crash(traceback.format_exc(), CRASH_LOG)
        sys.exit(1)
