"""Erzeugt die Asterisk-Konfiguration aus den Vorlagen und der Datei .env.

Aufruf: python -m assistent.konfig [vorlagen-ordner] [ziel-ordner]
"""

import os
import re
import sys
from pathlib import Path

PLATZHALTER = re.compile(r"\{\{([A-Z_]+)\}\}")
# Diese Zeichen würden die Asterisk-Konfiguration zerstören.
VERBOTEN = re.compile(r"[;\s\[\]\"'\\]")


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
    return {
        "FRITZBOX_ADRESSE": pflicht("FRITZBOX_ADRESSE"),
        "FRITZBOX_BENUTZER": pflicht("FRITZBOX_BENUTZER"),
        "FRITZBOX_KENNWORT": pflicht("FRITZBOX_KENNWORT"),
        "ARI_KENNWORT": pflicht("ARI_KENNWORT"),
        "APP_PORT": env.get("APP_PORT", "8765").strip() or "8765",
        "SIP_PORT": env.get("SIP_PORT", "5060").strip() or "5060",
        "EINGEHEND": "an" if eingehend else "aus",
    }


def erzeugen(vorlagen: Path, ziel: Path, werte: dict[str, str]) -> list[Path]:
    ziel.mkdir(parents=True, exist_ok=True)
    geschrieben = []
    for vorlage in sorted(vorlagen.glob("*.conf")):
        text = vorlage.read_text(encoding="utf-8")

        def ersetzen(treffer: re.Match) -> str:
            name = treffer.group(1)
            if name not in werte:
                raise KonfigFehler(f"Unbekannter Platzhalter {{{{{name}}}}} in {vorlage.name}")
            return werte[name]

        datei = ziel / vorlage.name
        datei.write_text(PLATZHALTER.sub(ersetzen, text), encoding="utf-8")
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
