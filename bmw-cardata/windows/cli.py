"""Startdatei der Kommandozeile für Windows (bmw-cardata.exe), gebaut mit PyInstaller."""

import sys

from bmw_cardata.cli import main

if __name__ == "__main__":
    # Umgeleitete Ausgaben (z. B. "> status.txt") in UTF-8 statt der alten Windows-Codepage,
    # damit Umlaute erhalten bleiben; im Konsolenfenster ändert das nichts.
    for stream in (sys.stdout, sys.stderr):
        if stream is not None and hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    main()
