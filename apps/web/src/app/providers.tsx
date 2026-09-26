import { useEffect, useState, type ReactNode } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { IconContext } from "@phosphor-icons/react";
import * as Tooltip from "@radix-ui/react-tooltip";
import { create } from "zustand";

export type ThemePref = "system" | "light" | "dark";

function readPref(): ThemePref {
  try {
    const v = localStorage.getItem("clause.theme");
    return v === "light" || v === "dark" ? v : "system";
  } catch {
    return "system";
  }
}

export const useThemePref = create<{ pref: ThemePref; setPref: (p: ThemePref) => void }>((set) => ({
  pref: readPref(),
  setPref: (pref) => {
    try {
      localStorage.setItem("clause.theme", pref);
    } catch {
      /* Storage unavailable: preference lasts for this session only. */
    }
    set({ pref });
  },
}));

function ThemeSync() {
  const pref = useThemePref((s) => s.pref);
  useEffect(() => {
    const root = document.documentElement;
    if (pref === "system") root.removeAttribute("data-theme");
    else root.setAttribute("data-theme", pref);
  }, [pref]);
  return null;
}

export function Providers({ children }: { children: ReactNode }) {
  const [client] = useState(
    () =>
      new QueryClient({
        defaultOptions: { queries: { staleTime: 15_000, retry: 1, refetchOnWindowFocus: false } },
      }),
  );
  return (
    <QueryClientProvider client={client}>
      <IconContext.Provider value={{ weight: "bold", size: 20 }}>
        <Tooltip.Provider delayDuration={300}>
          <ThemeSync />
          {children}
        </Tooltip.Provider>
      </IconContext.Provider>
    </QueryClientProvider>
  );
}
