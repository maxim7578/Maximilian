"""Erzeugt die Asterisk-Konfiguration aus den Vorlagen und der Datei .env.

Aufruf: python -m assistent.konfig [vorlagen-ordner] [ziel-ordner]
"""

import os
import re
import sys
import tempfile
from collections.abc import Mapping
from pathlib import Path

PLATZHALTER = re.compile(r"\{\{([A-Z_]+)\}\}")
# Diese Zeichen würden die Asterisk-Konfiguration zerstören.
VERBOTEN = re.compile(r"[;\s\[\]\"'\\]")
# Asterisk legt erst nach so vielen Sekunden über MAX_GESPRAECH_SEKUNDEN hart auf, damit der
# Assistent sich vorher normal verabschieden kann (siehe zeitlimit() in gespraech.py).
ZEITLIMIT_PUFFER = 60
# Das Asterisk-Image läuft standardmäßig als UID/GID 1000 (PUID/PGID).
STANDARD_BESITZER = 1000


class KonfigFehler(Exception):
    pass


def werte_aus_umgebung(env: dict[str, str]) -> dict[str, str]:
    def pflicht(name: str) -> str:
        wert = env.get(name, "").strip()
        if not wert or wert.startswith("HIER_"):
            raise KonfigFehler(f"Bitte {name} in der Datei .env eintragen.")
        if VERBOTEN.search(wert):
            raise KonfigFehler(
                f"{name} enthält ein Leerzeichen oder Sonderzeichen wie ; [ ] \" ' \\. "
                "Bitte nur Buchstaben, Ziffern und - _ . ! ? # * + verwenden."
            )
        return wert

    eingehend = env.get("EINGEHENDE_ANRUFE", "aus").strip().lower() in ("an", "ja", "1")
    max_sekunden = env.get("MAX_GESPRAECH_SEKUNDEN", "300").strip() or "300"
    if not max_sekunden.isdigit() or int(max_sekunden) <= 0:
        raise KonfigFehler("MAX_GESPRAECH_SEKUNDEN muss eine ganze Zahl größer 0 sein.")
    return {
        "FRITZBOX_ADRESSE": pflicht("FRITZBOX_ADRESSE"),
        "FRITZBOX_BENUTZER": pflicht("FRITZBOX_BENUTZER"),
        "FRITZBOX_KENNWORT": pflicht("FRITZBOX_KENNWORT"),
        "ARI_KENNWORT": pflicht("ARI_KENNWORT"),
        "APP_PORT": env.get("APP_PORT", "8765").strip() or "8765",
        "SIP_PORT": env.get("SIP_PORT", "5060").strip() or "5060",
        "EINGEHEND": "an" if eingehend else "aus",
        "GESPRAECH_LIMIT_SEKUNDEN": str(int(max_sekunden) + ZEITLIMIT_PUFFER),
    }


def besitzer_aus_umgebung(env: Mapping[str, str]) -> tuple[int, int] | None:
    """UID/GID, denen die Dateien gehören sollen – nur nötig, wenn wir als root laufen.

    Ohne root (oder unter Windows ohne os.geteuid) gehören die Dateien ohnehin dem
    aufrufenden Benutzer; dann wird nichts geändert.
    """
    geteuid = getattr(os, "geteuid", None)
    if geteuid is None or not hasattr(os, "chown") or geteuid() != 0:
        return None

    def zahl(name: str) -> int:
        wert = env.get(name, "").strip() or str(STANDARD_BESITZER)
        if not wert.isdigit():
            raise KonfigFehler(f"{name} muss eine Zahl sein (z. B. 1000).")
        return int(wert)

    return zahl("PUID"), zahl("PGID")


def _sicher_schreiben(datei: Path, text: str, besitzer: tuple[int, int] | None) -> None:
    """Schreibt mit Rechten 0600 – ohne Moment, in dem die Datei für andere lesbar ist.

    Die Zwischendatei wird gleich mit 0600 angelegt und dann atomar umbenannt; so werden
    auch ältere Dateien mit offenen Rechten ersetzt.
    """
    fd, zwischen = tempfile.mkstemp(dir=datei.parent, prefix=f".{datei.name}.")  # immer 0600
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
        if besitzer is not None:
            os.chown(zwischen, *besitzer)
        os.replace(zwischen, datei)
    except BaseException:
        Path(zwischen).unlink(missing_ok=True)
        raise


def erzeugen(
    vorlagen: Path, ziel: Path, werte: dict[str, str], env: Mapping[str, str] | None = None
) -> list[Path]:
    """Füllt die Vorlagen aus. pjsip.conf enthält das FRITZ!Box-Kennwort, daher sind
    Ordner (0700) und Dateien (0600) nur für den Besitzer lesbar; als root bekommt
    PUID:PGID (Standard 1000:1000, der Asterisk-Benutzer im Container) den Besitz."""
    besitzer = besitzer_aus_umgebung(os.environ if env is None else env)
    ziel.mkdir(mode=0o700, parents=True, exist_ok=True)
    ziel.chmod(0o700)
    if besitzer is not None:
        os.chown(ziel, *besitzer)
    geschrieben = []
    for vorlage in sorted(vorlagen.glob("*.conf")):
        text = vorlage.read_text(encoding="utf-8")

        def ersetzen(treffer: re.Match) -> str:
            name = treffer.group(1)
            if name not in werte:
                raise KonfigFehler(f"Unbekannter Platzhalter {{{{{name}}}}} in {vorlage.name}")
            return werte[name]

        datei = ziel / vorlage.name
        _sicher_schreiben(datei, PLATZHALTER.sub(ersetzen, text), besitzer)
        geschrieben.append(datei)
    return geschrieben


def main() -> None:
    vorlagen = Path(sys.argv[1] if len(sys.argv) > 1 else "/asterisk/vorlagen")
    ziel = Path(sys.argv[2] if len(sys.argv) > 2 else "/asterisk/etc")
    try:
        dateien = erzeugen(vorlagen, ziel, werte_aus_umgebung(dict(os.environ)))
    except KonfigFehler as fehler:
        print(f"FEHLER: {fehler}", file=sys.stderr)
        sys.exit(1)
    print(f"Asterisk-Konfiguration erzeugt ({len(dateien)} Dateien in {ziel}).")


if __name__ == "__main__":
    main()
