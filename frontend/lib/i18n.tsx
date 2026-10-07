"use client";

// Bahasa UI: English (default) dan Bahasa Indonesia. Pilihan disimpan di localStorage.
// Teks ditulis berpasangan di tempat dipakai: <L en="..." id="..." />. Tanpa ikon bendera.
import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";

export type Lang = "en" | "id";
type Ctx = { lang: Lang; setLang: (l: Lang) => void };

const LangContext = createContext<Ctx>({ lang: "en", setLang: () => {} });
const KEY = "clau-lang";

export function LangProvider({ children }: { children: ReactNode }) {
  const [lang, setLangState] = useState<Lang>("en");
  useEffect(() => {
    try {
      const saved = localStorage.getItem(KEY);
      if (saved === "id" || saved === "en") setLangState(saved);
    } catch {}
  }, []);
  useEffect(() => {
    document.documentElement.lang = lang;
  }, [lang]);
  const setLang = useCallback((l: Lang) => {
    setLangState(l);
    try {
      localStorage.setItem(KEY, l);
    } catch {}
  }, []);
  return <LangContext.Provider value={{ lang, setLang }}>{children}</LangContext.Provider>;
}

export function useLang() {
  return useContext(LangContext);
}

/** Pilih teks sesuai bahasa aktif, untuk atribut (placeholder, aria-label, title). */
export function useL() {
  const { lang } = useLang();
  return (en: string, id: string) => (lang === "id" ? id : en);
}

/** Teks dua bahasa. Aman dipakai di server component (render sebagai client leaf). */
export function L({ en, id }: { en: string; id: string }) {
  const { lang } = useLang();
  return <>{lang === "id" ? id : en}</>;
}

const MON = {
  en: ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
  id: ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"],
};

/** Tanggal ISO (YYYY-MM-DD) dalam format bahasa aktif: "Oct 7, 2026" / "7 Okt 2026". */
export function D({ iso, short, month }: { iso: string; short?: boolean; month?: boolean }) {
  const { lang } = useLang();
  const [y, m, d] = iso.split("-").map(Number);
  const mon = MON[lang][m - 1];
  if (month) return <>{mon}</>;
  if (short) return <>{lang === "en" ? `${mon} ${d}` : `${d} ${mon}`}</>;
  return <>{lang === "en" ? `${mon} ${d}, ${y}` : `${d} ${mon} ${y}`}</>;
}
