const RECENT = "vakowin.recentVins";
const FAV = "vakowin.favoriteVins";
const EQ = "vakoviN.ausstattung.";

function read(key: string): string[] {
  try {
    const v = JSON.parse(localStorage.getItem(key) || "[]");
    return Array.isArray(v) ? v.filter((x) => typeof x === "string") : [];
  } catch {
    return [];
  }
}
const write = (k: string, v: string[]) => localStorage.setItem(k, JSON.stringify(v));
const notify = () => window.dispatchEvent(new Event("vakovin-storage"));

export const getRecent = () => read(RECENT);
export const getFavorites = () => read(FAV);

export function addRecent(vin: string) {
  write(RECENT, [vin, ...read(RECENT).filter((v) => v !== vin)].slice(0, 20));
  notify();
}

export function toggleFavorite(vin: string) {
  const f = read(FAV);
  write(FAV, f.includes(vin) ? f.filter((v) => v !== vin) : [vin, ...f].slice(0, 50));
  notify();
}

export const getEquipment = (vin: string) => localStorage.getItem(EQ + vin) ?? "";
export function setEquipment(vin: string, text: string) {
  localStorage.setItem(EQ + vin, text); // wirft bei vollem Speicher
  notify();
}
export function deleteEquipment(vin: string) {
  localStorage.removeItem(EQ + vin);
  notify();
}

export function clearAll() {
  Object.keys(localStorage)
    .filter((k) => k === RECENT || k === FAV || k.startsWith(EQ))
    .forEach((k) => localStorage.removeItem(k));
  notify();
}
