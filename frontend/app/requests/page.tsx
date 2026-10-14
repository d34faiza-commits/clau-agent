"use client";

import Link from "next/link";
import { useEffect, useState, type FormEvent } from "react";
import { Card, PageHeader } from "../../components/ui";
import { Field, Notice, SessionGate, StatusPill } from "../../components/WorkflowUi";
import { api, errorText } from "../../lib/auth";
import { L, useL, useLang } from "../../lib/i18n";
import { AGENCY_WRITERS, formatDate, roleFor, useSession, type Agent, type Client, type Page, type WfRequest } from "../../lib/workflow";

export default function RequestsPage() {
  const tr = useL();
  const { lang } = useLang();
  const { me, state } = useSession();
  const [clients, setClients] = useState<Client[]>([]);
  const [filter, setFilter] = useState("");
  const [data, setData] = useState<Page<WfRequest> | null>(null);
  const [error, setError] = useState("");

  async function load(client = filter) {
    const r = await api<Page<WfRequest>>(`requests${client ? `?client_code=${encodeURIComponent(client)}` : ""}`);
    if (r.ok) setData(r.data);
    else setError(errorText(r, lang));
  }
  useEffect(() => {
    document.title = `${tr("Requests", "Permintaan")} · CLAU AI`;
    if (state !== "ready") return;
    api<{ items: Client[] }>("clients").then((r) => r.ok && setClients(r.data.items));
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [state]);

  const header = (
    <PageHeader
      title={<L en="Requests" id="Permintaan" />}
      subtitle={<L en="Content requests and their drafts, reviews, and client approvals. Nothing is ever published from here." id="Permintaan konten beserta draft, review, dan persetujuan klien. Tidak ada yang dipublish dari sini." />}
    />
  );
  if (state !== "ready" || !me) return <>{header}<SessionGate state={state} /></>;
  const canCreate = clients.some((c) => AGENCY_WRITERS.has(roleFor(me, c.client_code)) || roleFor(me, c.client_code) === "client_approver");

  return (
    <>
      {header}
      {error && <p className="auth-notice auth-notice--error" role="alert">{error}</p>}
      <div className="users-layout">
        <Card
          title={<L en="All requests" id="Semua permintaan" />}
          action={
            clients.length > 1 && (
              <select aria-label={tr("Filter by client", "Saring per klien")} className="wf-filter" value={filter} onChange={(e) => { setFilter(e.target.value); load(e.target.value); }}>
                <option value="">{tr("All clients", "Semua klien")}</option>
                {clients.map((c) => <option key={c.client_code} value={c.client_code}>{c.client_code}</option>)}
              </select>
            )
          }
          flush
        >
          {data && data.items.length === 0 ? (
            <p className="muted wf-empty">{tr("No requests yet.", "Belum ada permintaan.")}</p>
          ) : (
            <div className="table-wrap">
              <table className="table">
                <thead>
                  <tr>
                    <th>{tr("Request", "Permintaan")}</th>
                    <th>{tr("Client", "Klien")}</th>
                    <th>{tr("Priority", "Prioritas")}</th>
                    <th>{tr("Min. approval", "Approval min.")}</th>
                    <th>{tr("Status", "Status")}</th>
                  </tr>
                </thead>
                <tbody>
                  {data?.items.map((r) => (
                    <tr key={r.id}>
                      <td>
                        <Link className="cell-strong link" href={`/requests/${r.id}`}>#{r.id} · {r.intent}</Link>
                        <div className="muted cell-sub wf-clip">{r.text}</div>
                      </td>
                      <td>{r.client_code}</td>
                      <td>{r.priority}<div className="muted cell-sub">{r.deadline ? formatDate(r.deadline, lang) : "—"}</div></td>
                      <td>{r.approval_min}</td>
                      <td><StatusPill status={r.status} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
        {canCreate && <NewRequest clients={clients} onCreated={() => load()} />}
      </div>
    </>
  );
}

function NewRequest({ clients, onCreated }: { clients: Client[]; onCreated: () => void }) {
  const tr = useL();
  const { lang } = useLang();
  const [agents, setAgents] = useState<Agent[]>([]);
  const [client, setClient] = useState(clients[0]?.client_code ?? "");
  const [intent, setIntent] = useState("");
  const [text, setText] = useState("");
  const [deadline, setDeadline] = useState("");
  const [impact, setImpact] = useState(1);
  const [risk, setRisk] = useState(1);
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);
  useEffect(() => {
    api<{ agents: Agent[] }>("agents").then((r) => {
      if (!r.ok) return;
      const active = r.data.agents.filter((a) => a.status === "active");
      setAgents(active);
      setIntent(active[0]?.intents[0] ?? "");
    });
  }, []);

  async function submit(e: FormEvent) {
    e.preventDefault();
    const r = await api<WfRequest>("requests", { method: "POST", body: { client_code: client, intent, text, deadline: deadline || null, impact, risk } });
    if (r.ok) {
      setMsg({ ok: true, text: tr(`Request #${r.data.id} created (minimum approval ${r.data.approval_min}).`, `Permintaan #${r.data.id} dibuat (approval minimal ${r.data.approval_min}).`) });
      setText("");
      onCreated();
    } else setMsg({ ok: false, text: errorText(r, lang) });
  }

  return (
    <Card title={<L en="New request" id="Permintaan baru" />}>
      <form onSubmit={submit} className="auth-form">
        <Field id="rq-client" label={tr("Client", "Klien")}>
          <select id="rq-client" value={client} onChange={(e) => setClient(e.target.value)}>
            {clients.map((c) => <option key={c.client_code} value={c.client_code}>{c.client_code}{c.simulation ? " · SIMULASI" : ""}</option>)}
          </select>
        </Field>
        <Field id="rq-intent" label={tr("Type", "Jenis")}>
          <select id="rq-intent" value={intent} onChange={(e) => setIntent(e.target.value)}>
            {agents.flatMap((a) => a.intents.map((i) => <option key={i} value={i}>{i} · {a.display_name}</option>))}
          </select>
        </Field>
        <Field id="rq-text" label={tr("What is needed", "Kebutuhan")}>
          <textarea id="rq-text" value={text} onChange={(e) => setText(e.target.value)} required maxLength={4000} rows={4} />
        </Field>
        <div className="wf-row">
          <Field id="rq-deadline" label={tr("Deadline", "Tenggat")}>
            <input id="rq-deadline" type="date" value={deadline} onChange={(e) => setDeadline(e.target.value)} />
          </Field>
          <Field id="rq-impact" label={tr("Impact (0–3)", "Dampak (0–3)")}>
            <select id="rq-impact" value={impact} onChange={(e) => setImpact(Number(e.target.value))}>
              {[0, 1, 2, 3].map((n) => <option key={n} value={n}>{n}</option>)}
            </select>
          </Field>
          <Field id="rq-risk" label={tr("Risk (0–3)", "Risiko (0–3)")}>
            <select id="rq-risk" value={risk} onChange={(e) => setRisk(Number(e.target.value))}>
              {[0, 1, 2, 3].map((n) => <option key={n} value={n}>{n}</option>)}
            </select>
          </Field>
        </div>
        {risk === 3 && <p className="muted wf-hint">{tr("Risk 3 (crisis, legal, negative review) always needs L3 approval.", "Risiko 3 (krisis, legal, review negatif) selalu butuh approval L3.")}</p>}
        <Notice msg={msg} />
        <button type="submit" className="btn btn--primary" disabled={!client || !intent || !text.trim()}>{tr("Create request", "Buat permintaan")}</button>
      </form>
    </Card>
  );
}
