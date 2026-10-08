"use client";

import { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import Avatar from "./Avatar";
import Icon from "./Icon";
import { L, useL } from "../lib/i18n";
import type { Look, Uniform } from "../lib/team";

export type RunStep = { key: string; agent?: { name: string; hue: string; look: Look; uniform: Uniform }; en: string; id: string; subEn: string; subId: string; human?: boolean };

/** Pratinjau alur kerja tim AI. SIMULASI: tidak memanggil model AI apa pun. */
export function RunSteps({ steps, running }: { steps: RunStep[]; running: boolean }) {
  const [done, setDone] = useState(0);
  useEffect(() => {
    if (!running) return;
    setDone(0);
    const auto = steps.filter((s) => !s.human).length;
    let n = 0;
    const t = setInterval(() => {
      n += 1;
      setDone(n);
      if (n >= auto) clearInterval(t);
    }, 1100);
    return () => clearInterval(t);
  }, [running, steps]);

  return (
    <ol className="run" aria-live="polite">
      {steps.map((s, i) => {
        const state = i < done ? "done" : i === done ? (s.human ? "waiting" : "working") : "waiting";
        return (
          <li key={s.key} className={`is-${state === "waiting" ? "waiting" : state}`}>
            <span className="run__icon">{state === "done" && <Icon name="check" size={13} />}</span>
            {s.agent ? <Avatar {...s.agent} size="sm" /> : <span className="av av--sm" style={{ display: "grid", placeItems: "center", background: "var(--color-surface-muted)", color: "var(--color-text-muted)" }}><Icon name={s.human ? "user" : "shield"} size={16} /></span>}
            <div className="run__main">
              <div className="run__title">
                <L en={s.en} id={s.id} />
              </div>
              <div className="run__sub">
                <L en={s.subEn} id={s.subId} />
              </div>
            </div>
            <span className="run__state">
              {state === "done" && <L en="Completed" id="Selesai" />}
              {state === "working" && <L en="Working…" id="Bekerja…" />}
              {state === "waiting" && (s.human && i === done ? <L en="Waiting for your team" id="Menunggu tim kamu" /> : <L en="Waiting" id="Menunggu" />)}
            </span>
          </li>
        );
      })}
    </ol>
  );
}

export default function GenerateRun({ steps, label }: { steps: RunStep[]; label?: { en: string; id: string } }) {
  const [open, setOpen] = useState(false);
  const tr = useL();
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open]);
  return (
    <>
      <button type="button" className="btn btn--primary" onClick={() => setOpen(true)}>
        <Icon name="sparkles" size={16} />
        {label ? <L en={label.en} id={label.id} /> : <L en="Generate monthly content" id="Buat konten bulanan" />}
      </button>
      {open &&
        createPortal(
        <div className="modal-scrim" onClick={(e) => e.target === e.currentTarget && setOpen(false)}>
          <div className="modal" role="dialog" aria-modal="true" aria-labelledby="run-title">
            <div className="modal__head">
              <h2 id="run-title">
                <L en="Your AI team is working" id="Tim AI kamu sedang bekerja" />
              </h2>
              <button type="button" className="icon-btn icon-btn--ghost" onClick={() => setOpen(false)} aria-label={tr("Close", "Tutup")}>
                <Icon name="x" />
              </button>
            </div>
            <div className="modal__body">
              <div className="sim" role="note" style={{ margin: 0 }}>
                <span className="sim__tag">
                  <L en="SIMULATION" id="SIMULASI" />
                </span>
                <L en="Workflow preview only. No AI model is called until the AI backend is connected." id="Hanya pratinjau alur. Belum ada model AI yang dipanggil sampai backend AI tersambung." />
              </div>
              <RunSteps steps={steps} running={open} />
            </div>
            <div className="modal__foot">
              <button type="button" className="btn btn--secondary" onClick={() => setOpen(false)}>
                <L en="Close" id="Tutup" />
              </button>
            </div>
          </div>
        </div>,
          document.body,
        )}
    </>
  );
}
