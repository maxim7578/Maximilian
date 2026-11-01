import { Link, useNavigate } from "@tanstack/react-router";
import { Home, Search, Clock, Star, Settings } from "lucide-react";

const cls =
  "focus-ring flex flex-col items-center gap-0.5 rounded-full py-2 whitespace-nowrap text-[11px] font-medium tracking-tight text-muted-foreground data-[status=active]:bg-accent data-[status=active]:text-brand";

export function BottomNav() {
  const navigate = useNavigate();
  const goSearch = async () => {
    await navigate({ to: "/", search: {} });
    requestAnimationFrame(() => {
      const el = document.getElementById("vin-input");
      el?.scrollIntoView({ block: "center", behavior: "smooth" });
      el?.focus();
    });
  };
  return (
    <nav aria-label="Hauptnavigation" className="fixed inset-x-0 bottom-0 z-40 px-2 pb-[max(0.75rem,env(safe-area-inset-bottom))]">
      <ul className="glass-pill mx-auto grid max-w-[480px] grid-cols-[repeat(4,minmax(0,1fr))_auto] gap-0.5 p-1">
        <li>
          <Link to="/" search={{}} activeOptions={{ exact: true, includeSearch: false }} className={cls}>
            <Home className="h-6 w-6" /> Start
          </Link>
        </li>
        <li>
          <button onClick={goSearch} className={`${cls} w-full`}>
            <Search className="h-6 w-6" /> Suche
          </button>
        </li>
        <li>
          <Link to="/verlauf" className={cls}><Clock className="h-6 w-6" /> Verlauf</Link>
        </li>
        <li>
          <Link to="/favoriten" className={cls}><Star className="h-6 w-6" /> Favoriten</Link>
        </li>
        <li>
          <Link to="/mehr" className={`${cls} px-2.5`}><Settings className="h-6 w-6" /> Einstellungen</Link>
        </li>
      </ul>
    </nav>
  );
}
