// Updates ohne Neuinstallation (nur in der Android-App).
// Beim Start prüft die App eine kleine JSON-Datei im GitHub-Release
// "vakovin-latest". Gibt es eine neuere Version, lädt sie das Paket im
// Hintergrund und aktiviert es beim nächsten Öffnen der App.
import { Capacitor } from "@capacitor/core";
import { CapacitorUpdater } from "@capgo/capacitor-updater";

const MANIFEST_URL =
  "https://github.com/maxim7578/Maximilian/releases/download/vakovin-latest/update.json";

// Versionsnummer dieses Builds (GitHub-Laufnummer, beim Bauen gesetzt).
const BUILT_VERSION: string = import.meta.env["VITE_APP_VERSION"] ?? "0";

interface Manifest {
  version: string;
  url: string;
}

function isNewer(candidate: string, running: string): boolean {
  const a = Number(candidate);
  const b = Number(running);
  if (Number.isFinite(a) && Number.isFinite(b)) return a > b;
  return candidate !== running;
}

export async function checkForAppUpdate(): Promise<void> {
  if (!Capacitor.isNativePlatform()) return;
  try {
    // Meldet, dass diese Version sauber gestartet ist (sonst setzt der
    // Updater nach einem fehlerhaften Update automatisch zurück).
    await CapacitorUpdater.notifyAppReady();

    const res = await fetch(`${MANIFEST_URL}?t=${Date.now()}`, { cache: "no-store" });
    if (!res.ok) return;
    const manifest = (await res.json()) as Partial<Manifest>;
    if (!manifest.version || !manifest.url) return;

    const current = await CapacitorUpdater.current();
    const running =
      current.bundle.version === "builtin" ? BUILT_VERSION : current.bundle.version;
    if (!isNewer(manifest.version, running)) return;

    const { bundles } = await CapacitorUpdater.list();
    const ready = bundles.find(
      (b) => b.version === manifest.version && b.status === "success",
    );
    const bundle =
      ready ?? (await CapacitorUpdater.download({ url: manifest.url, version: manifest.version }));
    await CapacitorUpdater.next({ id: bundle.id });
  } catch {
    // Kein Netz oder kein Update verfügbar: die App läuft mit der aktuellen Version weiter.
  }
}
