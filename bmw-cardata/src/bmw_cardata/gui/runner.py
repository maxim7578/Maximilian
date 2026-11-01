"""Führt Befehle der Kommandozeile für die Windows-App im Hintergrund aus.

Die App nutzt genau dieselben, getesteten Befehle wie die Kommandozeile
(bmw_cardata.cli.run); Ausgaben laufen als Ereignisse über eine Queue zur Oberfläche.
"""

from __future__ import annotations

import io
import queue
import threading
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import TextIO

Event = tuple[str, object]  # ("out" | "err", Text) oder ("done", Rückgabewert)
Runner = Callable[[list[str], TextIO, TextIO, Callable[[], bool]], int]


def _cli_run(argv: list[str], out: TextIO, err: TextIO, stop: Callable[[], bool]) -> int:
    from ..cli import run

    return run(argv, out=out, err=err, stop=stop)


class QueueWriter(io.TextIOBase):
    """Ein Textstrom, der jeden Schreibvorgang als Ereignis in die Queue legt."""

    def __init__(self, events: queue.Queue[Event], kind: str) -> None:
        super().__init__()
        self.events, self.kind = events, kind

    def writable(self) -> bool:
        return True

    def write(self, text: str) -> int:
        if text:
            self.events.put((self.kind, text))
        return len(text)


@dataclass
class Job:
    thread: threading.Thread
    stop_event: threading.Event = field(default_factory=threading.Event)

    def stop(self) -> None:
        self.stop_event.set()

    @property
    def running(self) -> bool:
        return self.thread.is_alive()


def _with_state(args: list[str], state: str | None) -> list[str]:
    return ["--state", state, *args] if state else list(args)


def start_command(
    args: list[str], events: queue.Queue[Event], *, state: str | None = None, run: Runner = _cli_run
) -> Job:
    """Startet einen Befehl in einem Hintergrund-Thread; das Ende kommt als ("done", Code)."""
    stop_event = threading.Event()

    def work() -> None:
        out, err = QueueWriter(events, "out"), QueueWriter(events, "err")
        try:
            code = run(_with_state(args, state), out, err, stop_event.is_set)
        except SystemExit as exit_:  # argparse bei falschen Eingaben
            code = exit_.code if isinstance(exit_.code, int) else 1
        except Exception as error:  # noqa: BLE001 - die App soll nie wegen eines Befehls abstürzen
            events.put(("err", f"Unerwarteter Fehler: {type(error).__name__}: {error}\n"))
            code = 1
        events.put(("done", code))

    thread = threading.Thread(target=work, name=f"bmw-cardata {args[:1]}", daemon=True)
    job = Job(thread, stop_event)
    thread.start()
    return job


def drain(events: queue.Queue[Event]) -> list[Event]:
    """Alle bisher eingegangenen Ereignisse, ohne zu warten."""
    found = []
    while True:
        try:
            found.append(events.get_nowait())
        except queue.Empty:
            return found


_ALERT_COMMANDS = {"warnungen-pruefen": ["warnungen", "pruefen"], "warnungen-test": ["warnungen", "test"],
                   "warnungen-einstellen": ["warnungen", "einstellen"]}
_SETTING_OPTIONS = (("ntfy_thema", "--ntfy-thema", False), ("ladestand", "--ladestand", True),
                    ("batterie_12v", "--batterie-12v", True), ("reifendruck_toleranz", "--reifendruck-toleranz", True))


def _setting_args(settings: dict[str, str]) -> list[str]:
    """Optionen für 'warnungen einstellen'; Zahlen dürfen ein deutsches Komma haben."""
    args: list[str] = []
    for key, option, numeric in _SETTING_OPTIONS:
        value = settings.get(key, "").strip()
        if not value:
            continue
        if numeric:
            try:
                value = str(float(value.replace(",", ".")))
            except ValueError as error:
                raise ValueError(f"Bitte eine Zahl eintragen statt {value!r}.") from error
        args += [option, value]
    return args


def build_args(
    command: str,
    *,
    vin: str = "",
    client_id: str = "",
    nur_api: bool = False,
    speichern: bool = False,
    warnungen: bool = False,
    anzahl: int | None = None,
    einstellungen: dict[str, str] | None = None,
) -> list[str]:
    """Die Argumente der Kommandozeile aus den Eingaben der App."""
    vin, client_id = vin.strip(), client_id.strip()
    if command == "basisdaten" and not vin:
        raise ValueError("Für Basisdaten bitte eine Fahrgestellnummer eintragen.")
    args = list(_ALERT_COMMANDS.get(command, [command]))
    if command in ("status", "live", "basisdaten", "warnungen-pruefen") and vin:
        args.append(vin)
    if command == "anmelden" and client_id:
        args += ["--client-id", client_id]
    if command == "anmelden" and nur_api:
        args.append("--nur-api")
    if command in ("status", "live") and speichern:
        args.append("--speichern")
    if command == "live" and warnungen:
        args.append("--warnungen")
    if command == "verlauf" and anzahl is not None:
        args += ["--anzahl", str(anzahl)]
    if command == "warnungen-einstellen":
        args += _setting_args(einstellungen or {})
    return args


def export_csv(target: Path, *, state: str | None = None, run: Runner = _cli_run) -> tuple[int, str]:
    """Schreibt den Verlauf als CSV (mit BOM, damit Excel die Umlaute richtig liest)."""
    out, err = io.StringIO(), io.StringIO()
    code = run(_with_state(["verlauf", "--csv"], state), out, err, lambda: False)
    if code == 0:
        target.write_text(out.getvalue(), encoding="utf-8-sig", newline="")
    return code, err.getvalue()
