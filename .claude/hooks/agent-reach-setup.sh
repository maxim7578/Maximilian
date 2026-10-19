#!/bin/bash
# Installiert Agent Reach (agent-reach/, Skill in .claude/skills/agent-reach) in
# Claude Code Cloud-Sessions. Ein Fehler hier bricht die Session nicht ab.
set -euo pipefail

if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

# Asynchron: Die Session startet sofort, Agent Reach installiert sich im Hintergrund.
echo '{"async": true, "asyncTimeout": 300000}'

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/../.." && pwd)}"
LOG_DIR="$HOME/.cache/agent-reach-session-start"
LOG="$LOG_DIR/setup.log"
mkdir -p "$LOG_DIR"
export PATH="$HOME/.local/bin:$PATH"

# Editierbar installiert: Änderungen in agent-reach/ gelten sofort. yt-dlp kommt
# als eigener Befehl mit, weil der YouTube-Kanal ihn aufruft.
if ! command -v agent-reach > /dev/null 2>&1; then
  if ! uv tool install --quiet --editable "$PROJECT_DIR/agent-reach" \
      --with-executables-from yt-dlp > "$LOG" 2>&1; then
    echo "Agent-Reach-Installation ist fehlgeschlagen, Log: $LOG" >&2
    exit 0
  fi
fi

# YouTube braucht in yt-dlp eine JS-Laufzeit; Node ist in der Cloud-Umgebung vorhanden.
YTDLP_CONFIG="${XDG_CONFIG_HOME:-$HOME/.config}/yt-dlp/config"
if command -v node > /dev/null 2>&1 && ! grep -qxF -- '--js-runtimes node' "$YTDLP_CONFIG" 2>/dev/null; then
  mkdir -p "$(dirname "$YTDLP_CONFIG")"
  echo '--js-runtimes node' >> "$YTDLP_CONFIG"
fi

if [ -n "${CLAUDE_ENV_FILE:-}" ]; then
  echo "export PATH=\"$HOME/.local/bin:\$PATH\"" >> "$CLAUDE_ENV_FILE"
fi

echo "$(agent-reach version) ist installiert (Skill: agent-reach)."
