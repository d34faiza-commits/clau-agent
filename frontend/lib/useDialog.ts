"use client";

import { useEffect, useRef } from "react";

const FOCUSABLE = 'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

/**
 * Perilaku dialog modal: fokus pindah ke dalam dialog saat dibuka, Tab berputar di dalamnya,
 * Esc menutup, scroll halaman di belakang dikunci, dan fokus kembali ke pemicu saat ditutup.
 * Pasang `ref` yang dikembalikan ke elemen dialog (beri `tabIndex={-1}`).
 */
export function useDialog<T extends HTMLElement>(open: boolean, close: () => void) {
  const ref = useRef<T>(null);
  const closeRef = useRef(close);
  useEffect(() => {
    closeRef.current = close;
  });

  useEffect(() => {
    if (!open) return;
    const prev = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    const el = ref.current;
    const focusables = () => (el ? Array.from(el.querySelectorAll<HTMLElement>(FOCUSABLE)).filter((n) => n.getClientRects().length > 0) : []);
    (focusables()[0] ?? el)?.focus();

    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.preventDefault();
        closeRef.current();
        return;
      }
      if (e.key !== "Tab" || !el) return;
      const items = focusables();
      if (items.length === 0) {
        e.preventDefault();
        return;
      }
      const first = items[0];
      const last = items[items.length - 1];
      const active = document.activeElement;
      if (e.shiftKey && (active === first || !el.contains(active))) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && (active === last || !el.contains(active))) {
        e.preventDefault();
        first.focus();
      }
    };
    document.addEventListener("keydown", onKey);
    const overflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = overflow;
      if (prev?.isConnected) prev.focus();
    };
  }, [open]);

  return ref;
}
