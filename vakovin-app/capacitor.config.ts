import type { CapacitorConfig } from "@capacitor/cli";

// Android-App von VaKoViN: lädt die veröffentlichte App mit Anmeldung
// (https://vakovin.lovable.app). So gibt es nur eine Version, und jede
// Änderung in Lovable ist sofort auch in der APK.
const config: CapacitorConfig = {
  appId: "com.vakovin.app",
  appName: "VaKoViN",
  // Nur die Offline-Seite liegt in der APK.
  webDir: "shell",
  server: {
    url: "https://vakovin.lovable.app",
    cleartext: false,
    // Nur die eigene App bleibt in der App; fremde Seiten öffnen im Browser.
    allowNavigation: ["vakovin.lovable.app"],
    errorPath: "index.html",
  },
  android: {
    allowMixedContent: false,
    // Kein Zugriff per Chrome-DevTools/USB auf die WebView.
    webContentsDebuggingEnabled: false,
  },
};

export default config;
