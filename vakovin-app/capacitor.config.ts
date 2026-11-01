import type { CapacitorConfig } from "@capacitor/cli";

// Android-App von VaKoViN. Der Web-Teil kommt aus dem statischen Build
// (bun run build:android) und liegt fest in der APK.
const config: CapacitorConfig = {
  appId: "com.vakovin.app",
  appName: "VaKoViN",
  webDir: "dist/client",
  android: {
    // Die App lädt nur eigene Dateien und die NHTSA-API.
    allowMixedContent: false,
  },
  plugins: {
    // Native HTTP-Anfragen: die NHTSA-Abfrage läuft so ohne Browser-CORS-Prüfung.
    CapacitorHttp: { enabled: true },
    // Updates werden in src/lib/updater.ts selbst geprüft (GitHub-Release).
    CapacitorUpdater: { autoUpdate: false },
  },
};

export default config;
