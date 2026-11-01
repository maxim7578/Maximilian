# Cybersecurity-Skills – Übersicht

Kopie von [mukul975/Anthropic-Cybersecurity-Skills](https://github.com/mukul975/Anthropic-Cybersecurity-Skills),
Stand Commit `54a79883` (31.08.2026), Version 1.3.0, Lizenz Apache 2.0.

Das ist ein **Community-Projekt**, kein Projekt von Anthropic. Der Name täuscht.

## Was drin ist

818 Skills im Format von [agentskills.io](https://agentskills.io): Jeder Skill ist
ein Ordner `skills/<name>/` mit

- `SKILL.md`: Beschreibung (YAML-Kopf) und Arbeitsablauf
- `references/`: Hintergrund, API-Referenz, Normen
- `scripts/`: Python-Helfer (meist `agent.py`)
- `assets/`: Vorlagen und Checklisten (bei etwa der Hälfte)

Jeder Skill ist auf Frameworks abgebildet: MITRE ATT&CK, NIST CSF 2.0, MITRE ATLAS,
D3FEND, NIST AI RMF und MITRE F3 (Betrug). Die Abbildungen liegen in `mappings/`,
der maschinenlesbare Katalog in `index.json`.

## Bereiche

Gezählt aus dem Feld `subdomain` aller 818 Skills, Schreibvarianten zusammengefasst:

| Bereich | Skills |
|---|---|
| Cloud-Sicherheit | 66 |
| SOC & Security Operations | 63 |
| Threat Hunting | 58 |
| Threat Intelligence | 52 |
| Netzwerksicherheit | 43 |
| Web-Anwendungen | 42 |
| Digitale Forensik | 41 |
| Identitäten & Zugriffe (IAM) | 40 |
| Malware-Analyse | 39 |
| Red Teaming | 35 |
| Container & Kubernetes | 33 |
| OT/ICS (Industrieanlagen) | 29 |
| API-Sicherheit | 28 |
| Incident Response | 26 |
| Schwachstellenmanagement | 25 |
| Penetrationstests | 23 |
| DevSecOps | 22 |
| Zero Trust | 18 |
| Endpoint-Sicherheit | 17 |
| Phishing-Abwehr | 16 |
| Kryptografie | 16 |
| KI-Sicherheit | 14 |
| Mobile Apps | 13 |
| Ransomware-Abwehr | 13 |
| Compliance & Governance | 11 |
| Lieferkette (Pakete, SBOM) | 8 |
| Angriffserkennung | 7 |
| Hardware & Firmware | 6 |
| Täuschung (Honeytokens) | 6 |
| Datenschutz (DSGVO) | 3 |
| Blockchain | 2 |
| Funk (BLE) | 2 |
| Purple Team | 1 |

Ein großer Teil zielt auf Unternehmens-IT (SOC, Active Directory, Forensik,
Industrieanlagen). Für eigene Web-Apps, APIs und KI-Agenten sind vor allem
KI-Sicherheit, Lieferkette, DevSecOps, API- und Web-Sicherheit nützlich.

## Aktiv installierte Auswahl

Alle 818 Skills automatisch zu laden wäre schädlich: Die Beschreibungen sind
zusammen rund 322.000 Zeichen lang (etwa 80.000 Tokens), die in jeder Session
mitgeladen würden. Die README des Projekts nennt „~30 Tokens pro Skill“; im
Schnitt sind es aber rund 394 Zeichen, also etwa 100 Tokens.

Deshalb liegen nur diese 30 Skills als Kopie in `.claude/skills/` und werden
automatisch erkannt:

| Thema | Skills |
|---|---|
| KI-Agenten & MCP | `auditing-mcp-servers-for-tool-poisoning`, `securing-agentic-ai-tool-invocation`, `detecting-indirect-prompt-injection`, `testing-for-system-prompt-leakage`, `implementing-llm-guardrails-for-security` |
| Pakete & Lieferkette | `detecting-malicious-npm-packages`, `detecting-typosquatting-packages-in-npm-pypi`, `detecting-dependency-confusion`, `generating-and-analyzing-sboms` |
| GitHub & CI | `implementing-secret-scanning-with-gitleaks`, `securing-github-actions-workflows`, `integrating-sast-into-github-actions-pipeline`, `implementing-semgrep-for-custom-sast-rules`, `performing-threat-modeling-with-owasp-threat-dragon` |
| APIs | `implementing-api-key-security-controls`, `implementing-api-rate-limiting-and-throttling`, `testing-api-for-broken-object-level-authorization`, `testing-api-authentication-weaknesses`, `testing-oauth2-implementation-flaws` |
| Web-Apps | `performing-security-headers-audit`, `testing-cors-misconfiguration`, `testing-for-broken-access-control`, `testing-for-sensitive-data-exposure`, `testing-jwt-token-security` |
| Krypto & Datenschutz | `performing-cryptographic-audit-of-application`, `implementing-gdpr-data-subject-access-request`, `performing-privacy-impact-assessment` |
| E-Mail & Mobile | `implementing-dmarc-dkim-spf-email-security`, `testing-mobile-api-authentication`, `performing-android-app-static-analysis-with-mobsf` |

Weitere Skills aktivieren:

```bash
cp -r cybersecurity-skills/skills/<name> .claude/skills/
```

Einen passenden Skill finden, ohne alle zu laden:

```bash
grep -il "<stichwort>" cybersecurity-skills/skills/*/SKILL.md
```

## Sicherheitsprüfung beim Import

Vor der Übernahme wurde die ganze Bibliothek durchsucht:

- `curl … | sh`: nur offizielle Installer (Trivy, Syft, Grype, uv, Rustup …) und
  ausdrücklich als Angriffsbeispiel markierte Zeilen.
- Unsichtbare Unicode-Zeichen: nur in Erkennungscode, der genau solche Zeichen sucht.
- Secrets: nur die offiziellen AWS-Beispielschlüssel (`AKIAIOSFODNN7EXAMPLE`).
- In den Skripten der 30 aktiven Skills: keine Verbindungen zu unbekannten Servern,
  nur Paket-Registries, GitHub, `localhost` und Test-Platzhalter wie `evil.com`.

Das ist eine Stichwortprüfung, kein vollständiges Audit jedes Skripts. Skripte
vor dem Ausführen lesen.

## Nutzung

Angriffstechniken (C2, Phishing-Simulation, Exploits) nur gegen eigene Systeme
oder mit schriftlicher Erlaubnis einsetzen.
