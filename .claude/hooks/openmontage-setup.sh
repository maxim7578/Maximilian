#!/bin/bash
# Installiert die OpenMontage-Abhängigkeiten in Claude Code Cloud-Sessions:
# Python-venv (inkl. Test-Werkzeuge), Remotion-Composer, Piper-TTS, HyperFrames und .env.
set -euo pipefail

if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

# Asynchron: Die Session startet sofort, OpenMontage installiert sich im Hintergrund.
echo '{"async": true, "asyncTimeout": 900000}'

cd "$CLAUDE_PROJECT_DIR"

LOG_DIR="$HOME/.cache/openmontage-session-start"
LOG="$LOG_DIR/setup.log"
mkdir -p "$LOG_DIR"

# Python 3.12 statt der Mindestversion 3.10: Sicherheitsupdates wie Pillow 13 gibt es nur
# noch für Python >= 3.11. Eine ältere .venv wird deshalb einmalig neu angelegt.
VENV_PYTHON_VERSION=3.12
if [ -x .venv/bin/python ] && ! .venv/bin/python -c 'import sys; sys.exit(sys.version_info < (3, 11))'; then
  rm -rf .venv
fi

# make setup und install-dev sind idempotent (pip/npm überspringen bereits Installiertes,
# .env wird nur angelegt, wenn sie fehlt).
if ! make setup install-dev PYTHON_VERSION="$VENV_PYTHON_VERSION" < /dev/null > "$LOG" 2>&1; then
  echo "OpenMontage-Setup ist fehlgeschlagen, Log: $LOG" >&2
  tail -n 30 "$LOG" >&2
  exit 1
fi

# pip selbst aktuell halten: Eine neu angelegte venv bringt das pip ihres Python-Builds mit
# (z. B. 24.0 mit bekannten Lücken). Ein Fehler hier bricht die Session nicht ab.
.venv/bin/python -m pip install --quiet --disable-pip-version-check --upgrade pip >> "$LOG" 2>&1 \
  || echo "pip-Update in .venv fehlgeschlagen, Log: $LOG" >&2

# Die venv in den PATH der Session legen, damit `python` und `piper` sie verwenden.
if [ -n "${CLAUDE_ENV_FILE:-}" ]; then
  echo "export VIRTUAL_ENV=\"$CLAUDE_PROJECT_DIR/.venv\"" >> "$CLAUDE_ENV_FILE"
  echo "export PATH=\"$CLAUDE_PROJECT_DIR/.venv/bin:\$PATH\"" >> "$CLAUDE_ENV_FILE"
fi

# Piper-Stimmen laden (landen im Projektordner, *.onnx ist per .gitignore ausgeschlossen).
# Optional: schlägt fehl, solange die Netzwerkrichtlinie huggingface.co sperrt.
VOICES_OK=true
for voice in en_US-lessac-medium de_DE-thorsten-medium; do
  if [ ! -f "$voice.onnx" ]; then
    if ! .venv/bin/python -m piper.download_voices --download-dir "$CLAUDE_PROJECT_DIR" "$voice" >> "$LOG" 2>&1; then
      VOICES_OK=false
    fi
  fi
done

if [ "$VOICES_OK" = true ]; then
  echo "OpenMontage ist eingerichtet (venv, Remotion, HyperFrames, Piper-Stimmen)."
else
  echo "OpenMontage ist eingerichtet; Piper-Stimmen konnten nicht geladen werden (huggingface.co gesperrt?)."
fi
