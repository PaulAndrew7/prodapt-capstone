import { create } from "zustand";

function read(): boolean {
  try {
    return localStorage.getItem("clause.avatar") !== "off";
  } catch {
    return true;
  }
}

export const useAvatarPref = create<{ enabled: boolean; setEnabled: (v: boolean) => void }>((set) => ({
  enabled: read(),
  setEnabled: (enabled) => {
    try {
      localStorage.setItem("clause.avatar", enabled ? "on" : "off");
    } catch {
      /* Storage unavailable: the choice lasts for this session. */
    }
    set({ enabled });
  },
}));
