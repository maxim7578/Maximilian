# Project NOMAD – Übersicht

Kopie von [Crosstalk-Solutions/project-nomad](https://github.com/Crosstalk-Solutions/project-nomad)
(Apache 2.0, © Crosstalk Solutions, LLC; Lizenz in [`LICENSE`](LICENSE)).

- **Stand:** Version 1.35.1, Upstream-Commit `54ee30a` vom 05.10.2026
- **Übernommen am:** 01.11.2026, ohne Änderungen am Upstream-Code
- **Nicht dabei:** die Git-Historie (nur dieser eine Stand)

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
- **Abhängigkeiten:** Ein trivy-Scan von `admin/package-lock.json` (01.11.2026)
  fand 135 bekannte Schwachstellen in npm-Paketen (3 kritisch, 59 hoch,
  61 mittel, 12 niedrig), u. a. in `undici`, `axios`, `@xmldom/xmldom`, `tar`,
  `maplibre-gl` und `proxy-addr`. Für alle gibt es neuere Versionen.
- **Fest eingebauter Schlüssel:** `BENCHMARK_HMAC_SECRET` in
  `admin/app/services/benchmark_service.ts` ist öffentlich und laut Upstream
  bewusst so; er schützt nur die Benchmark-Rangliste.

Sicherheitslücken bitte nicht öffentlich melden, sondern privat über den
[Security-Tab des Upstream-Repos](https://github.com/Crosstalk-Solutions/project-nomad/security).

## Aktualisieren

Neuen Stand holen und diesen Ordner ersetzen (`UEBERSICHT.md` vorher sichern):

```bash
git clone --depth 1 https://github.com/Crosstalk-Solutions/project-nomad /tmp/nomad-neu
```

Danach Version und Commit oben in dieser Datei anpassen.
