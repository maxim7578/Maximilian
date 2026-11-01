import { describe, expect, it } from "vitest";
import { checkVin, clean, hpToPs, parseEquipment } from "@/lib/vin";

describe("VIN-Regeln", () => {
  it("17 Zeichen = volle VIN", () => expect(checkVin("wba3a5c51cf256651")).toBe("full"));
  it("7 Zeichen = Kurz-VIN", () => expect(checkVin("F256651")).toBe("short"));
  it("andere Längen ungültig", () => expect(checkVin("ABC12345")).toBe("invalid"));
  it("hp → PS", () => expect(hpToPs(300)).toBe(304));
  it("blendet 0 und Not Applicable aus", () => {
    expect(clean("0")).toBe("");
    expect(clean("Not Applicable")).toBe("");
  });
  it("Farbe/Innen/Paket aus Ausstattung", () => {
    const e = parseEquipment("609 Navigation Professional\nFarbe: Schwarz\nInnenausstattung: Leder\nPaket: M Sport");
    expect(e.farbe).toBe("Schwarz");
    expect(e.innen).toBe("Leder");
    expect(e.paket).toBe("M Sport");
    expect(e.items[0]).toEqual({ code: "609", text: "Navigation Professional", navi: true });
  });
});
