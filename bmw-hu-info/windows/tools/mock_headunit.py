"""Startet eine simulierte BMW-Headunit zum Testen (ohne Fahrzeug).

Aufruf:
    python tools/mock_headunit.py --port 2222 --passwort test

Danach die Windows-Software oder Android-App auf diesen Host/Port zeigen
lassen (Benutzer beliebig, Passwort wie hier gesetzt oder leer lassen,
wenn kein --passwort angegeben wurde).
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

# Paketverzeichnis (windows/) in den Suchpfad aufnehmen, damit das Skript
# auch direkt (nicht nur als Modul) startbar ist.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from bmw_hu_info.mock_server import MockHeadunit  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Simulierte BMW-Headunit (SSH).")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=2222)
    parser.add_argument(
        "--passwort",
        default=None,
        help="Erwartetes Passwort. Ohne Angabe wird jede Anmeldung akzeptiert.",
    )
    args = parser.parse_args(argv)

    server = MockHeadunit(host=args.host, port=args.port, passwort=args.passwort)
    server.start()
    pw = args.passwort if args.passwort else "(beliebig)"
    print(
        f"Simulierte Headunit laeuft auf {args.host}:{server.port}\n"
        f"  Benutzer: beliebig   Passwort: {pw}\n"
        "In der Windows-Software/App diese Daten eintragen und 'Alle lesen'.\n"
        "Beenden mit Strg+C."
    )
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nBeende Simulation ...")
    finally:
        server.stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
