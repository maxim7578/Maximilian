import { createFileRoute } from "@tanstack/react-router";
import { VinList } from "@/components/VinList";
import { useStore } from "@/hooks/use-store";
import { getRecent } from "@/lib/storage";

export const Route = createFileRoute("/verlauf")({
  head: () => ({
    meta: [
      { title: "Verlauf – VaKoViN" },
      { name: "description", content: "Deine zuletzt abgefragten Fahrgestellnummern." },
      { property: "og:title", content: "Verlauf – VaKoViN" },
      { property: "og:description", content: "Deine zuletzt abgefragten Fahrgestellnummern." },
    ],
  }),
  component: () => {
    const vins = useStore(getRecent, [] as string[]);
    return (
      <div className="space-y-4">
        <h1 className="text-3xl font-bold tracking-tight">Verlauf</h1>
        <VinList vins={vins} empty="Noch keine VINs abgefragt." />
      </div>
    );
  },
});
