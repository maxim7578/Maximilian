#!/bin/bash
# Richtet Claude Code Cloud-Sessions ein: Instagram-Datenordner und gstack
# (https://github.com/garrytan/gstack).
set -euo pipefail

if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

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

if [ ! -d "$GSTACK_DIR/.git" ]; then
  mkdir -p "$(dirname "$GSTACK_DIR")"
  git clone --quiet --single-branch --depth 1 "$GSTACK_REPO" "$GSTACK_DIR"
fi

# Der Proxy der Cloud-Umgebung blockiert den Playwright-Download (cdn.playwright.dev).
# gstack nutzt stattdessen das vorinstallierte Chromium über GSTACK_CHROMIUM_PATH.
if [ -x "$PREINSTALLED_CHROMIUM" ]; then
  export GSTACK_SKIP_PLAYWRIGHT=1
  export GSTACK_CHROMIUM_PATH="$PREINSTALLED_CHROMIUM"
  if [ -n "${CLAUDE_ENV_FILE:-}" ]; then
    echo "export GSTACK_CHROMIUM_PATH=\"$PREINSTALLED_CHROMIUM\"" >> "$CLAUDE_ENV_FILE"
  fi
fi

# ./setup nur ausführen, wenn sich der gstack-Stand seit dem letzten Lauf geändert hat.
HEAD_SHA="$(git -C "$GSTACK_DIR" rev-parse HEAD)"
if [ "$(cat "$MARKER" 2>/dev/null || true)" != "$HEAD_SHA" ]; then
  if ! (cd "$GSTACK_DIR" && ./setup --quiet < /dev/null > "$LOG" 2>&1); then
    echo "gstack ./setup ist fehlgeschlagen, Log: $LOG" >&2
    tail -n 30 "$LOG" >&2
    exit 1
  fi
  echo "$HEAD_SHA" > "$MARKER"
fi

echo "gstack $(cat "$GSTACK_DIR/VERSION") ist installiert (Skills in ~/.claude/skills)."
