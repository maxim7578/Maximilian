#!/data/data/com.termux/files/usr/bin/bash
# Startet den Telefonassistenten und startet ihn neu, falls er abstürzt.
cd "$(dirname "$0")"
termux-wake-lock 2>/dev/null || true
mkdir -p "$HOME/telefon-daten"
echo "Telefonassistent läuft. Protokoll: ~/telefon-daten/assistent.log  (Beenden: Strg+C)"
while true; do
  python -m assistent.handy 2>&1 | tee -a "$HOME/telefon-daten/assistent.log"
  echo "Neustart in 10 Sekunden …"
  sleep 10
done
