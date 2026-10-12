"use client";

import { useEffect, useState, type FormEvent } from "react";
import { Card, PageHeader } from "../../components/ui";
import { api, roleOf, type Me } from "../../lib/auth";
import { L, useL } from "../../lib/i18n";

type Setup = { secret: string; otpauth_uri: string };

export default function AccountPage() {
  const tr = useL();
  const [me, setMe] = useState<Me | null>(null);
  const [state, setState] = useState<"loading" | "ready" | "signed-out" | "unavailable">("loading");

  async function load() {
    const r = await api<Me>("auth/me");
    if (r.ok) {
      setMe(r.data);
      setState("ready");
    } else setState(r.status === 401 ? "signed-out" : "unavailable");
  }
  useEffect(() => {
    document.title = `${tr("Account", "Akun")} · CLAU AI`;
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function logout() {
    await api("auth/logout", { method: "POST" });
    window.location.assign("/login");
  }

  if (state === "loading") return <PageHeader title={<L en="Account" id="Akun" />} />;
  if (state !== "ready" || !me)
    return (
      <>
        <PageHeader title={<L en="Account" id="Akun" />} />
        <Card>
          {state === "signed-out" ? (
            <a className="btn btn--primary" href="/login?next=/account">
              <L en="Sign in" id="Masuk" />
            </a>
          ) : (
            <p className="muted">
              <L en="Login is not active on this server yet (preview with sample data)." id="Login belum aktif di server ini (pratinjau dengan data contoh)." />
            </p>
          )}
        </Card>
      </>
    );

  return (
    <>
      <PageHeader
        title={<L en="Account" id="Akun" />}
        subtitle={`${me.user.display_name} · ${me.user.email} · ${roleOf(me)}`}
        actions={
          <button type="button" className="btn btn--secondary" onClick={logout}>
            <L en="Sign out" id="Keluar" />
          </button>
        }
      />
      {me.next !== "ready" && (
        <p className="auth-notice" role="status">
          {me.next === "password_change"
            ? tr("Change your temporary password to continue.", "Ganti password sementara untuk melanjutkan.")
            : tr("Two-factor authentication is required for owners. Turn it on to continue.", "2FA wajib untuk owner. Aktifkan untuk melanjutkan.")}
        </p>
      )}
      <div className="auth-grid">
        <PasswordCard me={me} onDone={setMe} />
        <MfaCard me={me} onDone={setMe} />
      </div>
    </>
  );
}

function PasswordCard({ me, onDone }: { me: Me; onDone: (m: Me) => void }) {
  const tr = useL();
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);

  async function submit(e: FormEvent) {
    e.preventDefault();
    const r = await api<Me>("auth/password", { method: "POST", body: { current_password: current, new_password: next } });
    if (r.ok) {
      onDone(r.data);
      setCurrent("");
      setNext("");
      setMsg({ ok: true, text: tr("Password changed. Other sessions were signed out.", "Password diganti. Sesi lain sudah dikeluarkan.") });
    } else setMsg({ ok: false, text: r.message });
  }

  return (
    <Card title={<L en="Password" id="Password" />}>
      <form onSubmit={submit} className="auth-form">
        <input type="email" autoComplete="username" value={me.user.email} readOnly hidden />
        <div className="field">
          <label htmlFor="current">{tr("Current password", "Password saat ini")}</label>
          <input id="current" type="password" autoComplete="current-password" value={current} onChange={(e) => setCurrent(e.target.value)} required />
        </div>
        <div className="field">
          <label htmlFor="new">{tr("New password (min. 12 characters)", "Password baru (min. 12 karakter)")}</label>
          <input id="new" type="password" autoComplete="new-password" minLength={12} value={next} onChange={(e) => setNext(e.target.value)} required />
        </div>
        {msg && (
          <p className={msg.ok ? "auth-ok" : "auth-error"} role={msg.ok ? "status" : "alert"}>
            {msg.text}
          </p>
        )}
        <button type="submit" className="btn btn--primary" disabled={!current || next.length < 12}>
          {tr("Change password", "Ganti password")}
        </button>
      </form>
    </Card>
  );
}

function MfaCard({ me, onDone }: { me: Me; onDone: (m: Me) => void }) {
  const tr = useL();
  const [setup, setSetup] = useState<Setup | null>(null);
  const [code, setCode] = useState("");
  const [error, setError] = useState("");
  const blocked = me.must_change_password;

  async function start() {
    setError("");
    const r = await api<Setup>("auth/mfa/setup", { method: "POST" });
    if (r.ok) setSetup(r.data);
    else setError(r.message);
  }
  async function confirm(e: FormEvent) {
    e.preventDefault();
    const r = await api<Me>("auth/mfa/confirm", { method: "POST", body: { code } });
    if (r.ok) {
      onDone(r.data);
      setSetup(null);
    } else setError(r.message);
  }

  return (
    <Card title={<L en="Two-factor authentication (2FA)" id="Verifikasi dua langkah (2FA)" />}>
      {me.user.mfa_enabled ? (
        <p className="auth-ok">{tr("On. Sign-in asks for a code from your authenticator app.", "Aktif. Login meminta kode dari aplikasi authenticator.")}</p>
      ) : !setup ? (
        <div className="auth-form">
          <p className="muted">
            {me.mfa_required
              ? tr("Required for your role.", "Wajib untuk peran kamu.")
              : tr("Recommended. Protects your account if the password leaks.", "Disarankan. Melindungi akun bila password bocor.")}{" "}
            {tr("Use Google Authenticator, Microsoft Authenticator, or 1Password.", "Pakai Google Authenticator, Microsoft Authenticator, atau 1Password.")}
          </p>
          {error && <p className="auth-error" role="alert">{error}</p>}
          <button type="button" className="btn btn--primary" onClick={start} disabled={blocked}>
            {tr("Turn on 2FA", "Aktifkan 2FA")}
          </button>
          {blocked && <p className="muted">{tr("Change your temporary password first.", "Ganti password sementara dulu.")}</p>}
        </div>
      ) : (
        <form onSubmit={confirm} className="auth-form">
          <p>
            {tr("1. In your authenticator app, add an account with this setup key:", "1. Di aplikasi authenticator, tambah akun dengan kunci ini:")}
          </p>
          <code className="auth-secret" aria-label={tr("Setup key", "Kunci pengaturan")}>
            {setup.secret.match(/.{1,4}/g)?.join(" ")}
          </code>
          <p className="muted">
            <a href={setup.otpauth_uri}>{tr("Open in authenticator app (on this phone)", "Buka di aplikasi authenticator (di HP ini)")}</a>
          </p>
          <div className="field">
            <label htmlFor="mfa-code">{tr("2. Enter the 6-digit code shown", "2. Masukkan kode 6 digit yang muncul")}</label>
            <input id="mfa-code" inputMode="numeric" autoComplete="one-time-code" maxLength={6} value={code} onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))} required />
          </div>
          {error && <p className="auth-error" role="alert">{error}</p>}
          <button type="submit" className="btn btn--primary" disabled={code.length !== 6}>
            {tr("Confirm", "Konfirmasi")}
          </button>
        </form>
      )}
    </Card>
  );
}
