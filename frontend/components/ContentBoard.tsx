"use client";

import { useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import Avatar from "./Avatar";
import { RunSteps, type RunStep } from "./GenerateRun";
import Icon from "./Icon";
import { Empty, Level, StatusBadge } from "./ui";
import { CLIENTS, CONTENT, FORMATS, PREVIEW, STATUS, STATUS_ORDER, clientName, formatOf, projectName, type ContentItem, type ContentStatus, type Format } from "../lib/demo";
import { D, L, useL } from "../lib/i18n";

type AgentInfo = Record<string, { name: string; hue: string }>;

const TYPES = ["Instagram Post", "Instagram Reel", "Story", "Google Business", "WhatsApp Promotion", "Blog", "Campaign"];

function useEscape(active: boolean, close: () => void) {
  useEffect(() => {
    if (!active) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && close();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [active, close]);
}

export default function ContentBoard({ agents, steps }: { agents: AgentInfo; steps: RunStep[] }) {
  const params = useSearchParams();
  const tr = useL();
  const [tab, setTab] = useState<ContentStatus | "all">("all");
  const [fmt, setFmt] = useState<Format | "all">("all");
  const [open, setOpen] = useState(false);
  const [running, setRunning] = useState(false);
  const [preview, setPreview] = useState<ContentItem | null>(null);
  useEffect(() => {
    if (params?.get("new") === "1") setOpen(true);
  }, [params]);
  const closeCreate = () => {
    setOpen(false);
    setRunning(false);
  };
  useEscape(open, closeCreate);
  useEscape(!!preview, () => setPreview(null));

  const rows = CONTENT.filter((c) => (tab === "all" || c.status === tab) && (fmt === "all" || formatOf(c.type) === fmt)).sort((a, b) => b.date.localeCompare(a.date));
  const p = preview ? PREVIEW[preview.id] : undefined;

  return (
    <>
      <div className="page-head">
        <div>
          <h1><L en="Content" id="Konten" /></h1>
          <p><L en="Every draft, review and scheduled post across clients." id="Semua draft, review, dan jadwal tayang lintas klien." /></p>
        </div>
        <div className="page-head__actions">
          <button type="button" className="btn btn--primary" onClick={() => setOpen(true)}>
            <Icon name="plus" size={16} /> <L en="Create content" id="Buat konten" />
          </button>
        </div>
      </div>

      <section className="panel panel--flush">
        <div className="tabs" role="tablist" aria-label={tr("Filter by status", "Filter status")}>
          {(["all", ...STATUS_ORDER] as const).map((s) => (
            <button key={s} type="button" role="tab" aria-selected={tab === s} className={`tab${tab === s ? " tab--active" : ""}`} onClick={() => setTab(s)}>
              {s === "all" ? <L en="All" id="Semua" /> : <L en={STATUS[s].en} id={STATUS[s].id} />}
              <span className="tab__count">{s === "all" ? CONTENT.length : CONTENT.filter((c) => c.status === s).length}</span>
            </button>
          ))}
        </div>
        <div className="chips" role="group" aria-label={tr("Filter by format", "Filter format")}>
          {(["all", "post", "reel", "story", "google", "whatsapp", "blog"] as const).map((f) => (
            <button key={f} type="button" className="chip" aria-pressed={fmt === f} onClick={() => setFmt(f)}>
              {f === "all" ? <L en="All formats" id="Semua format" /> : <L en={FORMATS[f].en} id={FORMATS[f].id} />}
            </button>
          ))}
        </div>
        {rows.length === 0 ? (
          <Empty icon="inbox" title={<L en="Nothing here yet" id="Belum ada konten di sini" />} body={<L en="Content appears here when it reaches this status or format." id="Konten muncul di sini saat mencapai status atau format ini." />} />
        ) : (
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th><L en="Content" id="Konten" /></th>
                  <th><L en="Client · Campaign" id="Klien · Campaign" /></th>
                  <th><L en="AI agent" id="Agent AI" /></th>
                  <th><L en="Date" id="Tanggal" /></th>
                  <th><L en="Approval" id="Approval" /></th>
                  <th><L en="Status" id="Status" /></th>
                </tr>
              </thead>
              <tbody>
                {rows.map((c) => (
                  <tr key={c.id} className="is-click" onClick={() => setPreview(c)} onKeyDown={(e) => e.key === "Enter" && setPreview(c)} tabIndex={0}>
                    <td><span className="cell-strong">{c.title}</span><span className="cell-sub">{c.type}</span></td>
                    <td>{clientName(c.client)}<span className="cell-sub">{projectName(c.project)}</span></td>
                    <td><span className="cell-agent"><Avatar name={agents[c.agent].name} hue={agents[c.agent].hue} size="sm" />{agents[c.agent].name}</span></td>
                    <td className="nowrap muted"><D iso={c.date} /></td>
                    <td><Level level={c.level} /></td>
                    <td><StatusBadge status={c.status} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {preview && (
        <>
          <div className="drawer-scrim" onClick={() => setPreview(null)} />
          <aside className="drawer" role="dialog" aria-modal="true" aria-labelledby="preview-title">
            <div className="modal__head">
              <h2 id="preview-title">{preview.title}</h2>
              <button type="button" className="icon-btn icon-btn--ghost" onClick={() => setPreview(null)} aria-label={tr("Close", "Tutup")}><Icon name="x" /></button>
            </div>
            <div className="drawer__body">
              <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
                <StatusBadge status={preview.status} />
                <Level level={preview.level} />
                <span className="tag">{preview.type}</span>
              </div>
              <div className="visual"><L en="Visual: real property photo or video from the client's media library" id="Visual: foto atau video properti asli dari media library klien" /></div>
              {p ? (
                <>
                  <div className="kv-block"><h3><L en="Hook" id="Hook" /></h3><p className="cell-strong">{p.hook}</p></div>
                  <div className="kv-block"><h3><L en="Caption" id="Caption" /></h3><p>{p.caption}</p></div>
                  <div className="kv-block"><h3>CTA</h3><p>{p.cta}</p></div>
                  <div className="kv-block"><h3>Hashtags</h3><div className="tags">{p.hashtags.map((h) => <span key={h} className="tag">{h}</span>)}</div></div>
                </>
              ) : (
                <div className="callout"><Icon name="content" size={16} /><L en="Draft text appears here once the agent has written it." id="Teks draft muncul di sini setelah agent menulisnya." /></div>
              )}
              <dl className="kv">
                <dt><L en="Client" id="Klien" /></dt><dd>{clientName(preview.client)}</dd>
                <dt><L en="Campaign" id="Campaign" /></dt><dd>{projectName(preview.project)}</dd>
                <dt><L en="AI agent" id="Agent AI" /></dt><dd>{agents[preview.agent].name}</dd>
                <dt><L en="Publish date" id="Tanggal tayang" /></dt><dd><D iso={preview.date} /></dd>
              </dl>
              <div className="callout"><Icon name="shield" size={16} /><L en="Actions are enabled once sign-in and the backend are live. Approval is always done by a person." id="Aksi aktif setelah login dan backend berjalan. Persetujuan selalu dilakukan manusia." /></div>
            </div>
            <div className="modal__foot">
              <button type="button" className="btn btn--secondary btn--sm" disabled><Icon name="pen" size={14} /> <L en="Edit" id="Edit" /></button>
              <button type="button" className="btn btn--secondary btn--sm" disabled><Icon name="refresh" size={14} /> <L en="Regenerate" id="Buat ulang" /></button>
              <button type="button" className="btn btn--danger btn--sm" disabled><L en="Reject" id="Tolak" /></button>
              <button type="button" className="btn btn--primary btn--sm" disabled><Icon name="check" size={14} /> <L en="Approve" id="Setujui" /></button>
            </div>
          </aside>
        </>
      )}

      {open && (
        <div className="modal-scrim" onClick={(e) => e.target === e.currentTarget && closeCreate()}>
          <div className="modal" role="dialog" aria-modal="true" aria-labelledby="new-content-title">
            <div className="modal__head">
              <h2 id="new-content-title">{running ? <L en="Your AI team is working" id="Tim AI kamu sedang bekerja" /> : <L en="Create content" id="Buat konten" />}</h2>
              <button type="button" className="icon-btn icon-btn--ghost" onClick={closeCreate} aria-label={tr("Close", "Tutup")}><Icon name="x" /></button>
            </div>
            <div className="modal__body">
              {running ? (
                <>
                  <div className="sim" role="note" style={{ margin: 0 }}>
                    <span className="sim__tag"><L en="SIMULATION" id="SIMULASI" /></span>
                    <L en="Workflow preview only. No AI model is called until the AI backend is connected." id="Hanya pratinjau alur. Belum ada model AI yang dipanggil sampai backend AI tersambung." />
                  </div>
                  <RunSteps steps={steps} running={running} />
                </>
              ) : (
                <div className="form-grid">
                  <div className="field"><label htmlFor="f-client"><L en="Client" id="Klien" /></label><select id="f-client">{CLIENTS.map((c) => <option key={c.id}>{c.name}</option>)}</select></div>
                  <div className="field"><label htmlFor="f-type"><L en="Content type" id="Jenis konten" /></label><select id="f-type">{TYPES.map((t) => <option key={t}>{t}</option>)}</select></div>
                  <div className="field"><label htmlFor="f-goal"><L en="Goal" id="Tujuan" /></label><select id="f-goal"><option>{tr("Awareness", "Awareness")}</option><option>{tr("Direct bookings", "Booking langsung")}</option><option>{tr("Engagement", "Interaksi")}</option><option>{tr("Seasonal promotion", "Promo musiman")}</option></select></div>
                  <div className="field"><label htmlFor="f-aud"><L en="Audience" id="Audiens" /></label><select id="f-aud"><option>{tr("From client profile", "Dari profil klien")}</option><option>{tr("Australian travellers", "Wisatawan Australia")}</option><option>{tr("Domestic travellers", "Wisatawan domestik")}</option></select></div>
                  <div className="field"><label htmlFor="f-tone"><L en="Tone" id="Nada" /></label><select id="f-tone"><option>{tr("Client Voice Card", "Voice Card klien")}</option><option>{tr("Elegant", "Elegan")}</option><option>{tr("Relaxed", "Santai")}</option><option>{tr("Warm", "Hangat")}</option></select></div>
                  <div className="field"><label htmlFor="f-camp"><L en="Campaign" id="Campaign" /></label><select id="f-camp"><option>{tr("None", "Tanpa campaign")}</option><option>{tr("Year-end campaign", "Campaign akhir tahun")}</option></select></div>
                </div>
              )}
            </div>
            <div className="modal__foot">
              <button type="button" className="btn btn--secondary" onClick={closeCreate}>{running ? <L en="Close" id="Tutup" /> : <L en="Cancel" id="Batal" />}</button>
              {!running && (
                <button type="button" className="btn btn--primary" onClick={() => setRunning(true)}>
                  <Icon name="sparkles" size={16} /> <L en="Generate with AI" id="Buat dengan AI" />
                </button>
              )}
            </div>
          </div>
        </div>
      )}
    </>
  );
}
