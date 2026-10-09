"use client";

import { useId, useRef, useState, type KeyboardEvent, type ReactNode } from "react";
import { L } from "../lib/i18n";

/** Tab halaman klien (pola WAI-ARIA Tabs): panah kiri/kanan, Home/End, satu tab stop. */
export default function ClientTabs({ tabs }: { tabs: { key: string; en: string; id: string; body: ReactNode }[] }) {
  const [active, setActive] = useState(tabs[0].key);
  const base = useId();
  const refs = useRef<(HTMLButtonElement | null)[]>([]);
  const select = (i: number) => {
    const n = (i + tabs.length) % tabs.length;
    setActive(tabs[n].key);
    refs.current[n]?.focus();
  };
  const onKey = (e: KeyboardEvent<HTMLButtonElement>, i: number) => {
    const to = { ArrowRight: i + 1, ArrowLeft: i - 1, Home: 0, End: tabs.length - 1 }[e.key];
    if (to === undefined) return;
    e.preventDefault();
    select(to);
  };
  return (
    <>
      <div className="tabs tabs--page" role="tablist">
        {tabs.map((t, i) => (
          <button
            key={t.key}
            ref={(el) => {
              refs.current[i] = el;
            }}
            type="button"
            role="tab"
            id={`${base}-tab-${t.key}`}
            aria-controls={`${base}-panel-${t.key}`}
            aria-selected={active === t.key}
            tabIndex={active === t.key ? 0 : -1}
            className={`tab${active === t.key ? " tab--active" : ""}`}
            onClick={() => setActive(t.key)}
            onKeyDown={(e) => onKey(e, i)}
          >
            <L en={t.en} id={t.id} />
          </button>
        ))}
      </div>
      {tabs.map((t) => (
        <div key={t.key} role="tabpanel" id={`${base}-panel-${t.key}`} aria-labelledby={`${base}-tab-${t.key}`} hidden={active !== t.key} tabIndex={0}>
          {t.body}
        </div>
      ))}
    </>
  );
}
