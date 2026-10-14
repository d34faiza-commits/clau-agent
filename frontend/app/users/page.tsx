"use client";

import { useEffect, useState, type FormEvent } from "react";
import { Card, PageHeader } from "../../components/ui";
import { api, errorText, isOwner, type Me, type Membership, type User } from "../../lib/auth";
import { L, useL, useLang } from "../../lib/i18n";

type Users = { users: User[]; clients: string[] };

// Peran & scope sesuai tabel memberships (core/shared/database-schema.md): peran agency hanya di scope
// agency, approver klien hanya di scope klien, viewer di keduanya. Server menegakkan aturan yang sama.
const ROLES = ["owner", "content_lead", "content_staff", "viewer", "client_approver"] as const;
const AGENCY_ROLES = new Set(["owner", "content_lead", "content_staff"]);
const LEVELS = ["L1", "L2", "L3"] as const;
const ROLE_LABEL: Record<string, [string, string]> = {
  owner: ["Owner", "Owner"],
  content_lead: ["Content lead", "Content lead"],
  content_staff: ["Content staff", "Staf konten"],
  viewer: ["Viewer", "Viewer"],
  client_approver: ["Client approver", "Approver klien"],
};

function scopesFor(role: string, clients: string[]): string[] {
  if (AGENCY_ROLES.has(role)) return ["agency"];
  if (role === "client_approver") return clients;
  return ["agency", ...clients];
}

function tempPassword(): string {
  const words = ["kopi", "sawah", "pantai", "tebing", "kelapa", "bambu", "ombak", "pelangi", "subak", "candi", "lontar", "jukung"];
  const pick = () => words[crypto.getRandomValues(new Uint32Array(1))[0] % words.length];
  const n = 10 + (crypto.getRandomValues(new Uint32Array(1))[0] % 90);
  return `${pick()}-${pick()}-${pick()}-${n}`;
}

export default function UsersPage() {
  const tr = useL();
  const { lang } = useLang();
  const [me, setMe] = useState<Me | null>(null);
  const [data, setData] = useState<Users | null>(null);
  const [state, setState] = useState<"loading" | "ready" | "forbidden" | "signed-out" | "unavailable">("loading");
  const [error, setError] = useState("");

  async function load() {
    const m = await api<Me>("auth/me");
    if (!m.ok) return setState(m.status === 401 ? "signed-out" : "unavailable");
    setMe(m.data);
    if (!isOwner(m.data) || m.data.next !== "ready") return setState("forbidden");
    const r = await api<Users>("users");
    if (r.ok) {
      setData(r.data);
      setState("ready");
    } else setError(errorText(r, lang));
  }
  useEffect(() => {
    document.title = `${tr("Users", "Pengguna")} · CLAU AI`;
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function toggle(u: User) {
    setError("");
    const r = await api<User>(`users/${u.id}/${u.disabled ? "enable" : "disable"}`, { method: "POST" });
    if (r.ok) load();
    else setError(errorText(r, lang));
  }

  const header = <PageHeader title={<L en="Users" id="Pengguna" />} subtitle={<L en="Agency staff and client approvers. Only the owner can manage accounts." id="Staf agency dan approver klien. Hanya owner yang bisa mengelola akun." />} />;
  if (state !== "ready" || !data || !me)
    return (
      <>
        {header}
        {state !== "loading" && (
          <Card>
            <p className="muted">
              {state === "forbidden"
                ? tr("Only an owner with 2FA turned on can manage users.", "Hanya owner dengan 2FA aktif yang bisa mengelola pengguna.")
                : state === "signed-out"
                  ? tr("Please sign in.", "Silakan masuk.")
                  : tr("Sign-in is not active on this server yet (preview with sample data).", "Login belum aktif di server ini (pratinjau dengan data contoh).")}
            </p>
            {error && <p className="auth-error" role="alert">{error}</p>}
          </Card>
        )}
      </>
    );

  return (
    <>
      {header}
      {error && (
        <p className="auth-notice auth-notice--error" role="alert">
          {error}
        </p>
      )}
      <div className="users-layout">
        <Card title={<L en="All accounts" id="Semua akun" />} flush>
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th>{tr("Name", "Nama")}</th>
                  <th>{tr("Role", "Peran")}</th>
                  <th>2FA</th>
                  <th>{tr("Status", "Status")}</th>
                  <th>
                    <span className="sr-only">{tr("Actions", "Aksi")}</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {data.users.map((u) => (
                  <UserRow key={u.id} user={u} self={u.id === me.user.id} clients={data.clients} onToggle={() => toggle(u)} onSaved={load} onError={setError} />
                ))}
              </tbody>
            </table>
          </div>
        </Card>
        <div className="stack">
          <CreateUser clients={data.clients} onCreated={load} />
          <CreateClient onCreated={load} />
        </div>
      </div>
    </>
  );
}

function roleText(m: Membership, lang: string) {
  const label = ROLE_LABEL[m.role]?.[lang === "id" ? 1 : 0] ?? m.role;
  return `${label} · ${m.scope === "agency" ? "agency" : m.scope} · ${m.max_level}`;
}

function UserRow({ user, self, clients, onToggle, onSaved, onError }: { user: User; self: boolean; clients: string[]; onToggle: () => void; onSaved: () => void; onError: (e: string) => void }) {
  const tr = useL();
  const { lang } = useLang();
  const [editing, setEditing] = useState(false);
  const first = user.memberships[0] ?? { scope: "agency", role: "content_staff", max_level: "L1" };
  const [m, setM] = useState<Membership>(first);

  async function save(e: FormEvent) {
    e.preventDefault();
    const r = await api<User>(`users/${user.id}/memberships`, { method: "PUT", body: [m] });
    if (r.ok) {
      setEditing(false);
      onSaved();
    } else onError(errorText(r, lang));
  }

  return (
    <tr>
      <td>
        <div className="users-name">{user.display_name}{self && <span className="muted"> · {tr("you", "kamu")}</span>}</div>
        <div className="muted users-email">{user.email}</div>
      </td>
      <td>
        {editing ? (
          <form onSubmit={save} className="users-edit">
            <MembershipFields value={m} clients={clients} onChange={setM} idPrefix={`edit-${user.id}`} />
            <div className="auth-actions">
              <button type="submit" className="btn btn--primary btn--sm">{tr("Save", "Simpan")}</button>
              <button type="button" className="btn btn--secondary btn--sm" onClick={() => setEditing(false)}>{tr("Cancel", "Batal")}</button>
            </div>
          </form>
        ) : (
          <div className="users-roles">
            {user.memberships.map((x) => (
              <span key={x.scope} className="badge badge--neutral">{roleText(x, lang)}</span>
            ))}
          </div>
        )}
      </td>
      <td>{user.mfa_enabled ? <span className="badge badge--success">{tr("On", "Aktif")}</span> : <span className="badge badge--warning">{tr("Off", "Mati")}</span>}</td>
      <td>{user.disabled ? <span className="badge badge--neutral">{tr("Disabled", "Nonaktif")}</span> : <span className="badge badge--info">{tr("Active", "Aktif")}</span>}</td>
      <td>
        <div className="auth-actions users-row-actions">
          {!editing && (
            <button type="button" className="btn btn--secondary btn--sm" onClick={() => setEditing(true)} aria-label={tr(`Change role of ${user.display_name}`, `Ubah peran ${user.display_name}`)}>
              {tr("Change role", "Ubah peran")}
            </button>
          )}
          {!self && (
            <button type="button" className={`btn btn--sm ${user.disabled ? "btn--secondary" : "btn--danger"}`} onClick={onToggle}>
              {user.disabled ? tr("Enable", "Aktifkan") : tr("Disable", "Nonaktifkan")}
            </button>
          )}
        </div>
      </td>
    </tr>
  );
}

function MembershipFields({ value, clients, onChange, idPrefix }: { value: Membership; clients: string[]; onChange: (m: Membership) => void; idPrefix: string }) {
  const tr = useL();
  const { lang } = useLang();
  const scopes = scopesFor(value.role, clients);
  function setRole(role: string) {
    const next = scopesFor(role, clients);
    onChange({ ...value, role, scope: next.includes(value.scope) ? value.scope : next[0] ?? "", max_level: role === "owner" ? "L3" : value.max_level });
  }
  return (
    <div className="users-fields">
      <div className="field">
        <label htmlFor={`${idPrefix}-role`}>{tr("Role", "Peran")}</label>
        <select id={`${idPrefix}-role`} value={value.role} onChange={(e) => setRole(e.target.value)}>
          {ROLES.map((r) => (
            <option key={r} value={r}>{ROLE_LABEL[r][lang === "id" ? 1 : 0]}</option>
          ))}
        </select>
      </div>
      <div className="field">
        <label htmlFor={`${idPrefix}-scope`}>{tr("For", "Untuk")}</label>
        <select id={`${idPrefix}-scope`} value={value.scope} onChange={(e) => onChange({ ...value, scope: e.target.value })} disabled={scopes.length <= 1}>
          {scopes.length === 0 && <option value="">{tr("No clients yet", "Belum ada klien")}</option>}
          {scopes.map((s) => (
            <option key={s} value={s}>{s === "agency" ? tr("Agency (all clients)", "Agency (semua klien)") : s}</option>
          ))}
        </select>
      </div>
      <div className="field">
        <label htmlFor={`${idPrefix}-level`}>{tr("Max approval", "Approval maks.")}</label>
        <select id={`${idPrefix}-level`} value={value.max_level} onChange={(e) => onChange({ ...value, max_level: e.target.value })}>
          {LEVELS.map((l) => (
            <option key={l} value={l}>{l}</option>
          ))}
        </select>
      </div>
    </div>
  );
}

function CreateUser({ clients, onCreated }: { clients: string[]; onCreated: () => void }) {
  const tr = useL();
  const { lang } = useLang();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [m, setM] = useState<Membership>({ scope: "agency", role: "content_staff", max_level: "L1" });
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);

  async function submit(e: FormEvent) {
    e.preventDefault();
    const r = await api<User>("users", { method: "POST", body: { display_name: name, email, temporary_password: password, locale: lang === "id" ? "id" : "en", memberships: [m] } });
    if (r.ok) {
      setMsg({
        ok: true,
        text: tr(
          `Account created. Send ${email} the temporary password through a separate channel (e.g. a call); they must change it at first sign-in.`,
          `Akun dibuat. Kirim password sementara ke ${email} lewat jalur terpisah (mis. telepon); wajib diganti saat login pertama.`,
        ),
      });
      setName("");
      setEmail("");
      setPassword("");
      onCreated();
    } else setMsg({ ok: false, text: errorText(r, lang) });
  }

  return (
    <Card title={<L en="Add a user" id="Tambah pengguna" />}>
      <form onSubmit={submit} className="auth-form">
        <div className="field">
          <label htmlFor="new-name">{tr("Name", "Nama")}</label>
          <input id="new-name" value={name} onChange={(e) => setName(e.target.value)} required maxLength={120} autoComplete="off" />
        </div>
        <div className="field">
          <label htmlFor="new-email">Email</label>
          <input id="new-email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required autoComplete="off" />
        </div>
        <div className="field">
          <label htmlFor="new-password">{tr("Temporary password (min. 12)", "Password sementara (min. 12)")}</label>
          <div className="users-password">
            <input id="new-password" value={password} onChange={(e) => setPassword(e.target.value)} required minLength={12} autoComplete="off" spellCheck={false} />
            <button type="button" className="btn btn--secondary btn--sm" onClick={() => setPassword(tempPassword())}>
              {tr("Generate", "Buat acak")}
            </button>
          </div>
        </div>
        <MembershipFields value={m} clients={clients} onChange={setM} idPrefix="new" />
        {msg && (
          <p className={msg.ok ? "auth-ok" : "auth-error"} role={msg.ok ? "status" : "alert"}>
            {msg.text}
          </p>
        )}
        <button type="submit" className="btn btn--primary" disabled={!name || !email || password.length < 12 || !m.scope}>
          {tr("Create account", "Buat akun")}
        </button>
      </form>
    </Card>
  );
}

const VERTICAL_LABEL: Record<string, [string, string]> = {
  accommodation: ["Accommodation (villa, hotel)", "Akomodasi (villa, hotel)"],
  "food-beverage": ["Restaurant / cafe", "Restoran / kafe"],
  "spa-wellness": ["Spa & wellness", "Spa & wellness"],
  experience: ["Experience / activity", "Pengalaman / aktivitas"],
  "wedding-event": ["Wedding & event", "Wedding & event"],
  "travel-tour": ["Travel & tour", "Travel & tour"],
};

function CreateClient({ onCreated }: { onCreated: () => void }) {
  const tr = useL();
  const { lang } = useLang();
  const [code, setCode] = useState("");
  const [vertical, setVertical] = useState("accommodation");
  const [business, setBusiness] = useState("");
  const [area, setArea] = useState("");
  const [approverRole, setApproverRole] = useState("owner");
  const [simulation, setSimulation] = useState(false);
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);

  async function submit(e: FormEvent) {
    e.preventDefault();
    const r = await api("clients", { method: "POST", body: { client_code: code, vertical, business_type: business, location_area: area || null, approver_role: approverRole, simulation } });
    if (r.ok) {
      setMsg({ ok: true, text: tr(`Client ${code} added. Now add their approver as a user.`, `Klien ${code} ditambahkan. Sekarang tambahkan approver-nya sebagai pengguna.`) });
      setCode("");
      setBusiness("");
      setArea("");
      onCreated();
    } else setMsg({ ok: false, text: errorText(r, lang) });
  }

  return (
    <Card title={<L en="Add a client" id="Tambah klien" />}>
      <form onSubmit={submit} className="auth-form">
        <div className="field">
          <label htmlFor="cl-code">{tr("Client code (A–Z, 0–9)", "Kode klien (A–Z, 0–9)")}</label>
          <input id="cl-code" value={code} onChange={(e) => setCode(e.target.value.toUpperCase().replace(/[^A-Z0-9]/g, ""))} required minLength={2} maxLength={12} autoComplete="off" />
        </div>
        <div className="field">
          <label htmlFor="cl-vertical">{tr("Business", "Bisnis")}</label>
          <select id="cl-vertical" value={vertical} onChange={(e) => setVertical(e.target.value)}>
            {Object.entries(VERTICAL_LABEL).map(([v, label]) => <option key={v} value={v}>{label[lang === "id" ? 1 : 0]}</option>)}
          </select>
        </div>
        <div className="field">
          <label htmlFor="cl-type">{tr("Type (e.g. villa, cafe)", "Jenis (mis. villa, kafe)")}</label>
          <input id="cl-type" value={business} onChange={(e) => setBusiness(e.target.value)} required maxLength={60} />
        </div>
        <div className="field">
          <label htmlFor="cl-area">{tr("Area (optional)", "Area (opsional)")}</label>
          <input id="cl-area" value={area} onChange={(e) => setArea(e.target.value)} maxLength={120} />
        </div>
        <div className="field">
          <label htmlFor="cl-approver">{tr("Who approves at the client (job title)", "Yang menyetujui di klien (jabatan)")}</label>
          <input id="cl-approver" value={approverRole} onChange={(e) => setApproverRole(e.target.value)} required maxLength={60} />
        </div>
        <label className="wf-check">
          <input type="checkbox" checked={simulation} onChange={(e) => setSimulation(e.target.checked)} />
          {tr("Fictional client for practice (SIMULATION, never approved)", "Klien fiktif untuk latihan (SIMULASI, tidak pernah disetujui)")}
        </label>
        {msg && <p className={msg.ok ? "auth-ok" : "auth-error"} role={msg.ok ? "status" : "alert"}>{msg.text}</p>}
        <button type="submit" className="btn btn--primary" disabled={code.length < 2 || !business.trim() || !approverRole.trim()}>{tr("Add client", "Tambah klien")}</button>
      </form>
    </Card>
  );
}
