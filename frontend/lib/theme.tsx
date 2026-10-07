"use client";

import { useEffect, useState } from "react";

export type ThemePref = "light" | "dark" | "system";
const KEY = "clau-theme";

/** Dijalankan di <head> sebelum render agar tidak ada kedipan tema. */
export const THEME_SCRIPT = `(function(){try{var p=localStorage.getItem("${KEY}")||"system";var d=p==="dark"||(p==="system"&&matchMedia("(prefers-color-scheme: dark)").matches);document.documentElement.dataset.theme=d?"dark":"light";}catch(e){document.documentElement.dataset.theme="light";}})();`;

function resolve(pref: ThemePref): "light" | "dark" {
  return pref === "dark" || (pref === "system" && window.matchMedia("(prefers-color-scheme: dark)").matches) ? "dark" : "light";
}

function read(): ThemePref {
  try {
    const v = localStorage.getItem(KEY);
    if (v === "light" || v === "dark" || v === "system") return v;
  } catch {}
  return "system";
}

export function useTheme() {
  const [pref, setPrefState] = useState<ThemePref>("system");
  const [resolved, setResolved] = useState<"light" | "dark">("light");

  useEffect(() => {
    const p = read();
    setPrefState(p);
    setResolved(resolve(p));
    const mq = window.matchMedia("(prefers-color-scheme: dark)");
    const onChange = () => {
      if (read() !== "system") return;
      const r = resolve("system");
      document.documentElement.dataset.theme = r;
      setResolved(r);
    };
    mq.addEventListener("change", onChange);
    // Sinkron antar komponen (topbar ↔ halaman Settings).
    const onStorage = () => {
      const p2 = read();
      setPrefState(p2);
      setResolved(resolve(p2));
    };
    window.addEventListener("clau-theme", onStorage);
    return () => {
      mq.removeEventListener("change", onChange);
      window.removeEventListener("clau-theme", onStorage);
    };
  }, []);

  const setPref = (p: ThemePref) => {
    try {
      localStorage.setItem(KEY, p);
    } catch {}
    const r = resolve(p);
    document.documentElement.dataset.theme = r;
    setPrefState(p);
    setResolved(r);
    window.dispatchEvent(new Event("clau-theme"));
  };

  return { pref, resolved, setPref };
}
