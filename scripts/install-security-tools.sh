#!/usr/bin/env bash
# Installiert die Werkzeuge, die die Cybersecurity-Skills in .claude/skills/ brauchen.
# Aufruf: bash scripts/install-security-tools.sh
# Schon vorhandene Werkzeuge werden übersprungen. Ziel für Programme: $BIN_DIR.
set -uo pipefail

BIN_DIR="${BIN_DIR:-/usr/local/bin}"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

ARCH="$(uname -m)"
case "$ARCH" in
  x86_64) GOARCH=amd64 ;;
  aarch64|arm64) GOARCH=arm64 ;;
  *) echo "Nicht unterstützte Architektur: $ARCH" >&2; exit 1 ;;
esac

ok=() fehler=()

vorhanden() { command -v "$1" >/dev/null 2>&1; }

neueste_version() { # $1 = owner/repo -> neuester stabiler Tag ohne führendes v
  # Über git statt GitHub-API, weil die API hinter manchen Proxys gesperrt ist.
  git ls-remote --tags --refs --sort=-v:refname "https://github.com/$1" 'v*' \
    | sed 's|.*refs/tags/v||' | grep -E '^[0-9]+\.[0-9]+\.[0-9]+$' | head -1
}

installiere() { # $1 = Name, $2 = Funktion
  if vorhanden "$1"; then ok+=("$1 (schon da)"); return; fi
  echo "→ $1"
  if "$2" && vorhanden "$1"; then ok+=("$1"); else fehler+=("$1"); fi
}

# --- Programme aus offiziellen GitHub-Releases ---
gitleaks_inst() {
  local v; v="$(neueste_version gitleaks/gitleaks)"; [ -n "$v" ] || return 1
  local a=x64; [ "$GOARCH" = arm64 ] && a=arm64
  curl -fsSL "https://github.com/gitleaks/gitleaks/releases/download/v$v/gitleaks_${v}_linux_${a}.tar.gz" \
    | tar -xz -C "$TMP" gitleaks && install -m 755 "$TMP/gitleaks" "$BIN_DIR/gitleaks"
}
anchore_inst() { # syft und grype: gleiches Release-Schema
  local v; v="$(neueste_version "anchore/$1")"; [ -n "$v" ] || return 1
  curl -fsSL "https://github.com/anchore/$1/releases/download/v$v/$1_${v}_linux_$GOARCH.tar.gz" \
    | tar -xz -C "$TMP" "$1" && install -m 755 "$TMP/$1" "$BIN_DIR/$1"
}
syft_inst() { anchore_inst syft; }
grype_inst() { anchore_inst grype; }
trivy_inst() {
  local v; v="$(neueste_version aquasecurity/trivy)"; [ -n "$v" ] || return 1
  local a=64bit; [ "$GOARCH" = arm64 ] && a=ARM64
  curl -fsSL "https://github.com/aquasecurity/trivy/releases/download/v$v/trivy_${v}_Linux-$a.tar.gz" \
    | tar -xz -C "$TMP" trivy && install -m 755 "$TMP/trivy" "$BIN_DIR/trivy"
}
cosign_inst() {
  curl -fsSL "https://github.com/sigstore/cosign/releases/latest/download/cosign-linux-$GOARCH" -o "$TMP/cosign" \
    && install -m 755 "$TMP/cosign" "$BIN_DIR/cosign"
}
osv_inst() {
  curl -fsSL "https://github.com/google/osv-scanner/releases/latest/download/osv-scanner_linux_$GOARCH" -o "$TMP/osv-scanner" \
    && install -m 755 "$TMP/osv-scanner" "$BIN_DIR/osv-scanner"
}

# --- Python-Werkzeuge, je in eigener Umgebung über uv ---
uv_tool() { uv tool install --quiet "$1"; }
semgrep_inst() { uv_tool semgrep; }
guarddog_inst() { uv_tool guarddog; }
precommit_inst() { uv_tool pre-commit; }
# Früher „mcp-scan“ (Invariant Labs), umbenannt in snyk-agent-scan.
agentscan_inst() { uv_tool snyk-agent-scan; }

# --- npm ---
promptfoo_inst() { npm install -g --silent promptfoo >/dev/null; }

vorhanden uv || { curl -fsSL https://astral.sh/uv/install.sh -o "$TMP/uv.sh" && sh "$TMP/uv.sh"; }
export PATH="$HOME/.local/bin:$PATH"

installiere gitleaks gitleaks_inst
installiere syft syft_inst
installiere grype grype_inst
installiere trivy trivy_inst
installiere cosign cosign_inst
installiere osv-scanner osv_inst
installiere semgrep semgrep_inst
installiere guarddog guarddog_inst
installiere pre-commit precommit_inst
installiere snyk-agent-scan agentscan_inst
installiere promptfoo promptfoo_inst

# --- Python-Bibliotheken, die die scripts/agent.py-Dateien importieren ---
# Ziel ist die .venv des Projekts (die nutzt die Session als python3), sonst python3.
PROJEKT="$(cd "$(dirname "$0")/.." && pwd)"
PY="${SECURITY_TOOLS_PYTHON:-}"
if [ -z "$PY" ]; then
  if [ -x "$PROJEKT/.venv/bin/python" ]; then PY="$PROJEKT/.venv/bin/python"; else PY=python3; fi
fi
if "$PY" -c 'import requests, yaml, jwt, cryptography, bs4, pypdf, dns' 2>/dev/null; then
  ok+=("Python-Bibliotheken (schon da)")
else
  echo "→ Python-Bibliotheken ($PY)"
  # --user nur außerhalb einer virtuellen Umgebung, dort ist es nicht erlaubt.
  PIP_USER="$("$PY" -c 'import sys; print("" if sys.prefix != sys.base_prefix else "--user")')"
  if "$PY" -m pip install --quiet --disable-pip-version-check $PIP_USER \
      requests pyyaml pyjwt cryptography beautifulsoup4 pypdf dnspython; then
    ok+=("Python-Bibliotheken")
  else
    fehler+=("Python-Bibliotheken")
  fi
fi

echo
echo "Installiert: ${ok[*]:-nichts}"
[ ${#fehler[@]} -eq 0 ] && exit 0
echo "Fehlgeschlagen: ${fehler[*]}" >&2
exit 1
