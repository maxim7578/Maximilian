"""Fenster "Warnungen einstellen": Push-Thema und Grenzwerte."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from tkinter import ttk

from ..alert_store import load_settings, settings_path
from ..config import state_path

Start = Callable[..., bool]


class AlertDialog:
    """Zeigt die aktuellen Einstellungen und speichert Änderungen über 'warnungen einstellen'."""

    def __init__(self, parent: tk.Misc, state: str | None, start: Start) -> None:
        settings = load_settings(settings_path(state_path(state)))
        self.start = start
        self.window = tk.Toplevel(parent)
        self.window.title("Warnungen einstellen")
        self.window.transient(parent)
        self.topic = tk.StringVar(value=settings.ntfy_topic or "")
        self.soc = tk.StringVar(value=f"{settings.min_soc:g}")
        self.v12 = tk.StringVar(value=f"{settings.min_12v:g}")
        self.tire = tk.StringVar(value=f"{settings.tire_tolerance_bar:g}")
        self._build()

    def _row(self, frame: ttk.Frame, row: int, text: str, variable: tk.StringVar, width: int = 8) -> None:
        ttk.Label(frame, text=text).grid(row=row, column=0, sticky="w", pady=2)
        ttk.Entry(frame, textvariable=variable, width=width).grid(row=row, column=1, sticky="w", padx=4)

    def _build(self) -> None:
        frame = ttk.Frame(self.window, padding=10)
        frame.pack(fill="both", expand=True)
        self._row(frame, 0, "Push-Thema (ntfy):", self.topic, 36)
        ttk.Button(frame, text="Neues Thema erzeugen", command=lambda: self.topic.set("neu")).grid(row=0, column=2)
        self._row(frame, 1, "Warnen unter Ladestand (%):", self.soc)
        self._row(frame, 2, "Warnen unter 12-V-Ladestand (%):", self.v12)
        self._row(frame, 3, "Reifendruck unter Soll um (bar):", self.tire)
        ttk.Label(frame, text="Zum Abschalten der Pushes 'aus' eintragen. Leere Felder bleiben unverändert.").grid(
            row=4, column=0, columnspan=3, sticky="w", pady=(6, 0))
        buttons = ttk.Frame(frame)
        buttons.grid(row=5, column=0, columnspan=3, sticky="e", pady=(10, 0))
        self.save_button = ttk.Button(buttons, text="Speichern", command=self.save)
        self.save_button.pack(side="left", padx=3)
        ttk.Button(buttons, text="Test-Push (gespeichertes Thema)", command=self.test).pack(side="left", padx=3)
        ttk.Button(buttons, text="Schließen", command=self.window.destroy).pack(side="left", padx=3)

    def values(self) -> dict[str, str]:
        return {"ntfy_thema": self.topic.get(), "ladestand": self.soc.get(),
                "batterie_12v": self.v12.get(), "reifendruck_toleranz": self.tire.get()}

    def save(self) -> None:
        """Schließt nur, wenn gespeichert wird; sonst bleiben die Eingaben stehen."""
        if self.start("warnungen-einstellen", einstellungen=self.values()):
            self.window.destroy()

    def test(self) -> None:
        self.start("warnungen-test")
