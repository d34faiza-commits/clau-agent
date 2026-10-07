"use client";

import { useState, type ReactNode } from "react";
import { L } from "../lib/i18n";

export default function ClientTabs({ tabs }: { tabs: { key: string; en: string; id: string; body: ReactNode }[] }) {
  const [active, setActive] = useState(tabs[0].key);
  return (
    <>
      <div className="tabs tabs--page" role="tablist">
        {tabs.map((t) => (
          <button key={t.key} type="button" role="tab" aria-selected={active === t.key} className={`tab${active === t.key ? " tab--active" : ""}`} onClick={() => setActive(t.key)}>
            <L en={t.en} id={t.id} />
          </button>
        ))}
      </div>
      {tabs.map((t) => (
        <div key={t.key} role="tabpanel" hidden={active !== t.key}>
          {t.body}
        </div>
      ))}
    </>
  );
}
