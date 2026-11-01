import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { ArrowRight, Calendar, Car, ChevronDown, Cog, Gauge, Layers, Loader2, Palette, Search, Star, type LucideIcon } from "lucide-react";
import heroCar from "@/assets/hero-car.jpg";
import heroLogo from "@/assets/hero-logo.webp";
import { z } from "zod";
import { Equipment } from "@/components/Equipment";
import { VinList } from "@/components/VinList";
import { useStore } from "@/hooks/use-store";
import { addRecent, getFavorites, getRecent, toggleFavorite } from "@/lib/storage";
import { checkVin, clean, decodeVin, liters, parseEquipment, power, transmission, type Nhtsa } from "@/lib/vin";

export const Route = createFileRoute("/")({
  validateSearch: z.object({ vin: z.string().optional() }),
  head: () => ({
    meta: [
      { title: "VaKoViN – Fahrzeugdaten per VIN" },
      { name: "description", content: "Fahrzeugdaten per Fahrgestellnummer nachschlagen – über die NHTSA-vPIC-Datenbank." },
      { property: "og:title", content: "VaKoViN – Fahrzeugdaten per VIN" },
      { property: "og:description", content: "Fahrzeugdaten per Fahrgestellnummer nachschlagen." },
    ],
  }),
  component: Home,
});

type State = { s: "idle" } | { s: "loading" } | { s: "error" } | { s: "empty" } | { s: "ok"; r: Nhtsa };

function Home() {
  const { vin } = Route.useSearch();
  const navigate = useNavigate({ from: "/" });
  const [input, setInput] = useState(vin ?? "");
  const [hint, setHint] = useState("");
  const [state, setState] = useState<State>({ s: "idle" });
  const [eqRaw, setEqRaw] = useState("");
  const recent = useStore(getRecent, [] as string[]);
  const favs = useStore(getFavorites, [] as string[]);
  const kind = vin ? checkVin(vin) : "invalid";

  useEffect(() => {
    setInput(vin ?? "");
    if (!vin || kind === "invalid") return setState({ s: "idle" });
    addRecent(vin);
    if (kind === "short") return setState({ s: "idle" });
    let alive = true;
    setState({ s: "loading" });
    decodeVin(vin)
      .then((r) => alive && setState(r ? { s: "ok", r } : { s: "empty" }))
      .catch(() => alive && setState({ s: "error" }));
    return () => { alive = false; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [vin]);

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    const v = input.trim().toUpperCase();
    if (checkVin(v) === "invalid") return setHint("Bitte entweder die volle VIN (17 Zeichen) oder die Kurz-VIN (letzte 7) eingeben.");
    setHint("");
    navigate({ search: { vin: v } });
  };

  const eq = parseEquipment(eqRaw);
  const active = vin && kind !== "invalid";

  return (
    <div className="space-y-5">
      <header className="pt-2 text-center">
        <h1 className="text-5xl font-extrabold tracking-tight">
          <span className="text-foreground">VaKo</span><span className="text-brand">ViN</span>
        </h1>
        <p className="mx-auto mt-2 max-w-xs text-base text-muted-foreground">Fahrzeugdaten per Fahrgestellnummer nachschlagen</p>
      </header>

      <form onSubmit={submit}>
        <div className="glass-pill flex items-center gap-2 p-1.5 pl-4">
          <Search className="h-5 w-5 shrink-0 text-muted-foreground" aria-hidden />
          <input
            id="vin-input"
            value={input}
            onChange={(e) => setInput(e.target.value.toUpperCase().replace(/\s/g, ""))}
            placeholder="Fahrgestellnummer eingeben"
            aria-label="Fahrgestellnummer"
            maxLength={17}
            autoCapitalize="characters"
            autoCorrect="off"
            spellCheck={false}
            className="min-w-0 flex-1 bg-transparent py-2 text-base font-medium uppercase tabular-nums tracking-wide outline-none placeholder:font-normal placeholder:normal-case placeholder:tracking-normal placeholder:text-muted-foreground"
          />
          <button type="submit" aria-label="Abfragen" className="btn-cta">
            <ArrowRight className="h-5 w-5" />
          </button>
        </div>
        {hint && <p role="alert" className="mt-2 px-2 text-sm font-medium text-destructive">{hint}</p>}
      </form>

      {!active && (
        <img src={heroLogo} alt="VaKoViN-Logo" width={1254} height={1254} fetchPriority="high" className="mx-auto block w-full max-w-[440px] [mask-image:radial-gradient(closest-side,black_82%,transparent)]" />
      )}

      {active && (
        <div className="glass flex items-center justify-between gap-3 p-2 pl-4">
          <span className="min-w-0 truncate text-sm font-medium tabular-nums tracking-wide">{vin}</span>
          <button onClick={() => toggleFavorite(vin)} aria-pressed={favs.includes(vin)} className="btn-glass shrink-0">
            <Star className={favs.includes(vin) ? "h-4 w-4 fill-brand text-brand" : "h-4 w-4"} />
            {favs.includes(vin) ? "Gemerkt" : "Merken"}
          </button>
        </div>
      )}

      {active && kind === "short" && (
        <p className="glass p-5 text-sm">Für die US-Grunddaten (Modell/Motor) bitte die volle 17-stellige VIN eingeben.</p>
      )}
      {state.s === "loading" && <div role="status" className="glass flex items-center gap-2 p-5 text-sm"><Loader2 className="h-4 w-4 animate-spin text-brand" /> Frage NHTSA ab …</div>}
      {state.s === "error" && <p role="alert" className="glass p-5 text-sm font-medium text-destructive">Die Abfrage bei der NHTSA war nicht möglich. Bitte prüfe deine Verbindung und versuche es erneut.</p>}
      {state.s === "empty" && <p className="glass p-5 text-sm">Keine Fahrzeugdaten zu dieser VIN gefunden.</p>}

      {state.s === "ok" && <Overview r={state.r} eq={eq} />}

      {active && <Equipment vin={vin} onChange={setEqRaw} />}

      <section>
        <h2 className="mb-2 px-1 text-lg font-bold">Zuletzt abgefragt</h2>
        <VinList vins={recent.slice(0, 5)} empty="Noch keine Abfragen." />
      </section>
    </div>
  );
}

function Tile({ Icon, label, value, orb }: { Icon: LucideIcon; label: string; value: string; orb?: boolean }) {
  return (
    <div className="glass-tile flex min-w-0 items-center gap-2.5 p-3">
      {orb && value ? <span className="color-orb" aria-hidden /> : <Icon className="h-5 w-5 shrink-0" strokeWidth={1.6} aria-hidden />}
      <div className="min-w-0">
        <div className="text-xs text-muted-foreground">{label}</div>
        <div className={value ? "truncate text-sm font-semibold" : "text-sm text-muted-foreground"}>{value || "—"}</div>
      </div>
    </div>
  );
}

function Overview({ r, eq }: { r: Nhtsa; eq: ReturnType<typeof parseEquipment> }) {
  const [open, setOpen] = useState(false);
  const motor = [liters(r), power(r)].filter(Boolean).join(", ");
  const groups: [string, [string, string][]][] = [
    ["Fahrzeug", [["Marke", clean(r.Make)], ["Modell", clean(r.Model)], ["Baureihe", clean(r.Series)], ["Ausstattungslinie", clean(r.Trim)], ["Baujahr", clean(r.ModelYear)], ["Fahrzeugtyp", clean(r.VehicleType)], ["Karosserie", clean(r.BodyClass)], ["Türen", clean(r.Doors)]]],
    ["Motor & Antrieb", [["Hubraum", liters(r)], ["Zylinder", clean(r.EngineCylinders)], ["Leistung", power(r)], ["Kraftstoff", clean(r.FuelTypePrimary)], ["Motorcode", clean(r.EngineModel)], ["Getriebe", clean(r.TransmissionStyle)], ["Gänge", clean(r.TransmissionSpeeds)], ["Antrieb", clean(r.DriveType)]]],
    ["Herstellung", [["Hersteller", clean(r.Manufacturer)], ["Werk Stadt", clean(r.PlantCity)], ["Werk Land", clean(r.PlantCountry)]]],
  ];
  return (
    <section className="glass p-4">
      <div className="mb-4 flex items-center gap-3">
        <Car className="h-8 w-8 shrink-0" strokeWidth={1.5} aria-hidden />
        <div>
          <h2 className="text-xl font-bold">Fahrzeugübersicht</h2>
          <p className="text-sm text-muted-foreground">Fahrzeugdaten & Ausstattung</p>
        </div>
      </div>
      <div className="relative mb-2.5 h-40 overflow-hidden rounded-2xl bg-foreground">
        <img src={heroCar} alt="" width={1280} height={800} loading="lazy" className="absolute inset-0 h-full w-full object-cover object-[70%_60%] opacity-70" />
        <div className="absolute inset-0 bg-linear-to-r from-foreground/90 via-foreground/50 to-transparent" />
        <div className="relative flex h-full flex-col justify-between p-4 text-primary-foreground">
          <div>
            <div className="text-sm font-semibold">{clean(r.Make)}</div>
            <div className="text-3xl font-bold leading-tight">{clean(r.Model) || "—"}</div>
          </div>
          {eq.paket && (
            <span className="self-start rounded-full border border-primary-foreground/40 bg-primary-foreground/20 px-3 py-1 text-sm font-semibold backdrop-blur-md">{eq.paket}</span>
          )}
        </div>
      </div>
      <div className="grid grid-cols-2 gap-2.5">
        <Tile Icon={Car} label="Modell" value={clean(r.Model)} />
        <Tile Icon={Calendar} label="Baujahr" value={clean(r.ModelYear)} />
        <Tile Icon={Gauge} label="Motor" value={motor} />
        <Tile Icon={Palette} label="Farbe" value={eq.farbe} orb />
        <Tile Icon={Cog} label="Getriebe" value={transmission(r)} />
        <Tile Icon={Layers} label="Paket" value={eq.paket} />
      </div>
      <button onClick={() => setOpen(!open)} aria-expanded={open} className="btn-glass mt-3 w-full justify-between">
        Alle Fahrzeugdaten <ChevronDown className={`h-4 w-4 transition-transform ${open ? "rotate-180" : ""}`} />
      </button>
      {open && (
        <div className="mt-3 space-y-2.5">
          {groups.map(([title, rows]) => {
            const vis = rows.filter(([, v]) => v);
            if (!vis.length) return null;
            return (
              <div key={title} className="glass-tile p-4">
                <h3 className="mb-2 font-bold">{title}</h3>
                <dl className="divide-y divide-foreground/10 text-sm">
                  {vis.map(([k, v]) => (
                    <div key={k} className="flex justify-between gap-4 py-2"><dt className="text-muted-foreground">{k}</dt><dd className="text-right font-medium">{v}</dd></div>
                  ))}
                </dl>
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
}
