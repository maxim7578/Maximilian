"""Startdatei der Windows-App (BMW-CarData.exe), gebaut mit PyInstaller.

Eine Fenster-App hat unter Windows keine Konsole: sys.stdout und sys.stderr sind None.
Damit Bibliotheken, die etwas ausgeben, nicht abstürzen, bekommen sie einen Ersatz, und
Fehler beim Start (auch beim Laden der Module) landen in %TEMP%\\bmw-cardata-start.log.
"""

import os
import sys
import tempfile
import traceback
from pathlib import Path

START_LOG = Path(tempfile.gettempdir()) / "bmw-cardata-start.log"


def _log(text: str) -> None:
    try:
        with START_LOG.open("a", encoding="utf-8") as handle:
            handle.write(text + "\n")
    except OSError:
        pass


def _ensure_streams() -> None:
    if sys.stdout is None or sys.stderr is None:
        sink = open(os.devnull, "w", encoding="utf-8")  # noqa: SIM115 - lebt so lange wie die App
        sys.stdout = sys.stdout or sink
        sys.stderr = sys.stderr or sink


if __name__ == "__main__":
    _ensure_streams()
    try:
        from bmw_cardata.gui.app import main

        main()
    except SystemExit as exit_:
        if exit_.code not in (0, None):
            _log(f"Beendet mit Code {exit_.code}: {sys.argv}")
        raise
    except BaseException:
        _log(f"Fehler beim Start: {sys.argv}\n{traceback.format_exc()}")
        raise
