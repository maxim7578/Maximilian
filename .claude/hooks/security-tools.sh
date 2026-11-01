#!/bin/bash
# Installiert in Claude Code Cloud-Sessions die Werkzeuge für die Cybersecurity-Skills
# (gitleaks, semgrep, trivy, syft, grype, cosign, osv-scanner, guarddog, pre-commit,
# snyk-agent-scan, promptfoo, Python-Bibliotheken). Siehe scripts/install-security-tools.sh.
set -euo pipefail

if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/../.." && pwd)}"
LOG_DIR="$HOME/.cache/security-tools-session-start"
LOG="$LOG_DIR/setup.log"
mkdir -p "$LOG_DIR"

# Die Python-Bibliotheken gehören in die .venv, die openmontage-setup.sh parallel anlegt.
# Bis zu 60 Sekunden auf sie warten; danach installiert das Skript in python3.
for _ in $(seq 1 30); do
  [ -x "$PROJECT_DIR/.venv/bin/python" ] && break
  sleep 2
done

# Das Skript überspringt alles, was schon installiert ist. Bei einem Container aus dem
# Cache dauert das nur Sekunden, nur der erste Lauf lädt die Werkzeuge (etwa 1–2 Minuten).
if ! bash "$PROJECT_DIR/scripts/install-security-tools.sh" < /dev/null > "$LOG" 2>&1; then
  echo "Installation der Sicherheitswerkzeuge ist teilweise fehlgeschlagen, Log: $LOG" >&2
  tail -n 20 "$LOG" >&2
  exit 1
fi

# uv-Werkzeuge (semgrep, guarddog, pre-commit, snyk-agent-scan) liegen in ~/.local/bin.
if [ -n "${CLAUDE_ENV_FILE:-}" ]; then
  echo "export PATH=\"\$HOME/.local/bin:\$PATH\"" >> "$CLAUDE_ENV_FILE"
fi

echo "Sicherheitswerkzeuge für die Cybersecurity-Skills sind installiert, Log: $LOG"
