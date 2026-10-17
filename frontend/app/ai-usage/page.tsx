"use client";

import { useCallback, useEffect, useState, type FormEvent } from "react";
import { Card, Kpi, PageHeader } from "../../components/ui";
import { Field, Notice } from "../../components/WorkflowUi";
import { api, errorText, isOwner, type Me } from "../../lib/auth";
import { currentMonth, usd, type AiBudget, type AiUsage } from "../../lib/ai";
import { L, useL, useLang } from "../../lib/i18n";
import { formatDate, type Client } from "../../lib/workflow";

type State = "loading" | "ready" | "forbidden" | "signed-out" | "unavailable";
const MONTH_RE = /^\d{4}-(0[1-9]|1[0-2])$/;

/** Pemakaian & batas biaya AI (owner). Tanpa batas global bulan berjalan, AI menolak semua job (fail closed). */
export default function AiUsagePage() {
  const tr = useL();
  const { lang } = useLang();
  const [state, setState] = useState<State>("loading");
  const [month, setMonth] = useState(currentMonth());
  const [usage, setUsage] = useState<AiUsage | null>(null);
  const [clients, setClients] = useState<Client[]>([]);
  const [error, setError] = useState("");

  const load = useCallback(async (m: string) => {
    const r = await api<AiUsage>(`ai-usage?month=${m}`);
    if (r.ok) {
      setUsage(r.data);
      setError("");
    } else setError(errorText(r, lang));
  }, [lang]);

  useEffect(() => {
    document.title = `${tr("AI usage", "Pemakaian AI")} · CLAU AI`;
    api<Me>("auth/me").then(async (m) => {
      if (!m.ok) return setState(m.status === 401 ? "signed-out" : "unavailable");
      if (!isOwner(m.data) || m.data.next !== "ready") return setState("forbidden");
      setState("ready");
      const c = await api<{ items: Client[] }>("clients");
      if (c.ok) setClients(c.data.items);
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  useEffect(() => {
    if (state === "ready" && MONTH_RE.test(month)) load(month);
  }, [state, month, load]);

  const header = (
    <PageHeader
      title={<L en="AI usage & budget" id="Pemakaian & batas biaya AI" />}
      subtitle={<L en="What the AI costs per month, per client and per agent. Only the owner sees this page." id="Biaya AI per bulan, per klien, dan per agent. Hanya owner yang melihat halaman ini." />}
    />
  );
  if (state !== "ready")
    return (
      <>
        {header}
        {state !== "loading" && (
          <Card>
            <p className="muted">
              {state === "forbidden"
                ? tr("Only an owner with 2FA turned on can see AI costs.", "Hanya owner dengan 2FA aktif yang bisa melihat biaya AI.")
                : state === "signed-out"
                  ? tr("Please sign in.", "Silakan masuk.")
                  : tr("Sign-in is not active on this server yet (preview with sample data).", "Login belum aktif di server ini (pratinjau dengan data contoh).")}
            </p>
          </Card>
        )}
      </>
    );

  const global = usage?.budgets.find((b) => b.scope === "global");
  return (
    <>
      {header}
      {error && <p className="auth-notice auth-notice--error" role="alert">{error}</p>}
      <div className="wf-row">
        <Field id="ai-month" label={tr("Month (WITA)", "Bulan (WITA)")}>
          <input id="ai-month" type="month" value={month} onChange={(e) => setMonth(e.target.value)} />
        </Field>
      </div>
      {usage && (
        <>
          <div className="kpis">
            <Kpi label={tr("Spent", "Terpakai")} value={usd(usage.total_micro_usd)} hint={tr(`${usage.calls} AI calls`, `${usage.calls} panggilan AI`)} />
            <Kpi
              label={tr("Monthly limit", "Batas bulanan")}
              value={global ? usd(global.limit_micro_usd) : "—"}
              hint={global ? tr(`warning at ${global.alert_at_pct}%`, `peringatan di ${global.alert_at_pct}%`) : tr("Not set: AI is blocked", "Belum diatur: AI diblokir")}
            />
            <Kpi label={tr("Left", "Sisa")} value={global ? usd(Math.max(global.limit_micro_usd - global.spent_micro_usd, 0)) : "—"} />
          </div>
          {!global && month === currentMonth() && (
            <p className="auth-notice auth-notice--error" role="alert">
              {tr("No global limit for this month: every AI request is refused until you set one below.", "Belum ada batas global bulan ini: semua permintaan AI ditolak sampai kamu mengaturnya di bawah.")}
            </p>
          )}
          <div className="users-layout">
            <div className="stack">
              <Card title={<L en="Limits" id="Batas" />} flush>
                {usage.budgets.length === 0 ? (
                  <p className="muted wf-empty">{tr("No limits for this month yet.", "Belum ada batas untuk bulan ini.")}</p>
                ) : (
                  <div className="table-wrap">
                    <table className="table">
                      <thead><tr><th>Scope</th><th>{tr("Spent / limit", "Terpakai / batas")}</th><th>{tr("Updated", "Diubah")}</th></tr></thead>
                      <tbody>
                        {usage.budgets.map((b) => {
                          const pct = Math.min(100, Math.round((b.spent_micro_usd * 100) / b.limit_micro_usd));
                          return (
                            <tr key={b.scope}>
                              <td>{b.scope === "global" ? tr("All clients", "Semua klien") : b.scope}</td>
                              <td>
                                {usd(b.spent_micro_usd)} / {usd(b.limit_micro_usd)} ({pct}%)
                                {b.alert && <span className="badge badge--warning"> {tr("near limit", "hampir habis")}</span>}
                                <div className={`ai-meter${b.alert ? " ai-meter--alert" : ""}`} role="img" aria-label={`${pct}%`}><span style={{ width: `${pct}%` }} /></div>
                              </td>
                              <td className="muted">{formatDate(b.updated_at, lang)}</td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                )}
              </Card>
              <Breakdown title={tr("Per client", "Per klien")} column={tr("Client", "Klien")} rows={usage.by_client.map((c) => [c.client_code, c.cost_micro_usd, c.calls])} />
              <Breakdown title={tr("Per agent", "Per agent")} column="Agent" rows={usage.by_agent.map((a) => [a.agent_id, a.cost_micro_usd, a.calls])} />
            </div>
            <div className="stack">
              <BudgetForm month={month} clients={clients} budgets={usage.budgets} onDone={() => load(month)} />
            </div>
          </div>
        </>
      )}
    </>
  );
}

function Breakdown({ title, column, rows }: { title: string; column: string; rows: [string, number, number][] }) {
  const tr = useL();
  return (
    <Card title={title} flush>
      {rows.length === 0 ? (
        <p className="muted wf-empty">{tr("No AI calls this month.", "Belum ada panggilan AI bulan ini.")}</p>
      ) : (
        <div className="table-wrap">
          <table className="table">
            <thead><tr><th>{column}</th><th>{tr("Cost", "Biaya")}</th><th>{tr("Calls", "Panggilan")}</th></tr></thead>
            <tbody>{rows.map(([k, cost, calls]) => <tr key={k}><td>{k}</td><td>{usd(cost)}</td><td>{calls}</td></tr>)}</tbody>
          </table>
        </div>
      )}
    </Card>
  );
}

function BudgetForm({ month, clients, budgets, onDone }: { month: string; clients: Client[]; budgets: AiBudget[]; onDone: () => void }) {
  const tr = useL();
  const { lang } = useLang();
  const [scope, setScope] = useState("global");
  const [dollars, setDollars] = useState("");
  const [alertPct, setAlertPct] = useState("80");
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);
  const current = budgets.find((b) => b.scope === scope);
  const micro = Math.round(Number(dollars) * 1_000_000);
  const valid = /^\d+(\.\d{1,2})?$/.test(dollars.trim()) && micro >= 10_000 && micro <= 100_000_000_000;

  async function submit(e: FormEvent) {
    e.preventDefault();
    const r = await api<AiBudget>("ai-budgets", { method: "PUT", body: { scope, month, limit_micro_usd: micro, alert_at_pct: Number(alertPct) } });
    if (r.ok) {
      setMsg({ ok: true, text: tr("Limit saved.", "Batas tersimpan.") });
      setDollars("");
      onDone();
    } else setMsg({ ok: false, text: errorText(r, lang) });
  }

  return (
    <Card title={<L en="Set a limit" id="Atur batas" />}>
      <form onSubmit={submit} className="auth-form">
        <Field id="b-scope" label={tr("For", "Untuk")}>
          <select id="b-scope" value={scope} onChange={(e) => setScope(e.target.value)}>
            <option value="global">{tr("All clients (required)", "Semua klien (wajib)")}</option>
            {clients.map((c) => <option key={c.client_code} value={c.client_code}>{c.client_code}{c.simulation ? " · SIMULASI" : ""}</option>)}
          </select>
        </Field>
        <Field id="b-limit" label={tr(`Limit for ${month} (USD)`, `Batas ${month} (USD)`)}
          hint={current ? tr(`Now ${usd(current.limit_micro_usd)}.`, `Sekarang ${usd(current.limit_micro_usd)}.`) : tr("Minimum $0.01.", "Minimal $0,01.")}>
          <input id="b-limit" inputMode="decimal" value={dollars} onChange={(e) => setDollars(e.target.value)} placeholder="20.00" required />
        </Field>
        <Field id="b-alert" label={tr("Warn at (%)", "Peringatan di (%)")}>
          <input id="b-alert" type="number" min={1} max={100} value={alertPct} onChange={(e) => setAlertPct(e.target.value)} required />
        </Field>
        <Notice msg={msg} />
        <button type="submit" className="btn btn--primary" disabled={!valid || !MONTH_RE.test(month)}>{tr("Save limit", "Simpan batas")}</button>
        <p className="muted wf-hint">
          <L en="When a limit is reached, new AI requests are refused until next month or until you raise it. Test mode (fake AI) costs $0." id="Bila batas tercapai, permintaan AI baru ditolak sampai bulan depan atau sampai batas dinaikkan. Mode uji (AI tiruan) biayanya $0." />
        </p>
      </form>
    </Card>
  );
}
