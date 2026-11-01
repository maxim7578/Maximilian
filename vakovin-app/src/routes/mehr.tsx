import { createFileRoute } from "@tanstack/react-router";
import { Trash2 } from "lucide-react";
import { toast } from "sonner";
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription,
  AlertDialogFooter, AlertDialogHeader, AlertDialogTitle, AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { clearAll } from "@/lib/storage";

export const Route = createFileRoute("/mehr")({
  head: () => ({
    meta: [
      { title: "Einstellungen – VaKoViN" },
      { name: "description", content: "Datenquelle, Hinweise und Daten löschen." },
      { property: "og:title", content: "Einstellungen – VaKoViN" },
      { property: "og:description", content: "Datenquelle, Hinweise und Daten löschen." },
    ],
  }),
  component: Mehr,
});

const TEXT = "Löscht Verlauf, Favoriten und Ausstattungseinträge auf diesem Gerät. Die Daten lassen sich danach nicht wiederherstellen.";

function Mehr() {
  return (
    <div className="space-y-4">
      <h1 className="text-3xl font-bold tracking-tight">Einstellungen</h1>
      <section className="glass p-5">
        <h2 className="mb-2 flex items-center gap-2 text-lg font-bold"><Trash2 className="h-5 w-5 text-brand" /> Daten löschen</h2>
        <p className="mb-4 text-sm text-muted-foreground">{TEXT}</p>
        <AlertDialog>
          <AlertDialogTrigger asChild><button className="btn-glass text-destructive">Alle Daten löschen</button></AlertDialogTrigger>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>Wirklich alle Daten löschen?</AlertDialogTitle>
              <AlertDialogDescription>{TEXT}</AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>Abbrechen</AlertDialogCancel>
              <AlertDialogAction onClick={() => { clearAll(); toast.success("Daten gelöscht"); }}>Löschen</AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      </section>
    </div>
  );
}
