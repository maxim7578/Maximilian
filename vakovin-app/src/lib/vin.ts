export type VinCheck = "full" | "short" | "invalid";

export function checkVin(v: string): VinCheck {
  const s = v.trim().toUpperCase();
  if (/^[A-Z0-9]{17}$/.test(s)) return "full";
  if (/^[A-Z0-9]{7}$/.test(s)) return "short";
  return "invalid";
}

export const hpToPs = (hp: number) => Math.round(hp * 1.01387);

export function clean(v: unknown): string {
  if (v === null || v === undefined) return "";
  const s = String(v).trim();
  if (!s || s === "0" || s.toLowerCase() === "not applicable") return "";
  return s;
}

type NhtsaKey = "Make" | "Model" | "Series" | "Trim" | "ModelYear" | "VehicleType" | "BodyClass" | "Doors" | "DisplacementL" | "EngineCylinders" | "EngineHP" | "FuelTypePrimary" | "EngineModel" | "TransmissionStyle" | "TransmissionSpeeds" | "DriveType" | "Manufacturer" | "PlantCity" | "PlantCountry";
export type Nhtsa = Partial<Record<NhtsaKey, string>>;

export async function decodeVin(vin: string): Promise<Nhtsa | null> {
  const res = await fetch(
    `https://vpic.nhtsa.dot.gov/api/vehicles/DecodeVinValues/${encodeURIComponent(vin)}?format=json`,
    { cache: "no-store" },
  );
  if (!res.ok) throw new Error("http");
  const json = await res.json();
  const r: Nhtsa | undefined = json?.Results?.[0];
  if (!r || (!clean(r.Make) && !clean(r.Model) && !clean(r.ModelYear))) return null;
  return r;
}

export function liters(r: Nhtsa) {
  const l = clean(r.DisplacementL);
  if (!l) return "";
  const n = Number(l);
  return isNaN(n) ? l : `${n.toFixed(1).replace(".", ",")} l`;
}

export function power(r: Nhtsa) {
  const hp = Number(clean(r.EngineHP));
  return hp ? `${hpToPs(hp)} PS` : "";
}

export function transmission(r: Nhtsa) {
  return [clean(r.TransmissionStyle), clean(r.TransmissionSpeeds) && `${clean(r.TransmissionSpeeds)} Gänge`]
    .filter(Boolean)
    .join(", ");
}

export interface Equip {
  code: string;
  text: string;
  navi: boolean;
}

export function parseEquipment(raw: string) {
  const items: Equip[] = [];
  let farbe = "", innen = "", paket = "";
  for (const line of raw.split(/\r?\n/).map((l) => l.trim()).filter(Boolean)) {
    const m = line.match(/^(farbe|innenausstattung|paket)\s*:\s*(.+)$/i);
    if (m) {
      const k = (m[1] ?? "").toLowerCase();
      const val = m[2] ?? "";
      if (k === "farbe") farbe = val;
      else if (k === "innenausstattung") innen = val;
      else paket = val;
      continue;
    }
    const c = line.match(/^([A-Z0-9]{3,4})\s+(.+)$/i);
    const code = (c?.[1] ?? "").toUpperCase();
    const text = c?.[2] ?? line;
    items.push({ code, text, navi: /navi/i.test(line) });
  }
  return { items, farbe, innen, paket };
}
