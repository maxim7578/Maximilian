# Project NOMAD – Übersicht

Kopie von [Crosstalk-Solutions/project-nomad](https://github.com/Crosstalk-Solutions/project-nomad)
(Apache 2.0, © Crosstalk Solutions, LLC; Lizenz in [`LICENSE`](LICENSE)).

- **Stand:** Version 1.35.1, Upstream-Commit `54ee30a` vom 05.10.2026
- **Übernommen am:** 01.11.2026
- **Nicht dabei:** die Git-Historie (nur dieser eine Stand)
- **Eigene Änderungen:** nur Paket-Updates, siehe [Abschnitt unten](#eigene-änderungen-paket-updates-vom-01112026)

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
| `admin/` | Command Center: AdonisJS 6 (TypeScript), Inertia + React 19, Tailwind 4, MySQL (Lucid), Redis + BullMQ für Hintergrundjobs, `dockerode` zur Container-Steuerung |
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
  bekannte Schwachstellen (3 kritisch, 29 hoch). Nach den Updates unten sind
  es 36, alle „mittel“ (Details dort).
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

**Nicht geprüft:** Docker-Image-Build, Start der ganzen App, Daten-Import mit
`@openzim/libzim` 4.7.0 und das Kartenbild mit echten Offline-Karten.

**Bewusst nicht aktualisiert (36 mittlere Meldungen):**

- AdonisJS 6 → 7 (`@adonisjs/core` und Zubehör): Open Redirect und ReDoS in
  `@adonisjs/http-server`; braucht eine größere Migration.
- `stream-json` 1 → 3: komplett neue API, betrifft den Medikamenten-Datenimport.
- ESLint-Werkzeuge (`minimatch`): nur Entwicklungswerkzeuge.

## Aktualisieren

Neuen Stand holen und diesen Ordner ersetzen (`UEBERSICHT.md` vorher sichern;
die Paket-Updates oben ggf. neu anwenden):

```bash
git clone --depth 1 https://github.com/Crosstalk-Solutions/project-nomad /tmp/nomad-neu
```

Danach Version und Commit oben in dieser Datei anpassen.
