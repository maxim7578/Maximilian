import { useEffect, useState } from "react";

/** Liest einen localStorage-Wert nach der Hydration und hält ihn aktuell. */
export function useStore<T>(getter: () => T, initial: T): T {
  const [v, setV] = useState<T>(initial);
  useEffect(() => {
    const up = () => setV(getter());
    up();
    window.addEventListener("vakovin-storage", up);
    window.addEventListener("storage", up);
    return () => {
      window.removeEventListener("vakovin-storage", up);
      window.removeEventListener("storage", up);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  return v;
}
