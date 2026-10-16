#!/bin/bash
# Richtet Claude Code Cloud-Sessions ein: Instagram-Datenordner und gstack
# (https://github.com/garrytan/gstack).
set -euo pipefail

if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

# Asynchron: Die Session startet sofort, gstack installiert sich im Hintergrund.
echo '{"async": true, "asyncTimeout": 600000}'

# Die Instagram-Skills (.claude/skills/ig-*) speichern voice.md, plan.md,
# swipe.md und log.md in ~/.claude/instagram/. Das Home-Verzeichnis geht am
# Ende jeder Cloud-Session verloren, deshalb zeigt der Ordner auf instagram/
# im Repo.
PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/../.." && pwd)}"
IG_DATA="$PROJECT_DIR/instagram"
IG_LINK="$HOME/.claude/instagram"
mkdir -p "$IG_DATA" "$(dirname "$IG_LINK")"
if [ -L "$IG_LINK" ] || [ ! -e "$IG_LINK" ]; then
  ln -sfn "$IG_DATA" "$IG_LINK"
else
  echo "$IG_LINK ist ein echter Ordner und wird nicht auf $IG_DATA umgeleitet." >&2
fi

GSTACK_DIR="$HOME/.claude/skills/gstack"
GSTACK_REPO="https://github.com/garrytan/gstack.git"
MARKER="$HOME/.cache/gstack-session-start/setup.sha"
LOG="$HOME/.cache/gstack-session-start/setup.log"
PREINSTALLED_CHROMIUM="/opt/pw-browsers/chromium"

mkdir -p "$(dirname "$MARKER")"

# Der Proxy der Cloud-Umgebung blockiert den Playwright-Download (cdn.playwright.dev).
# gstack nutzt stattdessen das vorinstallierte Chromium über GSTACK_CHROMIUM_PATH.
if [ -x "$PREINSTALLED_CHROMIUM" ]; then
  export GSTACK_SKIP_PLAYWRIGHT=1
  export GSTACK_CHROMIUM_PATH="$PREINSTALLED_CHROMIUM"
  if [ -n "${CLAUDE_ENV_FILE:-}" ]; then
    echo "export GSTACK_CHROMIUM_PATH=\"$PREINSTALLED_CHROMIUM\"" >> "$CLAUDE_ENV_FILE"
  fi
fi

if [ ! -d "$GSTACK_DIR/.git" ]; then
  mkdir -p "$(dirname "$GSTACK_DIR")"
  git clone --quiet --single-branch --depth 1 "$GSTACK_REPO" "$GSTACK_DIR"
fi

# ./setup nur ausführen, wenn sich der gstack-Stand oder die Setup-Optionen seit dem
# letzten Lauf geändert haben. Die Plan-Tune-Hooks protokollieren Rückfragen für /plan-tune.
HEAD_SHA="$(git -C "$GSTACK_DIR" rev-parse HEAD)"
SETUP_STAMP="$HEAD_SHA plan-tune-hooks"
if [ "$(cat "$MARKER" 2>/dev/null || true)" != "$SETUP_STAMP" ]; then
  if ! (cd "$GSTACK_DIR" && GSTACK_PLAN_TUNE_HOOKS=yes ./setup --quiet < /dev/null > "$LOG" 2>&1); then
    echo "gstack ./setup ist fehlgeschlagen, Log: $LOG" >&2
    tail -n 30 "$LOG" >&2
    exit 1
  fi
  echo "$SETUP_STAMP" > "$MARKER"
fi

echo "gstack $(cat "$GSTACK_DIR/VERSION") ist installiert (Skills in ~/.claude/skills)."

# Codex-CLI für unabhängige Zweitmeinungen in /review, /ship und /office-hours.
# Nur mit OPENAI_API_KEY (Umgebungsvariable der Cloud-Umgebung), sonst nutzt gstack
# einen Claude-Subagent.
if [ -n "${OPENAI_API_KEY:-}" ] && ! command -v codex > /dev/null 2>&1; then
  if ! npm install -g --silent @openai/codex > "$HOME/.cache/gstack-session-start/codex.log" 2>&1; then
    echo "Codex-Installation ist fehlgeschlagen, Log: $HOME/.cache/gstack-session-start/codex.log" >&2
  fi
fi

# Installiert graphify (https://github.com/Graphify-Labs/graphify) samt /graphify-Skill.
# Ein Fehler hier bricht die Session nicht ab, gstack bleibt nutzbar.
export PATH="$HOME/.local/bin:$PATH"
GRAPHIFY_LOG="$HOME/.cache/gstack-session-start/graphify.log"
if ! command -v graphify > /dev/null 2>&1; then
  if ! uv tool install --quiet graphifyy > "$GRAPHIFY_LOG" 2>&1; then
    echo "graphify-Installation ist fehlgeschlagen, Log: $GRAPHIFY_LOG" >&2
    exit 0
  fi
fi
if [ ! -f "$HOME/.claude/skills/graphify/SKILL.md" ]; then
  graphify install --platform claude >> "$GRAPHIFY_LOG" 2>&1 || {
    echo "graphify install ist fehlgeschlagen, Log: $GRAPHIFY_LOG" >&2
    exit 0
  }
fi
echo "$(graphify --version) ist installiert (Skill: /graphify)."
