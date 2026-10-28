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

## REA (Reverse Engineering)

REA ([morluto/rea](https://github.com/morluto/rea)) ist in `.mcp.json` als
MCP-Server `rea` eingetragen (`npx -y rea-agents@6.8.0 mcp`, rund 230 Tools wie
`binary_session`, `open_binary`, `analyze_web_bundle`). Vor der Auswahl einer
Operation `binary_session` mit `{}` aufrufen; `result.tool_availability` zeigt,
was in der aktuellen Umgebung geht. Engines wie Ghidra, JADX, Hopper oder Frida
sind in Cloud-Sessions nicht installiert. Zum Aktualisieren die Version in
`.mcp.json` anheben.

## SkyAccess (Privatjet-Leerflüge)

SkyAccess ([sky-access/skyaccess-mcp](https://github.com/sky-access/skyaccess-mcp))
ist in `.mcp.json` als gehosteter MCP-Server `skyaccess` eingetragen
(`https://mcp.skyaccess.com/mcp`, ohne Konto und Schlüssel). Tools:
`search_empty_legs`, `get_flight`, `booking_handoff`, `get_charter_estimate`
(nur lesend) und `request_booking`, das Name, E-Mail und Reisewunsch an
SkyAccess schickt. `request_booking` nur aufrufen, wenn der Nutzer ausdrücklich
kontaktiert werden will. Preise in USD; Limit 30 Tool-Aufrufe pro Minute.
