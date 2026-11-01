# Sicherheitsprüfung des Repos Maximilian – 01.11.2026

Geprüfter Stand: `d484d2a` (Branch `claude/gstack-skill-setup-c85bwb`), 8.535 Dateien,
444 Commits. Die übernommene Bibliothek `cybersecurity-skills/` wurde nicht erneut geprüft.

## Ergebnis in Kürze

- **Keine echten Secrets** im Repo und in der gesamten Git-Historie.
- **Keine kritische Lücke im eigenen Code.** Die schwersten Punkte sind veraltete
  Abhängigkeiten mit bekannten Lücken und das Telefonie-Setup des Telefonassistenten,
  das SIP-Anfragen aus dem Netz zu bereitwillig annimmt.
- Die meisten automatischen Treffer liegen in übernommenem Fremdcode (`artemis/` von
  google/artemis) oder waren Fehlalarme.

| Schwere | Anzahl |
|---|---|
| Hoch | 1 |
| Mittel | 9 |
| Niedrig | 14 |

## Vorgehen

| Skill | Werkzeug | Umfang |
|---|---|---|
| implementing-secret-scanning-with-gitleaks | gitleaks 8.30.1 | alle 444 Commits, dazu sensible Dateinamen in der Historie |
| scanning-iac-and-images-with-trivy, generating-and-analyzing-sboms | trivy 0.76.1 | Lockfiles, `.venv`, Dockerfiles |
| implementing-semgrep-for-custom-sast-rules | semgrep 1.183.0 | eigene Regeln-Kopie (semgrep.dev ist gesperrt): Python, JS/TS, Bash, Java, Kotlin, Dockerfile, GitHub Actions, Secrets |
| securing-github-actions-workflows | Skill-Skript + Handprüfung | `.github/workflows/` |
| auditing-mcp-servers-for-tool-poisoning, securing-agentic-ai-tool-invocation | Handprüfung | `.mcp.json`, `.claude/settings.json`, Session-Hooks |
| detecting-malicious-npm-packages, detecting-typosquatting-packages-in-npm-pypi | guarddog 3.2.0 + PyPI/npm-Metadaten | `requirements.txt`, `telefon-assistent/requirements.txt`, `remotion-composer/package.json`, `rea-agents`, `graphifyy`, `pipecat-asterisk` |
| testing-for-broken-access-control, testing-api-authentication-weaknesses u. a. | Handprüfung, backlot lokal gestartet | `telefon-assistent/`, `bmw-cardata/`, `backlot/` |

Jeder Befund unten wurde am Code nachgeprüft. „Nicht live getestet“ heißt: Der Code
bzw. die Konfiguration ist so, das Verhalten wurde aber nicht gegen ein echtes System
ausprobiert.

## Hoch

### H1 – Abhängigkeiten mit bekannten Lücken

| Ort | Paket | Version | Höchste Schwere | Behoben in |
|---|---|---|---|---|
| `artemis/uv.lock` | pillow | 12.3.0 | kritisch (41 CVEs) | 13.0.0 |
| `artemis/uv.lock` | pyjwt | 2.13.0 | kritisch (15 CVEs) | 2.14.0 |
| `artemis/uv.lock` | certifi | 2026.7.22 | kritisch | 2026.10.18 |
| `artemis/uv.lock` | aiohttp, urllib3, tornado, filelock, virtualenv, pyasn1, langgraph-sdk | – | hoch | siehe `trivy` |
| Projekt-`.venv` (`requirements.txt`) | pillow | 12.3.0 | kritisch | 13.0.0 |
| Projekt-`.venv` | dnspython, wheel, jaraco.context | – | hoch | 2.9.0 / 0.46.2 / 6.1.0 |
| `remotion-composer/package-lock.json` | fast-uri, browserslist, source-map-js | – | hoch | 3.1.6 / 4.28.7 / 1.2.2 |
| `artemis/apps/showcase_ui/package-lock.json` | @angular/router | 22.1.4 | hoch | 22.2.0 |

Insgesamt: 7 kritische, 63 hohe, 56 mittlere CVEs. `requirements.txt` gibt nur
Mindestversionen an (`>=`), die tatsächlich installierte Version entscheidet.
Hinweis: dnspython 2.9.x setzt Python ≥ 3.11 voraus, die `.venv` läuft auf 3.10.

**Fix:** `uv lock --upgrade-package pillow --upgrade-package pyjwt …` in `artemis/`,
`npm update` bzw. `npm audit fix` in `remotion-composer/`, `.venv` neu aufbauen.

## Mittel

### M1 – Telefonassistent (PC): SIP-Anrufe mit gefälschtem Absender möglich
`telefon-assistent/asterisk/vorlagen/pjsip.conf:10, 29–49`, `docker-compose.yml` (`network_mode: host`)

Asterisk lauscht auf `0.0.0.0`. Der Endpunkt `fritzbox` hat kein `identify_by` und
keine `acl`; Asterisk erkennt Endpunkte standardmäßig auch am Benutzernamen. Ein Gerät
im selben Netz (im Café-WLAN jeder) kann ein `INVITE` mit `From: sip:<FRITZBOX_BENUTZER>@…`
schicken und Gespräche mit der KI starten: LLM-Kosten, gefälschte Anrufernummer im
Telegram-Bericht. Nach außen wählen kann der Kontext `von-fritzbox` nicht, Gebührenbetrug
ist also ausgeschlossen. Nicht live getestet.

**Fix:** am Endpunkt `identify_by=ip`, `acl` mit `deny=0.0.0.0/0.0.0.0` und
`permit=<FRITZ!Box-IP>`, Transport an die LAN-IP binden.

### M2 – Telefonassistent (Handy): SIP-Anfragen von beliebigen Absendern
`telefon-assistent/assistent/handy/sip.py:519–529`

`datagram_received` prüft nicht, ob die Anfrage von der FRITZ!Box kommt. Folgen wie M1;
bei abgeschalteten eingehenden Anrufen wächst `_eingehend_offen` ohne Grenze.
**Fix:** Anfragen verwerfen, wenn `adresse[0] != self.server`.

### M3 – Telefonassistent (Handy): RTP-Ton kann umgeleitet werden
`telefon-assistent/assistent/handy/sip.py:220–221`

Jedes gültige RTP-Paket von irgendwoher setzt das Ziel neu. Ein Angreifer im LAN kann
das Gespräch mithören und eigene Sprache einspeisen (Prompt-Injection per Ton).
**Fix:** Ziel aus dem SDP übernehmen oder nach dem ersten Paket festhalten.

### M4 – Telefonassistent: Sperrliste für teure Nummern hat Lücken
`telefon-assistent/assistent/telefonbuch.py:10–22`

Nicht gesperrt: Call-by-Call-Vorwahlen `010xx` (damit z. B. `01088 0043…` oder
`01088 0900…`), `012x`, `0181–0189`, `0191–0194`. Ob die FRITZ!Box Call-by-Call über
SIP ausführt, ist unklar. Vor jedem Anruf steht ein Bestätigungsknopf mit der Nummer,
das begrenzt das Risiko deutlich.
**Fix:** Positivliste statt Sperrliste; zusätzlich Wahlregeln in der FRITZ!Box für das
IP-Telefon (Ausland, Sonderrufnummern).

### M5 – Artemis: Befehlsinjektion im Script-Notifier (Fremdcode)
`artemis/mcp_server/notifiers/script.py:69–81`

Ist ein Benachrichtigungsbefehl per Umgebungsvariable gesetzt, ersetzt Artemis
`{message}` usw. per String-Ersetzung und führt das Ergebnis mit `shell=True` aus. Die
Nachricht stammt aus dem Agenten-Ergebnis und kann über Bildschirminhalte des
Android-Geräts beeinflusst werden; `"; befehl; "` im Text läuft dann als Shell-Befehl.
Nur relevant, wenn der Script-Notifier eingeschaltet ist.
**Fix:** jeden Wert mit `shlex.quote` einsetzen oder `shlex.split` + `shell=False`.

### M6 – backlot: Fremde Webseiten können Projektdaten lesen (DNS-Rebinding)
`backlot/server.py` (ab Zeile 165), `backlot/__main__.py:85`

Kein Host-Header-Check, keine Anmeldung, fester Port 4750. Eine präparierte Webseite
kann ihre Domain auf 127.0.0.1 umbiegen und `/api/projects`, Projektzustände und Medien
auslesen. Getestet: `Host: evil.example` wird mit 200 beantwortet.
**Fix:** `TrustedHostMiddleware(allowed_hosts=["127.0.0.1", "localhost"])`.

### M7 – backlot: HTML/SVG aus Projekten werden ausführbar ausgeliefert
`backlot/server.py:245–276`

`/media` und `/thumb` liefern `.html` als `text/html` und `.svg` mit Skript aus, ohne
CSP und `nosniff`. Ein heruntergeladenes oder generiertes Asset mit Skript kann alle
Projekte lesen. Getestet.
**Fix:** erlaubte Endungen festlegen, `Content-Security-Policy: sandbox`,
`X-Content-Type-Options: nosniff`, sonst `Content-Disposition: attachment`.

### M8 – Artemis-Playground: XSS und offenes CORS (Fremdcode, nur bei Deployment)
`artemis/playground/backend_manager/app/static/app.js:296`, `app/main.py:50–56`, `app/config.py:24`

Agenten-Nachrichten aus dem Event-Stream gehen ungefiltert in `innerHTML` (Zeile 226 →
296); CORS erlaubt jede Herkunft mit Credentials; der Server lauscht auf `0.0.0.0`.
Betrifft nur, wer den Playground (`deploy_to_cos.sh`) wirklich betreibt.
**Fix:** `textContent` statt `innerHTML`, Origins einschränken.

### M9 – Session-Hooks laden ungepinnten Fremdcode
`.claude/hooks/session-start.sh`, `.claude/settings.json`

Jede Cloud-Session klont `garrytan/gstack` auf dem jeweils neuesten Stand und führt
`./setup` aus, installiert `graphifyy` ohne Version, und das Plugin `ponytail` kommt
ungepinnt aus `DietrichGebert/ponytail`. Wird eines dieser Projekte kompromittiert,
läuft der Code mit vollen Rechten in deinen Sessions (dort liegt z. B. dein
GitHub-Zugriff). Geprüft: `graphifyy` ist das echte Paket (Projekt-URLs zeigen auf
Graphify-Labs/graphify), kein Typosquatting.
**Fix:** gstack auf einen Commit pinnen (`git checkout <sha>`), `graphifyy==<version>`.

## Niedrig

| # | Ort | Befund | Fix |
|---|---|---|---|
| N1 | `telefon-assistent/assistent/gemini.py:133`, `anrufe.py:238` | Gemini-Schlüssel steht in der URL; bei Verbindungsfehlern landet er womöglich im Log und im Telegram-Chat (unsicher) | Header `x-goog-api-key` |
| N2 | `telefon-assistent` Gesprächs-Prompts | Angerufene können per Gespräch Auftrag, Spielraum und Rückrufnummer herauslocken; Wählen ist nicht möglich | Prompt: Anweisungen der Gegenseite ignorieren, Spielraum nicht nennen |
| N3 | `telefon-assistent` | Kein Limit für eingehende Anrufe pro Nummer/Tag | Tageslimit |
| N4 | `telefon-assistent/einrichten-handy.sh:72–77` | Übernimmt die letzte Chat-ID, die dem Bot schreibt | ID anzeigen und bestätigen lassen |
| N5 | `telefon-assistent/assistent/telegram_bot.py:70–72` | Berechtigung je Chat, nicht je Person (Gruppen!) | zusätzlich `effective_user.id` prüfen |
| N6 | `telefon-assistent/assistent/gespraech.py:221–239` | PC-Version legt bei hängender Pipeline nicht hart auf | `TIMEOUT(absolute)` im Wählplan |
| N7 | `telefon-assistent/assistent/konfig.py:56` | Erzeugt `asterisk/etc/pjsip.conf` (nicht im Repo, per `.gitignore` ausgeschlossen) mit dem FRITZ!Box-Kennwort im Klartext per `write_text`, also mit Standardrechten (meist für alle lesbar) | Datei mit Rechten 600 anlegen |
| N8 | 5 Dockerfiles (`telefon-assistent/`, `artemis/…`) | Container laufen als root | `USER` setzen |
| N9 | `.github/workflows/*.yml` | Actions nur per Tag gepinnt; bmw-Workflow installiert pip-Pakete ohne Version/Hash, `persist-credentials` Standard | SHA-Pinning, `--require-hashes`, `persist-credentials: false` |
| N10 | `bmw-cardata/report.py:102–104`, `cli.py:105, 140` | Steuerzeichen aus API-Antworten gehen ungefiltert ans Terminal | `printable()` anwenden |
| N11 | `bmw-cardata` (`verlauf.jsonl`, CSV-Export, Absturzprotokoll) | Standortverlauf ohne Löschfrist; Exporte mit Standardrechten (DSGVO) | Aufbewahrungsfrist, Rechte 600 |
| N12 | `backlot/server.py` | Ohne Anmeldung: andere lokale Benutzer können mitlesen | Token |
| N13 | `artemis/packages/artemis-accessibility-helper/debug.keystore` | Android-Debug-Schlüssel im Repo (Standardkennwort `android`) | nur für Debug-Builds nutzen |
| N14 | `.mcp.json` | `rea` lädt per `npx` 42 Abhängigkeiten ohne Lockfile; `skyaccess` ist ein fremder Remote-Server, dessen Tool-Beschreibungen sich jederzeit ändern können (von hier nicht abrufbar, Proxy sperrt) | rea lokal mit Lockfile installieren; `request_booking` nur auf ausdrücklichen Wunsch (steht schon in CLAUDE.md) |

## Kein Sicherheitsbefund, aber wichtig

- **CI läuft nie:** `.github/workflows/ci.yml` startet nur für `main`, den es nicht
  gibt (Standardbranch ist `claude/gstack-skill-setup-c85bwb`). Pull Requests werden
  deshalb nicht getestet.

## Fehlalarme (geprüft und verworfen)

- gitleaks: alle 12 eigenen Treffer sind Beispiele/Platzhalter (BMW-i-Remote-README,
  Test-Dummies, `YOUR_API_KEY`, Modellname). Kein Secret wurde je wieder entfernt.
- `.env.example`, `artemis/.env.example`, `telefon-assistent/.env.beispiel`: nur leere Werte/Platzhalter.
- Semgrep SQL (`artemis/…/storage.py:1102, 1191`, `blackboard.py:160`): feste Tabellen-/Spaltennamen.
- Semgrep `os.execv` (`artemis/apps/admin_console/routers/system.py:575`): Neustart mit eigenen Argumenten, nur von localhost.
- Semgrep `unencrypted-socket` (`CommandServer.java:61`): bindet an 127.0.0.1 und verlangt ein Token.
- Semgrep MD5 (`telefon-assistent/assistent/handy/sip.py:50`): SIP-Digest nach RFC 2617, von der FRITZ!Box vorgegeben.
- Semgrep `urlopen` (`scripts/backlot_*.py`): feste URL `http://127.0.0.1:<Konstante>`.
- guarddog: nur heuristische „capability“-Treffer bei bekannten Paketen.
  `pipecat-asterisk 0.1.4` (kleines Paket) von Hand gelesen: 1.177 Zeilen, nur
  WebSocket-Transport, kein Netz-/Prozess-/Umgebungszugriff außerhalb des Zwecks.

## Was in Ordnung ist

- **Telefonassistent:** Alle Telegram-Handler prüfen die Chat-ID; leere ID sperrt alles.
  Nummern werden auf Ziffern reduziert (keine Einschleusung), Notrufe/0900/Ausland
  gesperrt, jeder Anruf braucht Bestätigung. ARI nur auf 127.0.0.1 mit Kennwort, kein
  `shell=True`, kein `verify=False`, Timeouts gesetzt, `.env` mit `chmod 600`.
  Gesprächsdauer wird durchgesetzt.
- **bmw-cardata:** Tokens außerhalb des Repos (`~/.config/bmw-cardata/state.json`, 600/700,
  atomar geschrieben), PKCE S256, Tokens werden aus Fehlermeldungen gefiltert, TLS geprüft,
  Eingaben per Regex validiert, CSV-Formel-Injection abgefangen.
- **backlot:** nur 127.0.0.1, Pfad-Traversal in 11 Varianten getestet und blockiert,
  Oberfläche nutzt `textContent`, ffmpeg ohne Shell.
- **Workflows:** `permissions: contents: read`, keine Secrets, keine Script-Injection.

## Nicht geprüft

- Tiefenprüfung des übrigen Fremdcodes (`artemis/`, `mimic/`, `open-higgsfield-ai/`,
  `.agents/`, `BMW-i-Remote/`) über die automatischen Scans hinaus.
- `rea-agents` (guarddog-Analyse scheiterte an der Sandbox) und der Remote-Server `skyaccess`.
- Laufzeittests gegen echte Geräte (FRITZ!Box, Android, BMW-API).
- OSV- und Grype-Datenbank (Proxy gesperrt); Trivy deckt dieselben Quellen weitgehend ab.
