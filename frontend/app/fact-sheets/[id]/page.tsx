"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState, type FormEvent } from "react";
import { Card, PageHeader } from "../../../components/ui";
import { Field, Notice, RefLink, SessionGate, StatusPill } from "../../../components/WorkflowUi";
import { api, errorText, type Me } from "../../../lib/auth";
import { L, useL, useLang } from "../../../lib/i18n";
import { REF_RE, SENIOR, formatDate, roleFor, useSession, type Fact, type FactSheetDetail } from "../../../lib/workflow";

type Msg = { ok: boolean; text: string } | null;

export default function FactSheetDetailPage() {
  const params = useParams<{ id: string }>();
  const id = Number(params?.id);
  const tr = useL();
  const { lang } = useLang();
  const { me, state } = useSession();
  const [sheet, setSheet] = useState<FactSheetDetail | null>(null);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    const r = await api<FactSheetDetail>(`fact-sheets/${id}`);
    if (r.ok) setSheet(r.data);
    else setError(errorText(r, lang));
  }, [id, lang]);
  useEffect(() => {
    document.title = `${tr("Fact sheet", "Fact sheet")} #${id} · CLAU AI`;
    if (state === "ready" && Number.isInteger(id) && id > 0) load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [state, id]);

  const header = (
    <PageHeader
      title={sheet ? <>{sheet.client_code} · <L en="fact sheet" id="fact sheet" /> v{sheet.version}</> : <L en="Fact sheet" id="Fact sheet" />}
      subtitle={<Link className="link" href="/fact-sheets">← <L en="All fact sheets" id="Semua fact sheet" /></Link>}
    />
  );
  if (state !== "ready" || !me) return <>{header}<SessionGate state={state} /></>;
  if (!sheet) return <>{header}{error && <p className="auth-notice auth-notice--error" role="alert">{error}</p>}</>;

  const role = roleFor(me, sheet.client_code);
  const answerer = (SENIOR.has(role) || role === "client_approver") && sheet.created_by !== me.user.id;
  const agency = SENIOR.has(role);
  const groups = sheet.facts.reduce<Record<string, Fact[]>>((acc, f) => ({ ...acc, [f.category]: [...(acc[f.category] ?? []), f] }), {});

  return (
    <>
      {header}
      {error && <p className="auth-notice auth-notice--error" role="alert">{error}</p>}
      <Card title={<L en="Status" id="Status" />} action={<StatusPill status={sheet.status} />}>
        <dl className="kv wf-kv">
          <div><dt>{tr("Answered", "Dijawab")}</dt><dd>{sheet.facts_answered}/{sheet.facts_total}</dd></div>
          <div><dt>{tr("Source document", "Dokumen sumber")}</dt><dd><RefLink value={sheet.document_ref} /></dd></div>
          <div><dt>{tr("Approved", "Disetujui")}</dt><dd>{formatDate(sheet.approved_at, lang)}{sheet.approved_by_role ? ` · ${sheet.approved_by_role}` : ""}</dd></div>
          {sheet.approval_ref && <div><dt>{tr("Written approval", "Persetujuan tertulis")}</dt><dd><RefLink value={sheet.approval_ref} /></dd></div>}
        </dl>
        {sheet.status === "approved" && <p className="muted wf-hint">{tr("Approved versions are frozen. Changes need a new version.", "Versi yang disetujui dibekukan. Perubahan perlu versi baru.")}</p>}
        {!answerer && sheet.status !== "approved" && (
          <p className="muted wf-hint">
            {sheet.created_by === me.user.id
              ? tr("You prepared this version, so the client (or another lead with the client's written answer) answers it.", "Kamu yang menyusun versi ini, jadi klien (atau lead lain dengan jawaban tertulis klien) yang menjawabnya.")
              : tr("Only the client's approver (or the owner/content lead with the client's written answer) answers facts.", "Hanya approver klien (atau owner/content lead dengan jawaban tertulis klien) yang menjawab fakta.")}
          </p>
        )}
        {answerer && sheet.status === "ready" && <ApproveForm sheet={sheet} agency={agency} onDone={load} />}
      </Card>

      {Object.entries(groups).map(([category, facts]) => (
        <Card key={category} title={category} flush>
          <ul className="wf-facts">
            {facts.map((f) => (
              <FactCard key={f.fact_key} fact={f} sheetId={sheet.id} canAnswer={answerer && sheet.status !== "approved"} agency={agency} me={me} onDone={load} />
            ))}
          </ul>
        </Card>
      ))}
    </>
  );
}

function FactCard({ fact, sheetId, canAnswer, agency, me, onDone }: { fact: Fact; sheetId: number; canAnswer: boolean; agency: boolean; me: Me; onDone: () => void }) {
  const tr = useL();
  const { lang } = useLang();
  const [correcting, setCorrecting] = useState(false);
  const [value, setValue] = useState(fact.current_value);
  const [ref, setRef] = useState("");
  const [msg, setMsg] = useState<Msg>(null);
  const last = fact.answers[fact.answers.length - 1];

  async function send(decision: "confirmed" | "corrected", e?: FormEvent) {
    e?.preventDefault();
    const body = { fact_key: fact.fact_key, decision, ...(decision === "corrected" ? { value_after: value } : {}), ...(ref.trim() ? { channel_ref: ref.trim() } : {}) };
    const r = await api(`fact-sheets/${sheetId}/confirmations`, { method: "POST", body });
    if (r.ok) {
      setCorrecting(false);
      setMsg(null);
      onDone();
    } else setMsg({ ok: false, text: errorText(r, lang) });
  }
  const refOk = !agency || REF_RE.test(ref.trim());

  return (
    <li className="wf-fact">
      <div className="wf-fact__head">
        <div>
          <div className="cell-strong">{fact.label}</div>
          <code className="muted">{fact.fact_key}</code>
        </div>
        <StatusPill status={fact.status} />
      </div>
      <p className="wf-fact__value">
        {fact.status === "corrected" ? (
          <><s className="muted">{fact.value}</s> → <strong>{fact.current_value}</strong></>
        ) : (
          fact.value
        )}
      </p>
      {last && (
        <p className="muted wf-hint">
          {last.confirmed_by === me.user.id ? tr("You", "Kamu") : last.confirmed_by_role} · {formatDate(last.confirmed_at, lang)}
          {last.channel_ref && <> · <RefLink value={last.channel_ref} /></>}
          {fact.answers.length > 1 && ` · ${tr(`${fact.answers.length} answers`, `${fact.answers.length} jawaban`)}`}
        </p>
      )}
      {canAnswer && (
        <form className="wf-fact__actions" onSubmit={(e) => send("corrected", e)}>
          {agency && (
            <Field id={`ref-${fact.fact_key}`} label={tr("Client's written answer (link)", "Jawaban tertulis klien (link)")}>
              <input id={`ref-${fact.fact_key}`} value={ref} onChange={(e) => setRef(e.target.value)} maxLength={500} placeholder="https://" />
            </Field>
          )}
          {correcting ? (
            <>
              <Field id={`val-${fact.fact_key}`} label={tr("Correct value", "Nilai yang benar")}>
                <input id={`val-${fact.fact_key}`} value={value} onChange={(e) => setValue(e.target.value)} required maxLength={1000} />
              </Field>
              <div className="auth-actions">
                <button type="submit" className="btn btn--primary btn--sm" disabled={!value.trim() || !refOk}>{tr("Save correction", "Simpan koreksi")}</button>
                <button type="button" className="btn btn--secondary btn--sm" onClick={() => setCorrecting(false)}>{tr("Cancel", "Batal")}</button>
              </div>
            </>
          ) : (
            <div className="auth-actions">
              <button type="button" className="btn btn--primary btn--sm" disabled={!refOk} onClick={() => send("confirmed")}>{tr("Correct", "Benar")}</button>
              <button type="button" className="btn btn--secondary btn--sm" onClick={() => setCorrecting(true)}>{tr("Fix it", "Perbaiki")}</button>
            </div>
          )}
          <Notice msg={msg} />
        </form>
      )}
    </li>
  );
}

function ApproveForm({ sheet, agency, onDone }: { sheet: FactSheetDetail; agency: boolean; onDone: () => void }) {
  const tr = useL();
  const { lang } = useLang();
  const [ref, setRef] = useState("");
  const [msg, setMsg] = useState<Msg>(null);
  async function submit(e: FormEvent) {
    e.preventDefault();
    const r = await api<FactSheetDetail>(`fact-sheets/${sheet.id}/approve`, { method: "POST", body: ref.trim() ? { approval_ref: ref.trim() } : {} });
    if (r.ok) onDone();
    else setMsg({ ok: false, text: errorText(r, lang) });
  }
  return (
    <form onSubmit={submit} className="auth-form mt">
      <p className="wf-text">{tr("All facts are answered. Approve this version so content can use it.", "Semua fakta sudah dijawab. Setujui versi ini agar bisa dipakai di konten.")}</p>
      {agency && (
        <Field id="fs-approval-ref" label={tr("Client's written approval (link)", "Persetujuan tertulis klien (link)")}>
          <input id="fs-approval-ref" value={ref} onChange={(e) => setRef(e.target.value)} required maxLength={500} placeholder="https://" />
        </Field>
      )}
      <Notice msg={msg} />
      <button type="submit" className="btn btn--primary" disabled={agency && !REF_RE.test(ref.trim())}>{tr("Approve fact sheet", "Setujui fact sheet")}</button>
    </form>
  );
}
