"use client";

import { useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import Icon from "./Icon";
import { Empty, Level, StatusBadge } from "./ui";
import { CLIENTS, CONTENT, STATUS, STATUS_ORDER, clientName, fmtDate, projectName, type ContentStatus } from "../lib/demo";

const TYPES = ["Instagram Post", "Instagram Reel", "Story", "Google Business", "WhatsApp Promo", "Blog", "Campaign"];
const GOALS = ["Awareness", "Booking langsung", "Engagement", "Promo musiman"];
const TONES = ["Sesuai Voice Card klien", "Elegan", "Santai", "Hangat"];
const PIPELINE = ["Konteks klien & fakta terkonfirmasi", "Agent menyiapkan draft", "Cek otomatis (aturan & klaim)", "Review manusia (L1–L3)"];

export default function ContentBoard({ agents }: { agents: Record<string, string> }) {
  const params = useSearchParams();
  const [tab, setTab] = useState<ContentStatus | "all">("all");
  const [open, setOpen] = useState(false);
  useEffect(() => {
    if (params?.get("new") === "1") setOpen(true);
  }, [params]);
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open]);

  const rows = (tab === "all" ? CONTENT : CONTENT.filter((c) => c.status === tab)).slice().sort((a, b) => b.date.localeCompare(a.date));

  return (
    <>
      <div className="page-head">
        <div>
          <h1>Konten</h1>
          <p>Semua draft, review, dan jadwal tayang lintas klien.</p>
        </div>
        <div className="page-head__actions">
          <button type="button" className="btn btn--primary" onClick={() => setOpen(true)}>
            <Icon name="plus" size={16} /> Buat konten
          </button>
        </div>
      </div>

      <section className="panel panel--flush">
        <div className="tabs" role="tablist" aria-label="Filter status">
          {(["all", ...STATUS_ORDER] as const).map((s) => (
            <button
              key={s}
              type="button"
              role="tab"
              aria-selected={tab === s}
              className={`tab${tab === s ? " tab--active" : ""}`}
              onClick={() => setTab(s)}
            >
              {s === "all" ? "Semua" : STATUS[s].label}
              <span className="tab__count">{s === "all" ? CONTENT.length : CONTENT.filter((c) => c.status === s).length}</span>
            </button>
          ))}
        </div>
        {rows.length === 0 ? (
          <Empty icon="inbox" title="Belum ada konten di status ini" body="Konten akan muncul di sini saat statusnya berubah." />
        ) : (
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th>Konten</th>
                  <th>Klien · Proyek</th>
                  <th>Agent</th>
                  <th>Dibuat</th>
                  <th>Tayang</th>
                  <th>Approval</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((c) => (
                  <tr key={c.id}>
                    <td>
                      <span className="cell-strong">{c.title}</span>
                      <span className="cell-sub">{c.type}</span>
                    </td>
                    <td>
                      {clientName(c.client)}
                      <span className="cell-sub">{projectName(c.project)}</span>
                    </td>
                    <td className="muted">{agents[c.agent]}</td>
                    <td className="nowrap muted">{fmtDate(c.created)}</td>
                    <td className="nowrap muted">{fmtDate(c.date)}</td>
                    <td>
                      <Level level={c.level} />
                    </td>
                    <td>
                      <StatusBadge status={c.status} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {open && (
        <div className="modal-scrim" onClick={(e) => e.target === e.currentTarget && setOpen(false)}>
          <div className="modal" role="dialog" aria-modal="true" aria-labelledby="new-content-title">
            <div className="modal__head">
              <h2 id="new-content-title">Buat konten</h2>
              <button type="button" className="icon-btn icon-btn--ghost" onClick={() => setOpen(false)} aria-label="Tutup">
                <Icon name="x" />
              </button>
            </div>
            <div className="modal__body">
              <div className="form-grid">
                <div className="field">
                  <label htmlFor="f-client">Klien</label>
                  <select id="f-client">
                    {CLIENTS.map((c) => (
                      <option key={c.id}>{c.name}</option>
                    ))}
                  </select>
                </div>
                <div className="field">
                  <label htmlFor="f-type">Jenis konten</label>
                  <select id="f-type">
                    {TYPES.map((t) => (
                      <option key={t}>{t}</option>
                    ))}
                  </select>
                </div>
                <div className="field">
                  <label htmlFor="f-goal">Tujuan</label>
                  <select id="f-goal">
                    {GOALS.map((t) => (
                      <option key={t}>{t}</option>
                    ))}
                  </select>
                </div>
                <div className="field">
                  <label htmlFor="f-tone">Nada</label>
                  <select id="f-tone">
                    {TONES.map((t) => (
                      <option key={t}>{t}</option>
                    ))}
                  </select>
                </div>
                <div className="field" style={{ gridColumn: "1 / -1" }}>
                  <label htmlFor="f-brief">Brief singkat</label>
                  <input id="f-brief" placeholder="Contoh: promo menginap 3 malam untuk November" />
                </div>
              </div>
              <div>
                <div className="field" style={{ marginBottom: 8 }}>
                  <label>Alur yang akan dijalankan</label>
                </div>
                <ol className="steps-mini">
                  {PIPELINE.map((p) => (
                    <li key={p}>
                      <span />
                      {p}
                    </li>
                  ))}
                </ol>
              </div>
              <div className="callout" role="note">
                <Icon name="shield" size={16} />
                Generate dengan AI aktif setelah backend AI (VPS 2) tersambung. Hasilnya selalu berupa draft yang wajib direview
                manusia sebelum tayang.
              </div>
            </div>
            <div className="modal__foot">
              <button type="button" className="btn btn--secondary" onClick={() => setOpen(false)}>
                Batal
              </button>
              <button type="button" className="btn btn--primary" disabled>
                Generate dengan AI
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
