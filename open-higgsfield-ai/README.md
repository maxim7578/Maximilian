# Open Higgsfield AI – Korrekturen

Patches für [Autom8AI/open-higgsfield-ai](https://github.com/Autom8AI/open-higgsfield-ai),
erstellt auf Basis von Commit `b578108` („Merge pull request #58 …“).

## Inhalt

| Patch | Was er ändert |
|---|---|
| `0001-fix-restore-Vite-Electron-desktop-build-…` | Repariert den Desktop-Build (Vite/Electron) und spielt die nicht-brechenden Sicherheitsupdates ein (`npm audit fix`, u. a. Next.js 15.5.14 → 15.5.27). |
| `0002-chore-upgrade-electron-to-44-…` | Hebt Electron von 33 auf 44 und electron-builder von 25 auf 26. Damit ist die kritische Sicherheitslücke behoben. |

### Was im Original kaputt war

1. `vite.config.js` konnte `@tailwindcss/vite` nicht laden (Paket gibt es nur als ES-Modul) → umbenannt in `vite.config.mjs`.
2. Die Next-Web-App nutzt Tailwind v3, die Desktop-App (`src/`) Tailwind v4. v4 ist jetzt zusätzlich als `tailwindcss-v4` installiert, Vite wird darauf umgeleitet.
3. `electron/main.js` war ein ES-Modul ohne passende Projekteinstellung und nicht als Startdatei eingetragen → `electron/main.mjs`, in `package.json` als `main` gesetzt.
4. `ImageStudio.js` rief eine nie geschriebene Funktion `createInlineInstructions` auf, wodurch das Image Studio in der Desktop-App leer blieb → Aufruf entfernt.

### Stand der Sicherheitsmeldungen (`npm audit`)

52 vorher (2 kritisch) → 22 nachher (keine kritisch; 12 mittel, 10 hoch). Die übrigen betreffen
fast nur Build-Werkzeuge (Vite, Tailwind v3, Babel, ESLint-Config); in den Laufzeit-Paketen
bleibt nur `postcss` innerhalb von Next.js.

## Anwenden

```bash
git clone https://github.com/Autom8AI/open-higgsfield-ai
cd open-higgsfield-ai
git checkout b578108
git am /pfad/zu/Maximilian/open-higgsfield-ai/*.patch
npm run setup
```

Danach:

- Web-App: `npm run dev` (oder `npm run build && npm start`), dann http://localhost:3000
- Desktop-App: `npm run electron:build` (macOS), `npm run electron:build:win` (Windows)

## Getestet (Linux, Node 22)

- `npm run setup`, `npm run build`, `npm run vite:build`: erfolgreich
- Web-App im Browser: API-Key-Seite und alle vier Studios (Image, Video, Lip Sync, Cinema) ohne Fehler
- Desktop-App mit Electron 44, als Linux-Paket gebaut und gestartet: alle vier Studios ohne Fehler

Nicht getestet: echte Bild-/Video-Erzeugung (braucht einen Muapi.ai-API-Key) sowie die
macOS- und Windows-Installer (lassen sich unter Linux nicht bauen).
