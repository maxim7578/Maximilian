#!/bin/sh
# Startskript im Container: läuft als root nur so lange, bis die Ordner dem Benutzer
# "assistent" (UID/GID 1000) gehören, und startet das eigentliche Kommando dann ohne root.
# UID 1000 ist auch der Benutzer, als der Asterisk im Image andrius/asterisk läuft – so kann
# Asterisk die erzeugte Konfiguration (Rechte 0600) lesen.
set -eu

ZIEL_UID=1000
ZIEL_GID=1000
DATEN="${DATEN_ORDNER:-/daten}"
ASTERISK="${ASTERISK_ORDNER:-/asterisk}"

if [ "$(id -u)" != "0" ]; then
  exec "$@"  # schon ohne root gestartet (z. B. mit "user:" in docker-compose.yml)
fi

# Besitz nur ändern, wenn nötig (ältere Installationen: ./daten und ./asterisk/etc gehören root).
besitz_uebergeben() {
  [ -d "$1" ] || return 0
  if [ -n "$(find "$1" \( ! -user "$ZIEL_UID" -o ! -group "$ZIEL_GID" \) -print -quit)" ]; then
    chown -R "$ZIEL_UID:$ZIEL_GID" "$1"
  fi
}

besitz_uebergeben "$DATEN"
if [ -d "$ASTERISK" ]; then
  # Dienst "konfig": schreibt nach /asterisk/etc
  mkdir -p "$ASTERISK/etc"
  besitz_uebergeben "$ASTERISK/etc"
fi

export HOME=/home/assistent
exec setpriv --reuid="$ZIEL_UID" --regid="$ZIEL_GID" --init-groups --no-new-privs "$@"
