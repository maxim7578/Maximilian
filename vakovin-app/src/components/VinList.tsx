import { Link } from "@tanstack/react-router";
import { Star, ChevronRight } from "lucide-react";
import { getFavorites, toggleFavorite } from "@/lib/storage";
import { useStore } from "@/hooks/use-store";

export function VinList({ vins, empty, star = true }: { vins: string[]; empty: string; star?: boolean }) {
  const favs = useStore(getFavorites, [] as string[]);
  if (!vins.length) return <p className="glass p-5 text-sm text-muted-foreground">{empty}</p>;
  return (
    <ul className="glass divide-y divide-foreground/10 overflow-hidden p-1">
      {vins.map((v) => {
        const fav = favs.includes(v);
        return (
          <li key={v} className="flex items-center gap-1">
            <Link to="/" search={{ vin: v }} className="focus-ring flex min-h-12 min-w-0 flex-1 items-center justify-between rounded-2xl px-4 py-3 font-medium tabular-nums tracking-wide">
              <span className="truncate">{v}</span>
              <ChevronRight className="h-4 w-4 shrink-0 text-muted-foreground" />
            </Link>
            {star && (
              <button
                aria-label={fav ? "Aus Favoriten entfernen" : "Zu Favoriten hinzufügen"}
                aria-pressed={fav}
                onClick={() => toggleFavorite(v)}
                className="focus-ring grid h-12 w-12 shrink-0 place-items-center rounded-full"
              >
                <Star className={fav ? "h-5 w-5 fill-brand text-brand" : "h-5 w-5 text-muted-foreground"} />
              </button>
            )}
          </li>
        );
      })}
    </ul>
  );
}
