"""Kommandozeilen-Variante des Diagnose-Clients."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .catalog import Katalog, lade_katalog
from .connectivity import teste_verbindung
from .fehler_analyse import analysiere
from .ssh_client import HeadunitClient, SSHVerbindungsError, Verbindungsdaten


def _argumente(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="bmw-hu-info",
        description="Lesender SSH-Diagnose-Client fuer BMW-Headunits.",
    )
    parser.add_argument("--host", required=True, help="IP der Headunit")
    parser.add_argument("--port", type=int, default=22)
    parser.add_argument("--benutzer", default="root")
    parser.add_argument("--passwort", default=None)
    parser.add_argument("--schluessel", default=None, help="Pfad privater Schluessel")
    parser.add_argument(
        "--headunit",
        choices=["NBT", "NBTEVO", "ENAVEVO", "MGU"],
        default=None,
        help="Katalog auf diese Headunit filtern",
    )
    parser.add_argument(
        "--liste", action="store_true", help="Nur Befehle auflisten"
    )
    parser.add_argument(
        "--analyse",
        action="store_true",
        help="Fehlerspeicher auslesen und zusammenfassen",
    )
    parser.add_argument(
        "--export",
        default=None,
        metavar="DATEI",
        help="Ausgabe zusaetzlich als Textdatei speichern",
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Nur die Verbindung (ENET + SSH) pruefen",
    )
    return parser.parse_args(argv)


def _katalog_fuer(args: argparse.Namespace) -> Katalog:
    katalog = lade_katalog()
    if args.headunit:
        return katalog.fuer_headunit(args.headunit)
    return katalog


def _drucke_liste(katalog: Katalog) -> None:
    for kategorie in katalog.kategorien:
        print(f"\n== {kategorie.titel} ==")
        for befehl in kategorie.befehle:
            markierung = "  [Platzhalter]" if befehl.hat_platzhalter else ""
            print(f"  {befehl.id}: {befehl.titel}{markierung}")


def _fuehre_alle_aus(katalog: Katalog, client: HeadunitClient) -> str:
    zeilen: list[str] = []

    def ausgeben(text: str) -> None:
        print(text)
        zeilen.append(text)

    for kategorie in katalog.kategorien:
        ausgeben(f"\n===== {kategorie.titel} =====")
        for befehl in kategorie.befehle:
            if befehl.hat_platzhalter:
                ausgeben(f"\n# {befehl.titel}: uebersprungen (Platzhalter)")
                continue
            ausgeben(f"\n# {befehl.titel}  ($ {befehl.command})")
            ergebnis = client.ausfuehren(befehl.command)
            ausgeben(ergebnis.ausgabe.rstrip() or "(keine Ausgabe)")
            if ergebnis.fehlerausgabe.strip():
                ausgeben(f"[stderr] {ergebnis.fehlerausgabe.rstrip()}")
    return "\n".join(zeilen)


def _analysiere_fehlerspeicher(katalog: Katalog, client: HeadunitClient) -> str:
    gesammelt = []
    for kategorie in katalog.kategorien:
        if kategorie.id != "fehlerspeicher":
            continue
        for befehl in kategorie.befehle:
            if befehl.hat_platzhalter:
                continue
            gesammelt.append(client.ausfuehren(befehl.command).ausgabe)
    text = analysiere("\n".join(gesammelt)).als_text()
    print(text)
    return text


def main(argv: list[str] | None = None) -> int:
    args = _argumente(argv)
    katalog = _katalog_fuer(args)

    if args.liste:
        _drucke_liste(katalog)
        return 0

    daten = Verbindungsdaten(
        host=args.host,
        port=args.port,
        benutzer=args.benutzer,
        passwort=args.passwort,
        schluesseldatei=args.schluessel,
    )

    if args.test:
        status = teste_verbindung(daten)
        print(("VERBUNDEN: " if status.verbunden else "NICHT VERBUNDEN: ") + status.meldung)
        return 0 if status.verbunden else 1

    try:
        with HeadunitClient(daten) as client:
            if args.analyse:
                bericht = _analysiere_fehlerspeicher(katalog, client)
            else:
                bericht = _fuehre_alle_aus(katalog, client)
    except SSHVerbindungsError as fehler:
        print(f"Fehler: {fehler}", file=sys.stderr)
        return 1

    if args.export:
        try:
            Path(args.export).write_text(bericht, encoding="utf-8")
            print(f"\nBericht gespeichert: {args.export}")
        except OSError as fehler:
            print(f"Export fehlgeschlagen: {fehler}", file=sys.stderr)
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
