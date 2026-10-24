# Maximilian

## Instagram-Daten

Die Instagram-Skills (`/ig-*`) schreiben nach `~/.claude/instagram/`. In
Cloud-Sessions ist das ein Link auf `instagram/` in diesem Repo. Wenn sich
dort eine Datei geändert hat, sie committen und auf den aktuellen Branch
pushen, sonst ist sie am Ende der Session weg.

## OpenMontage (Videoproduktion)

OpenMontage liegt im Hauptverzeichnis (`pipeline_defs/`, `tools/`, `skills/`,
`remotion-composer/` usw.). Bei Aufgaben zu Videoproduktion, Montage, Rendering
oder den OpenMontage-Pipelines zuerst [`AGENT_GUIDE.md`](AGENT_GUIDE.md) lesen
und dessen Routing-Regeln folgen. Für andere Aufgaben im Repo gilt das nicht.

## Tests immer auf Deutsch

Alle Tests auf Deutsch zeigen und schreiben: Testnamen (`describe`/`it`,
pgTAP-Beschreibungen), Testausgaben-Zusammenfassungen und Testberichte an den
Nutzer. Gilt für alle Projekte.

## Artemis (Android-Geräte steuern)

Artemis liegt in `artemis/` und ist in `.mcp.json` als MCP-Server `artemis`
eingetragen (`mobile_run_task`, `mobile_get_device_state` usw.). Bevor du die
Artemis-Tools nutzt, [`artemis/mcp_server/rules.md`](artemis/mcp_server/rules.md)
lesen. Die Tools brauchen ein per ADB erreichbares Android-Gerät oder einen
Emulator und einen LLM-Schlüssel (z. B. `GEMINI_API_KEY`) in der Umgebung oder in
`artemis/.env`; in Cloud-Sessions gibt es kein Gerät.
