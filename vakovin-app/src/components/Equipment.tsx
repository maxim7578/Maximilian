import { useEffect, useState } from "react";
import { Armchair, CarFront, Check, CircleDot, Layers, ListChecks, Navigation, Pencil, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { deleteEquipment, getEquipment, setEquipment } from "@/lib/storage";
import { parseEquipment } from "@/lib/vin";

export function Equipment({ vin, onChange }: { vin: string; onChange: (raw: string) => void }) {
  const [saved, setSaved] = useState("");
  const [draft, setDraft] = useState("");
  const [editing, setEditing] = useState(false);
  const [showAll, setShowAll] = useState(false);

  useEffect(() => {
    const s = getEquipment(vin);
    setSaved(s);
    setDraft(s);
    setEditing(!s);
    onChange(s);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [vin]);

  const save = () => {
    try {
      setEquipment(vin, draft.trim());
      setSaved(draft.trim());
      onChange(draft.trim());
      setEditing(!draft.trim());
      toast.success("Ausstattung gespeichert");
    } catch {
      toast.error("Speichern fehlgeschlagen", { description: "Der Browser-Speicher ist möglicherweise voll." });
    }
  };
  const remove = () => {
    deleteEquipment(vin);
    setSaved("");
    setDraft("");
    setEditing(true);
    onChange("");
  };

  const { items } = parseEquipment(saved);
  const shown = showAll ? items : items.slice(0, 4);

  return (
    <section className="glass p-4">
      <div className="mb-3 flex items-center justify-between gap-3">
        <h2 className="flex items-center gap-2 text-xl font-bold">
          <Layers className="h-6 w-6" strokeWidth={1.6} />
          {editing ? "Ausstattung eintragen" : "Ausstattung"}
        </h2>
        {!editing && items.length > 4 && (
          <button onClick={() => setShowAll(!showAll)} aria-expanded={showAll} className="focus-ring rounded-full px-2 py-1 text-sm font-semibold text-brand">
            {showAll ? "Weniger anzeigen" : "Alle Details →"}
          </button>
        )}
      </div>
      {editing ? (
        <>
          <textarea
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            rows={7}
            placeholder={"609 Navigation Professional\nFarbe: Saphirschwarz\nInnenausstattung: Leder Dakota\nPaket: M Sportpaket"}
            aria-label="Ausstattung"
            className="glass-field w-full p-3 text-sm placeholder:text-muted-foreground"
          />
          <div className="mt-3 flex flex-wrap gap-2">
            <button onClick={save} className="btn-primary">Speichern</button>
            {saved && <button onClick={() => { setDraft(saved); setEditing(false); }} className="btn-glass">Abbrechen</button>}
          </div>
        </>
      ) : (
        <>
          <ul className="grid grid-cols-2 gap-2.5">
            {shown.map((it, i) => {
              const { Icon, title } = iconFor(it.text + " " + it.code);
              return (
                <li key={i} className="glass-tile relative flex flex-col items-center px-3 pb-4 pt-5 text-center">
                  <span className="check-dot absolute right-2.5 top-2.5" aria-hidden><Check className="h-3.5 w-3.5" strokeWidth={3} /></span>
                  <Icon className="h-9 w-9" strokeWidth={1.4} aria-hidden />
                  <span className="mt-2 font-semibold">{title}</span>
                  <span className="mt-1 text-xs leading-snug text-muted-foreground">
                    {it.code && <b className="mr-1 text-brand">{it.code}</b>}
                    {it.text}
                  </span>
                </li>
              );
            })}
          </ul>
          {items.length === 0 && <p className="text-sm text-muted-foreground">Nur Farbe/Innenausstattung/Paket eingetragen.</p>}
          <div className="mt-4 flex flex-wrap gap-2">
            <button onClick={() => setEditing(true)} className="btn-glass"><Pencil className="h-4 w-4" /> Bearbeiten</button>
            <button onClick={remove} className="btn-glass text-destructive"><Trash2 className="h-4 w-4" /> Löschen</button>
          </div>
        </>
      )}
    </section>
  );
}

function iconFor(line: string) {
  const l = line.toLowerCase();
  if (/navi/.test(l)) return { Icon: Navigation, title: "Navigation" };
  if (/leder|sitz/.test(l)) return { Icon: Armchair, title: "Sitze & Leder" };
  if (/felge|\brad\b|räder|zoll|\d{2}\s?["”]/.test(l)) return { Icon: CircleDot, title: "Felgen" };
  if (/assist|driving/.test(l)) return { Icon: CarFront, title: "Assistenz" };
  return { Icon: ListChecks, title: "Ausstattung" };
}
