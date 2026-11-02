# Project NOMAD – Übersicht

Kopie von [Crosstalk-Solutions/project-nomad](https://github.com/Crosstalk-Solutions/project-nomad)
(Apache 2.0, © Crosstalk Solutions, LLC; Lizenz in [`LICENSE`](LICENSE)).

- **Stand:** Version 1.35.1, Upstream-Commit `54ee30a` vom 05.10.2026
- **Übernommen am:** 01.11.2026
- **Nicht dabei:** die Git-Historie (nur dieser eine Stand)
- **Eigene Änderungen:** Paket-Updates und Migration auf AdonisJS 7, siehe
  [Paket-Updates](#eigene-änderungen-paket-updates-vom-01112026) und
  [AdonisJS-7-Migration](#eigene-änderungen-migration-auf-adonisjs-7-vom-01112026),
  außerdem [Sprachumschaltung Deutsch/Englisch](#eigene-änderungen-sprachumschaltung-deutschenglisch-vom-02112026)

## Was es ist

Ein offline nutzbarer Wissens- und Lernserver. Nach der Installation
erreicht man im Browser unter `http://<gerät>:8080` das „Command Center“. Darüber
installiert und verwaltet man Inhalte und Apps:

- **Wissen:** Wikipedia und andere ZIM-Archive (Kiwix), Kolibri-Lernkurse,
  Offline-Karten (MapLibre/PMTiles), medizinische Nachschlagedaten
- **KI-Assistent:** Ollama (lokale Sprachmodelle) und Qdrant (Vektorsuche für
  Fragen zu eigenen Dokumenten)
- **App-Katalog „Supply Depot“:** u. a. CyberChef, Stirling PDF, Filebrowser,
  Calibre-Web, IT-Tools, Excalidraw, Homebox, Vaultwarden, Jellyfin, Meshtastic,
  dazu eigene Docker-Container

Installiert wird auf Debian/Ubuntu (empfohlen: Ubuntu 26.04 LTS) mit
`install/install_nomad.sh`. NOMAD selbst braucht etwa 5 GB Speicher und unter
1 GB RAM; Inhalte und KI brauchen deutlich mehr.

## Aufbau

| Teil | Inhalt |
|------|--------|
| `admin/` | Command Center: AdonisJS 7 (TypeScript, Node.js 24), Inertia 3 + React 19, Vite 8, Tailwind 4, MySQL (Lucid), Redis + BullMQ für Hintergrundjobs, `dockerode` zur Container-Steuerung |
| `admin/app/services/` | 37 Dienste, u. a. Docker, Downloads, ZIM/Kiwix, Karten, Ollama, RAG, Benchmark, Updates |
| `admin/start/routes.ts` | 178 Routen (Weboberfläche und API) |
| `install/` | Installations-, Start-, Stopp-, Update- und Deinstallationsskripte, `management_compose.yaml`, Sidecars (Updater, Disk-Collector, Übersetzungs-Proxy) |
| `collections/` | JSON-Kataloge der Inhalte (Wikipedia-Pakete, Karten, Kiwix-Kategorien, Heilmittel) |
| `Dockerfile` | Image des Command Centers |
| `.github/workflows/` | Image-Builds, Releases, Prüfung der Sammlungs-URLs |

Laufende Container laut `install/management_compose.yaml`: `admin`, `mysql`,
`redis`, `dozzle` (Logs, Port 9999), `updater` und `disk-collector`.

## Sicherheitshinweise

- **Keine Anmeldung:** Wer Port 8080 erreicht, hat volle Kontrolle. Das ist
  laut Upstream Absicht (README und `SECURITY.md`). Der `admin`-Container hat
  Zugriff auf den Docker-Socket des Rechners. Wer das Command Center bedienen
  kann, kann also Container mit Zugriff auf Teile des Host-Dateisystems
  starten. NOMAD gehört deshalb nur in ein vertrauenswürdiges Netz und nie
  direkt ins Internet.
- **Dozzle auf Port 9999** zeigt alle Container-Logs, ebenfalls ohne Anmeldung.
- **Abhängigkeiten:** Upstream-Stand 1.35.1 hatte laut `npm audit` 84
  bekannte Schwachstellen (3 kritisch, 29 hoch). Nach den Updates und der
  AdonisJS-7-Migration unten sind keine kritischen oder hohen mehr übrig
  (Details dort).
- **Fest eingebauter Schlüssel:** `BENCHMARK_HMAC_SECRET` in
  `admin/app/services/benchmark_service.ts` ist öffentlich und laut Upstream
  bewusst so; er schützt nur die Benchmark-Rangliste.

Sicherheitslücken bitte nicht öffentlich melden, sondern privat über den
[Security-Tab des Upstream-Repos](https://github.com/Crosstalk-Solutions/project-nomad/security).

## Eigene Änderungen: Paket-Updates vom 01.11.2026

Alles in `admin/`. `npm audit`: vorher 84 Meldungen (3 kritisch, 29 hoch,
46 mittel, 6 niedrig), nachher 36 (alle mittel).

| Paket | Vorher | Nachher | Hinweis |
|-------|--------|---------|---------|
| `maplibre-gl` | 4.7.1 | 6.16.0 | Hauptversion; behebt kritische XSS-Lücke |
| `react-map-gl` | 8.1.0 | 8.1.3 | unterstützt maplibre 6 |
| `sharp` | 0.34.5 | 0.35.5 | Hauptversion (0.x); Lücken in libvips/libheif |
| `tar` | 7.5.16 | 7.5.22 | kritisch (DoS) |
| `axios` | 1.18.1 | 1.21.0 | u. a. SSRF |
| `systeminformation` | 5.31.7 | 5.33.19 | Command Injection |
| `vite` | 6.4.3 | 6.4.5 | |
| `postcss`, `compression`, `mysql2`, `yauzl`, `@openzim/libzim`, `@scalar/api-reference`, `@adonisjs/prettier-config` | | neueste passende Version | |
| `@faker-js/faker` | 9.9.0 | 10.5.0 | per `overrides`, kommt nur über `@adonisjs/lucid`, wird im Code nicht genutzt |
| indirekte Pakete | | | `npm audit fix`: u. a. `undici`, `proxy-addr`, `@xmldom/xmldom`, `form-data`, `follow-redirects`, `qs` |

**Codeänderung:** `admin/inertia/components/maps/MapComponent.tsx`.
maplibre-gl 6 hat keinen Default-Export mehr
(`import * as maplibregl from 'maplibre-gl'`) und braucht unter Vite
`setWorkerUrl(...)` mit `?worker&url`. Ohne diesen Aufruf bleibt die Karte
leer („Worker failed to load“, 404 auf `maplibre-gl-worker.mjs`).

**Geprüft:**

- Backend-Typecheck (`tsc --noEmit`): fehlerfrei.
- Frontend-Typecheck: dieselben 35 Fehler wie im Upstream-Stand, keine neuen.
- `vite build` läuft durch, der Worker wird mitgebaut.
- Eine Karten-Testseite in Headless-Chromium rendert mit der Korrektur und
  scheitert ohne sie.
- Unit-Tests: 599 von 609 bestanden, vor und nach dem Update identisch. Die
  10 Fehler liegen am nicht kompilierten nativen Modul `@openzim/libzim`
  (Installation ohne Install-Skripte), nicht an den Updates.
- sharp-Bildtests (`tests/unit/chat_images.spec.ts`, laufen nicht in
  `test:unit` mit): 10 von 10 bestanden.

**Nicht geprüft:** Docker-Image-Build, Daten-Import mit `@openzim/libzim`
4.7.0 und das Kartenbild mit echten Offline-Karten. (Der App-Start wurde bei
der AdonisJS-7-Migration unten geprüft.)

**Bewusst nicht aktualisiert (36 mittlere Meldungen):**

- AdonisJS 6 → 7: inzwischen erledigt, siehe nächster Abschnitt.
- `stream-json` 1 → 3: komplett neue API, betrifft den Medikamenten-Datenimport.
- ESLint-Werkzeuge (`minimatch`): nur Entwicklungswerkzeuge.

## Eigene Änderungen: Migration auf AdonisJS 7 vom 01.11.2026

Nach der offiziellen Anleitung
([adonisjs/v7-docs](https://github.com/adonisjs/v7-docs/blob/main/content/start/resources/upgrade_guide.md))
und dem offiziellen Starter-Kit `inertia-react`.

**Plattform:** Node.js 24 statt 22 (`Dockerfile`: `node:24-slim`,
`package.json`: `engines`), Vite 8 statt 6, Inertia 3 statt 2, TypeScript 5.9.

**Pakete:** alle `@adonisjs/*` auf die v7-Linie (`core` 7.6.0, `lucid` 22.4.2,
`inertia` 5.0.5, `vite` 6.0.4, `transmit` 3.0.2, `session` 8.3.0, `shield`
9.0.0, `cors` 3.0.0, `static` 2.0.1, `auth` 10.1.0, `assembler` 8.6.0), dazu
`@inertiajs/react` 3.10.0, `@tuyau/core`, `@poppinss/ts-exec` (ersetzt
`ts-node-maintained`), `youch`, `@japa/runner` 5, `@vitejs/plugin-react` 6,
Tailwind 4.3.3. Die Lockfile wurde dafür neu aufgelöst.

`npm audit`: 40 Meldungen (39 mittel, 1 niedrig), keine kritischen oder hohen.
Die AdonisJS-Lücken selbst (Open Redirect, ReDoS) sind mit
`@adonisjs/http-server` 9.3.1 behoben. Übrig sind Meldungen, die über
`minimatch` (nur Build- und Lint-Werkzeuge) vererbt werden, `stream-json` und
`deepmerge` (niedrig).

**Umstellungen nach der Anleitung:**

- `adonisrc.ts`: neue Hooks (`indexEntities`, `indexPages`, `generateRegistry`,
  `buildStarting`), Test-Glob `*.spec.{ts,js}`, `assetsBundler` und die
  experimentellen Flags entfernt (jetzt Standard).
- `config/encryption.ts` neu mit `legacy`-Treiber, damit mit v6 verschlüsselte
  Werte lesbar bleiben; `appKey` aus `config/app.ts` entfernt.
- `config/inertia.ts`: `sharedData` ersetzt durch
  `app/middleware/inertia_middleware.ts`; der Cache für den Namen des
  KI-Assistenten liegt jetzt in `app/utils/assistant_name.ts`.
- `inertia/app/app.tsx` → `inertia/app.tsx`; Inertia-Vite-Plugin entfernt;
  Layout mit `data-inertia`; `ace.js` und Test-Skripte nutzen `@poppinss/ts-exec`.
- `package.json`: Aliase `#generated/*` und `#transformers/*`.
- Generierte Typdateien in `.adonisjs/` (wie im Starter-Kit eingecheckt;
  `node ace build` und `node ace serve` erzeugen sie neu).
- `inertia.render()` ist jetzt typisiert und verlangt immer Props; Seiten ohne
  Props bekommen `{}`.

**Zusätzlich nötige Korrekturen (beim Testen gefunden):**

- `vite.config.ts`: `resolve.dedupe: ['react', 'react-dom']`. Ohne das landet
  die React-18-Kopie von `react-adonis-transmit` im Bundle und keine Seite
  rendert („Cannot read properties of null (reading 'useRef')“).
  `@vitejs/plugin-react` 4 hatte das automatisch gemacht.
- Tailwind 4.3.3: ältere Versionen registrieren einen asynchronen ESM-Loader,
  der zusammen mit `@poppinss/ts-exec` danach geladene TypeScript-Module leer
  zurückgibt. Das brach `node ace test` und den Entwicklungsmodus.
- `config/transmit.ts`: Import aus `@adonisjs/transmit/transports/redis`, weil
  der Sammel-Export auch den MQTT-Transport lädt (Paket `mqtt` fehlt).
- `config/database.ts`: `schemaGeneration` aus; Lucid 22 würde sonst bei jedem
  `migration:run` (also bei jedem Containerstart) `database/schema.ts` schreiben.
- `app/exceptions/handler.ts`: Fehlerseiten bekommen nur `{ name, message }`.
  Inertia 5 kann Fehlerobjekte mit Zirkelbezügen (z. B. von axios) nicht
  serialisieren; außerdem landet der Stacktrace nicht mehr im Browser.
- `inertia/lib/icons.ts`: doppelte Importe entfernt (Vite 8 bricht sonst ab).
- `settings/update`: der Controller liefert jetzt `earlyAccess` mit, das die
  Seite erwartet (von der neuen Typprüfung gefunden; vorher `undefined`).
- `tsconfig.json` ohne `references`/`tsconfig.inertia.json` aus der
  Anleitung: Die Referenz verursachte 28 Fehler in Tests, die Hilfsdateien aus
  `inertia/lib` importieren, und hätte den Build gestoppt; die Typprüfung von
  `render()` funktioniert auch ohne.

**Geprüft (Node 24, MariaDB 10.11, Redis; v6 und v7 jeweils gebaut und parallel
gestartet):**

- Backend-Typecheck fehlerfrei; Frontend-Typecheck 36 Fehler (Upstream 35:
  6 alte behoben, 7 neue durch die strengere Props-Prüfung, siehe unten).
- `node ace build` (Codegen, Vite, `tsc`) erfolgreich; Migrationen und Seeds laufen.
- 23 Seiten: gleiche Statuscodes und Komponenten wie v6; 13 davon im
  Headless-Browser gerendert: gleiche Titel und Inhalte, keine JS-Fehler,
  Navigation per Inertia-Link funktioniert. Auch im Entwicklungsmodus
  (`node ace serve`).
- 56 API-Endpunkte: 51 identisch; 4 liefern bei Fehlern jetzt JSON statt
  HTML (dokumentierte v7-Änderung), 1 Abweichung durch die neuere
  `systeminformation`-Version.
- Schreibzugriff (Einstellung ändern), Namens-Cache, Transmit-Livekanal.
- Unit-Tests (`node --test`): 599/609 wie vorher; Japa-Tests: funktional 2/2,
  Unit 76/80 wie in v6 (die 4 Fehler kommen von meiner Testumgebung).

Für den Test wurde `@openzim/libzim` durch ein Test-Double ersetzt, weil das
Kompilieren des nativen Moduls hier nicht erlaubt war. ZIM-Funktionen sind
deshalb nicht geprüft, ebenso wenig der Docker-Image-Build.

**Bekannte Restpunkte:**

- `@boringnode/transmit` 0.4.2 abonniert seinen Redis-Kanal ohne
  Fehlerbehandlung. Endet die App, bevor Redis bereit ist (z. B. sehr kurze
  Testläufe), gibt es eine unbehandelte Ablehnung „Connection is closed“;
  Japa meldet dann Exit-Code 1, obwohl alle Tests bestehen.
- Die 7 neuen Meldungen im Frontend-Typecheck: Seiten-Props mit
  `interface`-Typen (u. a. aus `types/*.ts` und `systeminformation`) sind für
  die JSON-Prüfung von Inertia 5 nicht zulässig. Laufzeit und Build sind nicht
  betroffen; sauber lösbar über AdonisJS-Transformer.
- Fehlt `.adonisjs/` oder ist es veraltet (z. B. nach neuen Seiten), vor dem
  Typecheck `node ace codegen` ausführen.

## Eigene Änderungen: Sprachumschaltung Deutsch/Englisch vom 02.11.2026

Die Oberfläche des Command Centers gibt es auf Deutsch und Englisch.
Umschalter „DE | EN“ neben dem Tag-/Nachtmodus (Fußzeile und Seitenleiste der
Einstellungen); die Wahl gilt sofort, ohne Neuladen, und wird im Browser
gespeichert (`localStorage`, Schlüssel `nomad:language`). Ohne gespeicherte
Wahl gilt die Browsersprache, sonst Englisch.

**Technik:** `i18next` 26.5.2 und `react-i18next` 17.1.0.

- `inertia/i18n/`: Einrichtung, `setLanguage`, `formatNumber`, `formatDate`,
  `formatDateTime`; Zahlen und Datumsangaben folgen der gewählten Sprache.
- `inertia/locales/<sprache>/<namensraum>.json`: 14 Namensräume mit zusammen
  1713 Texten je Sprache.
- Schlüssel stehen immer mit Namensraum im Code (`t('apps:…')`). Module, die
  Node-Tests importieren, markieren Schlüssel mit `tk('…')` und die Komponente
  übersetzt sie.
- Eine neue Sprache braucht nur einen weiteren Ordner unter `locales/` und einen
  Eintrag in `inertia/i18n/language.ts`.

**Tests (deutsch):**

- `tests/unit/i18n_locales.spec.ts` prüft gleiche Namensräume, Schlüssel und
  Platzhalter in allen Sprachen, keine leeren Texte, und dass jeder im Code
  verwendete Schlüssel existiert.
- `tests/unit/i18n_language.spec.ts` prüft die Sprachwahl.
- Die Tests zu `chat_stream`, `vision_guidance` und `kb_file_grouping` prüfen
  jetzt Schlüssel statt englischer Texte.

**Geprüft:**

- 18 Seiten wurden im Headless-Browser in beiden Sprachen geöffnet: kein
  JS-Fehler, richtiges `lang`-Attribut, übersetzte Titel.
- Umschalten per Klick ohne Neuladen und Merken nach dem Neuladen funktionieren.
- Unit-Tests wie vorher plus die neuen. Backend-Typecheck fehlerfrei; der
  Frontend-Typecheck hat 32 statt 36 Fehler (siehe unten).

**Nebenbei behoben:** `ChatInterface` rief `addNotification` auf, ohne es zu
definieren. Fehler bei Bildanhängen hätten den Chat abstürzen lassen
(Upstream-Fehler).

**Bleibt Englisch (bewusst oder noch offen):**

- Inhalte und Daten vom Server: Beschreibungen von Apps, Modellen,
  Wikipedia-Paketen und Kategorien, medizinische Daten (FDA), Länder- und
  Kartennamen, Dokumentation.
- Meldungen, die der Server erzeugt: API-Fehlertexte, Status von Hintergrundjobs
  und Updates.
- Eigennamen wie Project NOMAD, Command Center, Supply Depot, NOMAD Score und
  Creator Packs.
- Der Text der Apache-Lizenz und Copyright-Zeilen auf der Seite „Rechtliche
  Hinweise“. Datenschutzhinweis und Haftungsausschlüsse sind übersetzt.
- Eingebaute Texte von Fremdbibliotheken: Upload-Feld (Uppy) und Kartenknöpfe
  (MapLibre, z. B. „Zoom in“).
- Der Debug-Bericht für GitHub-Issues.
- Fehlermeldungen, die schon im Chat stehen, bleiben nach einem Sprachwechsel
  in der alten Sprache.
- Die vorgegebene NOMAD.md-Vorlage ist auf Deutsch, wenn Deutsch eingestellt ist.

**Zur fachlichen Durchsicht empfohlen:** die deutschen Überschriften der
FDA-Packungsbeilagen und die Sicherheitshinweise auf den Medizin-Seiten.

## Aktualisieren

Neuen Stand holen und diesen Ordner ersetzen (`UEBERSICHT.md` vorher sichern;
die eigenen Änderungen oben ggf. neu anwenden):

```bash
git clone --depth 1 https://github.com/Crosstalk-Solutions/project-nomad /tmp/nomad-neu
```

Danach Version und Commit oben in dieser Datei anpassen.
