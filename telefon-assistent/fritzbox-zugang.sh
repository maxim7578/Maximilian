#!/data/data/com.termux/files/usr/bin/bash
# Trägt Benutzername und Kennwort des IP-Telefons in .env ein und prüft die Anmeldung an der FRITZ!Box.
cd "$(dirname "$0")"
if [ ! -f .env ]; then
  echo "❌ Keine .env gefunden. Bitte zuerst das Einrichtungsskript ausführen."
  exit 1
fi
echo "FRITZ!Box → Telefonie → Telefoniegeräte → Stift beim KI-Assistent → Reiter „Anmeldedaten“"
read -r -p "Benutzername [kiassistent]: " BENUTZER < /dev/tty
BENUTZER="${BENUTZER:-kiassistent}"
while true; do
  read -r -s -p "Kennwort (wird beim Tippen nicht angezeigt): " KENNWORT < /dev/tty; echo
  read -r -s -p "Kennwort noch einmal: " KENNWORT2 < /dev/tty; echo
  if [ -z "$KENNWORT" ]; then echo "Das Kennwort ist leer. Bitte noch einmal."
  elif [ "$KENNWORT" != "$KENNWORT2" ]; then echo "Die beiden Eingaben sind verschieden. Bitte noch einmal."
  else break; fi
done
BENUTZER="$BENUTZER" KENNWORT="$KENNWORT" python - <<'PY'
import os
from pathlib import Path
datei = Path(".env")
werte = {"FRITZBOX_BENUTZER": os.environ["BENUTZER"].strip(), "FRITZBOX_KENNWORT": os.environ["KENNWORT"]}
zeilen = []
for zeile in datei.read_text(encoding="utf-8").splitlines():
    name = zeile.split("=", 1)[0].strip()
    zeilen.append(f"{name}={werte.pop(name)}" if name in werte else zeile)
zeilen += [f"{name}={wert}" for name, wert in werte.items()]
datei.write_text("\n".join(zeilen) + "\n", encoding="utf-8")
PY
chmod 600 .env
echo "✅ Gespeichert. Ich teste jetzt die Anmeldung …"
echo
python -m assistent.handy.pruefen
