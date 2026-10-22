#!/bin/bash
# Klont den GitHub MCP Server (https://github.com/github/github-mcp-server) neben
# dieses Repo und installiert das Binary in Claude Code Cloud-Sessions.
set -euo pipefail

if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

# Asynchron: Die Session startet sofort, der Server baut sich im Hintergrund.
echo '{"async": true, "asyncTimeout": 600000}'

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/../.." && pwd)}"
SRC_DIR="$(dirname "$PROJECT_DIR")/github-mcp-server"
REPO="https://github.com/github/github-mcp-server.git"
LOG_DIR="$HOME/.cache/github-mcp-server-session-start"
LOG="$LOG_DIR/setup.log"
mkdir -p "$LOG_DIR" "$HOME/.local/bin"

if [ ! -d "$SRC_DIR/.git" ]; then
  git clone --quiet --single-branch --depth 1 "$REPO" "$SRC_DIR"
fi

# go install legt das Binary nach $(go env GOPATH)/bin, das nicht im PATH liegt;
# der Link in ~/.local/bin macht `github-mcp-server` direkt aufrufbar.
if ! (cd "$SRC_DIR" && go install ./cmd/github-mcp-server) < /dev/null > "$LOG" 2>&1; then
  echo "github-mcp-server-Build ist fehlgeschlagen, Log: $LOG" >&2
  tail -n 30 "$LOG" >&2
  exit 1
fi
ln -sf "$(go env GOPATH)/bin/github-mcp-server" "$HOME/.local/bin/github-mcp-server"

echo "github-mcp-server ($(git -C "$SRC_DIR" rev-parse --short HEAD)) ist installiert, Quelle: $SRC_DIR"
