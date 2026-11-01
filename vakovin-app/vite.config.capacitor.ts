// Build für die Android-App (Capacitor): statische Single-Page-App ohne Server.
// Der normale Lovable-Build (vite.config.ts) bleibt unverändert.
import { defineConfig } from "@lovable.dev/vite-tanstack-config";

export default defineConfig({
  nitro: false,
  tanstackStart: {
    server: { entry: "server" },
    spa: { enabled: true, prerender: { outputPath: "/index.html" } },
  },
});
