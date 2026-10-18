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

## Base44: sehr sparsam mit Credits

Base44-Credits sparsam und gezielt einsetzen. Gilt für alle Base44-Apps.

- Änderungen direkt im Code machen (`read_file`, `edit_file`, `run_command`),
  nicht über den Builder-KI-Chat (`edit_base44_app`); der kostet bei jeder Runde
  Credits.
- Integrationen, die Credits verbrauchen (z. B. `GenerateImage`, `InvokeLLM`),
  erst mit einem kleinen Test (1–2 Aufrufe) prüfen und vor größeren Mengen die
  Anzahl nennen und nachfragen.
- Nichts doppelt erzeugen: Vorhandenes wiederverwenden, Fertiges überspringen.
- Keine Versuchs- oder Wiederholungsläufe auf Verdacht; erst Ursache klären,
  dann gezielt einmal ausführen.
