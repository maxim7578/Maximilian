# Herkunft

Dieser Ordner ist eine Kopie von https://github.com/Panniantong/Agent-Reach
(Commit `94f06c1`, „Merge pull request #787 from Panniantong/chore/step0-hotfixes“, Version 1.5.0),
MIT-Lizenz – siehe `LICENSE`.

Der Skill dazu liegt in `.claude/skills/agent-reach/` (Kopie von
`agent_reach/skill/SKILL_en.md` und `agent_reach/skill/references/`).

In Cloud-Sessions installiert `.claude/hooks/agent-reach-setup.sh` das Programm
automatisch. Von Hand (aus dem Repo-Hauptverzeichnis):

```bash
uv tool install --editable ./agent-reach --with-executables-from yt-dlp
agent-reach doctor
```

Tests:

```bash
cd agent-reach && bash test.sh
```
