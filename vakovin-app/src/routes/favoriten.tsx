import { createFileRoute } from "@tanstack/react-router";
import { VinList } from "@/components/VinList";
import { useStore } from "@/hooks/use-store";
import { getFavorites } from "@/lib/storage";

export const Route = createFileRoute("/favoriten")({
  head: () => ({
    meta: [
      { title: "Favoriten – VaKoViN" },
      { name: "description", content: "Deine gemerkten Fahrgestellnummern." },
      { property: "og:title", content: "Favoriten – VaKoViN" },
      { property: "og:description", content: "Deine gemerkten Fahrgestellnummern." },
    ],
  }),
  component: () => {
    const vins = useStore(getFavorites, [] as string[]);
    return (
      <div className="space-y-4">
        <h1 className="text-3xl font-bold tracking-tight">Favoriten</h1>
        <VinList vins={vins} empty="Noch keine Favoriten. Tippe auf den Stern, um eine VIN zu merken." />
      </div>
    );
  },
});
