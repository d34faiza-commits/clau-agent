"use client";

import type { ReactNode } from "react";
import { useL } from "../lib/i18n";

/** Tombol yang belum aktif, dengan alasan (tooltip) dalam bahasa yang dipilih. */
export default function DisabledAction({ children, en, id, className = "btn btn--primary" }: { children: ReactNode; en: string; id: string; className?: string }) {
  const tr = useL();
  return (
    <button type="button" className={className} disabled title={tr(en, id)}>
      {children}
    </button>
  );
}
