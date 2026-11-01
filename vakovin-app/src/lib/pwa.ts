// Einziger Ort, an dem der Service Worker registriert wird.
function isPreviewHost(h: string) {
  if (h === "lovableproject.com" || h.endsWith(".lovableproject.com")) return true;
  if (h === "lovableproject-dev.com" || h.endsWith(".lovableproject-dev.com")) return true;
  if (h === "beta.lovable.dev" || h.endsWith(".beta.lovable.dev")) return true;
  if (/\.(lovable\.app|gpt-eng\.com|gptengineer\.run)$/.test(h)) {
    const label = h.split(".")[0] ?? "";
    if (/^(?:id-preview|preview)(?:-[a-z0-9]+)?--.+$/.test(label)) return true;
    if (/^project--.+-dev$/.test(label)) return true;
  }
  return false;
}

export async function registerServiceWorker() {
  if (typeof window === "undefined" || !("serviceWorker" in navigator)) return;
  const h = window.location.hostname.toLowerCase();
  let inIframe = false;
  try { inIframe = window.self !== window.top; } catch { inIframe = true; }
  const off = new URLSearchParams(window.location.search).get("sw") === "off";
  if (!import.meta.env.PROD || inIframe || isPreviewHost(h) || off) {
    const regs = await navigator.serviceWorker.getRegistrations();
    await Promise.all(
      regs.filter((r) => r.active?.scriptURL.endsWith("/sw.js")).map((r) => r.unregister()),
    );
    return;
  }
  navigator.serviceWorker.register("/sw.js").catch(() => {});
}
