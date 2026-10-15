#!/data/data/com.termux/files/usr/bin/bash
# Einrichtung des Telefonassistenten auf einem Android-Handy (Termux).
# Aufruf in Termux:
#   curl -sL https://raw.githubusercontent.com/maxim7578/Maximilian/claude/gracious-sagan-dus97i/telefon-assistent/einrichten-handy.sh | bash
set -e
ZWEIG="${ZWEIG:-claude/gracious-sagan-dus97i}"
ORDNER="$HOME/Maximilian/telefon-assistent"
DATEN="$HOME/telefon-daten"

frage() { # frage VARIABLE "Text" [geheim]
  local antwort
  if [ "$3" = "geheim" ]; then read -r -s -p "$2: " antwort < /dev/tty; echo; else read -r -p "$2: " antwort < /dev/tty; fi
  printf -v "$1" '%s' "$antwort"
}

# Alles steckt in main(), damit "curl … | bash" erst das ganze Skript liest, bevor es losgeht.
main() {
echo "=== 1/5 Programme installieren (dauert ein paar Minuten) ==="
yes | pkg upgrade -y
yes | pkg install -y python python-numpy python-onnxruntime espeak ffmpeg git curl
# aiohttp & Co. ohne C-Erweiterungen installieren (reines Python, läuft überall)
export AIOHTTP_NO_EXTENSIONS=1 MULTIDICT_NO_EXTENSIONS=1 YARL_NO_EXTENSIONS=1 \
       FROZENLIST_NO_EXTENSIONS=1 PROPCACHE_NO_EXTENSIONS=1

echo "=== 2/5 Assistent herunterladen ==="
if [ -d "$HOME/Maximilian/.git" ]; then
  git -C "$HOME/Maximilian" fetch -q origin "$ZWEIG" && git -C "$HOME/Maximilian" checkout -q -B "$ZWEIG" "origin/$ZWEIG"
else
  git clone -q -b "$ZWEIG" https://github.com/maxim7578/Maximilian.git "$HOME/Maximilian"
fi
cd "$ORDNER"
pip install -q -r requirements-handy.txt

echo "=== 3/5 Ersatzstimme (Piper) herunterladen ==="
mkdir -p "$DATEN/piper"
BASIS="https://huggingface.co/rhasspy/piper-voices/resolve/main/de/de_DE/thorsten/medium"
for datei in de_DE-thorsten-medium.onnx de_DE-thorsten-medium.onnx.json; do
  [ -s "$DATEN/piper/$datei" ] || curl -sL -o "$DATEN/piper/$datei" "$BASIS/$datei"
done

echo "=== 4/5 Deine Angaben ==="
if [ -f .env ]; then
  echo "Es gibt schon eine .env – ich lasse sie unverändert. (Zum Neu-Eingeben: rm $ORDNER/.env und Skript erneut starten.)"
else
  frage TOKEN "Telegram-Token von BotFather"
  frage GROQ "Groq-Schlüssel (gsk_...)"
  frage FB_BENUTZER "FRITZ!Box: Benutzername des IP-Telefons"
  frage FB_KENNWORT "FRITZ!Box: Kennwort des IP-Telefons (wird nicht angezeigt)" geheim
  frage NAME "Dein Name, wie im Satz 'der digitale Assistent von ...' (z. B. Herrn Mustermann)"
  frage ORT "Dein Wohnort (für die Nummernsuche)"
  echo
  echo ">>> Öffne jetzt Telegram, such deinen Bot und schick ihm: /start"
  echo "    Ich warte auf deine Nachricht …"
  CHAT_ID=""
  for _ in $(seq 1 120); do
    CHAT_ID=$(curl -s "https://api.telegram.org/bot$TOKEN/getUpdates" | python -c '
import json, sys
try:
    daten = json.load(sys.stdin)
    ids = [u["message"]["chat"]["id"] for u in daten.get("result", []) if "message" in u]
    print(ids[-1] if ids else "")
except Exception:
    print("")')
    [ -n "$CHAT_ID" ] && break
    sleep 3
  done
  if [ -z "$CHAT_ID" ]; then
    echo "Keine Nachricht erhalten. Prüf den Token und trag TELEGRAM_CHAT_ID später in $ORDNER/.env ein."
  else
    echo "Gefunden: Deine Chat-ID ist $CHAT_ID"
  fi
  cat > .env <<ENDE
TELEGRAM_BOT_TOKEN=$TOKEN
TELEGRAM_CHAT_ID=$CHAT_ID
GROQ_API_KEY=$GROQ
FRITZBOX_ADRESSE=192.168.178.1
FRITZBOX_BENUTZER=$FB_BENUTZER
FRITZBOX_KENNWORT=$FB_KENNWORT
INHABER_NAME=$NAME
WOHNORT=$ORT
RUECKRUFNUMMER=
EINGEHENDE_ANRUFE=aus
# Stimme: microsoft (sehr natürlich, braucht Internet) oder piper (lokal)
STIMME=microsoft
# Andere natürliche Stimmen: de-DE-ConradNeural, de-DE-AmalaNeural, de-DE-SeraphinaMultilingualNeural
MICROSOFT_STIMME=de-DE-KatjaNeural
DATEN_ORDNER=$DATEN
ENDE
  chmod 600 .env
fi

echo "=== 5/5 Autostart einrichten ==="
mkdir -p "$HOME/.termux/boot"
cat > "$HOME/.termux/boot/telefon-assistent" <<ENDE
#!/data/data/com.termux/files/usr/bin/bash
termux-wake-lock
cd "$ORDNER" && nohup ./start-handy.sh > /dev/null 2>&1 &
ENDE
chmod +x "$HOME/.termux/boot/telefon-assistent" start-handy.sh

echo
echo "Fertig! Starte den Assistenten jetzt mit:"
echo "  cd $ORDNER && ./start-handy.sh"
echo "Nach einem Neustart des Handys startet er automatisch (App Termux:Boot nötig)."
}

main "$@"
