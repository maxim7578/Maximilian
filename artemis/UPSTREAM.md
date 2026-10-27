# Herkunft

Dieser Ordner ist eine Kopie von https://github.com/google/artemis
(Commit `351ca84`, „fix: server status, CLI entrypoint, replay and test issues“), Apache-2.0-Lizenz – siehe `LICENSE`.

Artemis lässt KI-Assistenten und Testsuites echte Android-Geräte bedienen
(ADB, scrcpy, MCP-Server für Claude Code u. a.).

Start (aus diesem Ordner, Android-Gerät mit USB-Debugging oder Emulator angeschlossen):

```bash
cd artemis && ./start.sh
```

Die Workflows unter `artemis/.github/` laufen hier nicht, weil GitHub nur
`.github/` im Hauptverzeichnis auswertet.
