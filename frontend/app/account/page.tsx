"use client";

import { useEffect, useState, type FormEvent } from "react";
import { Card, PageHeader } from "../../components/ui";
import { api, errorText, isOwner, roleOf, type Me } from "../../lib/auth";
import { L, useL, useLang } from "../../lib/i18n";

type Setup = { secret: string; otpauth_uri: string; qr_svg: string };

export default function AccountPage() {
  const tr = useL();
  const { lang } = useLang();
  const [me, setMe] = useState<Me | null>(null);
  const [state, setState] = useState<"loading" | "ready" | "signed-out" | "unavailable">("loading");
  const [codes, setCodes] = useState<string[] | null>(null);
  const [error, setError] = useState("");

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

  async function signOut(all: boolean) {
    setError("");
    const r = await api(all ? "auth/logout-all" : "auth/logout", { method: "POST" });
    // Gagal = jangan pura-pura sudah keluar (komputer bersama): tampilkan error, sesi masih aktif.
    if (!r.ok) setError(errorText(r, lang));
    else window.location.assign("/login");
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
              <L en="Sign-in is not active on this server yet (preview with sample data)." id="Login belum aktif di server ini (pratinjau dengan data contoh)." />
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
          <>
            {isOwner(me) && me.next === "ready" && (
              <a className="btn btn--secondary" href="/users">
                <L en="Manage users" id="Kelola pengguna" />
              </a>
            )}
            <button type="button" className="btn btn--secondary" onClick={() => signOut(false)}>
              <L en="Sign out" id="Keluar" />
            </button>
          </>
        }
      />
      {error && (
        <p className="auth-notice auth-notice--error" role="alert">
          {error}
        </p>
      )}
      {me.next !== "ready" && !codes && (
        <p className="auth-notice" role="status">
          {me.next === "password_change"
            ? tr("Change your temporary password to continue.", "Ganti password sementara untuk melanjutkan.")
            : tr("Two-factor authentication is required for owners. Turn it on to continue.", "2FA wajib untuk owner. Aktifkan untuk melanjutkan.")}
        </p>
      )}
      {codes && <RecoveryCodes codes={codes} onDone={() => setCodes(null)} />}
      <div className="auth-grid">
        <PasswordCard me={me} onDone={setMe} />
        <MfaCard me={me} onDone={(m, c) => (setMe(m), setCodes(c))} onCodes={setCodes} />
        <SessionsCard me={me} onSignOutAll={() => signOut(true)} />
      </div>
    </>
  );
}

function PasswordCard({ me, onDone }: { me: Me; onDone: (m: Me) => void }) {
  const tr = useL();
  const { lang } = useLang();
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
      setMsg({ ok: true, text: tr("Password changed. Other devices were signed out.", "Password diganti. Perangkat lain sudah dikeluarkan.") });
    } else setMsg({ ok: false, text: errorText(r, lang) });
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
        <p className="muted auth-hint">{tr("Tip: three or four unrelated words, e.g. kopi-sawah-pelangi-27.", "Tips: tiga-empat kata acak, mis. kopi-sawah-pelangi-27.")}</p>
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

function MfaCard({ me, onDone, onCodes }: { me: Me; onDone: (m: Me, codes: string[]) => void; onCodes: (c: string[]) => void }) {
  const tr = useL();
  const { lang } = useLang();
  const [setup, setSetup] = useState<Setup | null>(null);
  const [code, setCode] = useState("");
  const [password, setPassword] = useState("");
  const [showKey, setShowKey] = useState(false);
  const [error, setError] = useState("");
  const blocked = me.must_change_password;

  async function start() {
    setError("");
    const r = await api<Setup>("auth/mfa/setup", { method: "POST" });
    if (r.ok) setSetup(r.data);
    else setError(errorText(r, lang));
  }
  async function confirm(e: FormEvent) {
    e.preventDefault();
    const r = await api<Me & { recovery_codes: string[] }>("auth/mfa/confirm", { method: "POST", body: { code } });
    if (r.ok) {
      setSetup(null);
      onDone(r.data, r.data.recovery_codes);
    } else setError(errorText(r, lang));
  }
  async function regenerate(e: FormEvent) {
    e.preventDefault();
    setError("");
    const r = await api<{ recovery_codes: string[] }>("auth/mfa/recovery-codes", { method: "POST", body: { password } });
    if (r.ok) {
      setPassword("");
      onCodes(r.data.recovery_codes);
    } else setError(errorText(r, lang));
  }

  if (me.user.mfa_enabled)
    return (
      <Card title={<L en="Two-factor authentication (2FA)" id="Verifikasi dua langkah (2FA)" />}>
        <form onSubmit={regenerate} className="auth-form">
          <p className="auth-ok">{tr("On. Sign-in asks for a code from your authenticator app.", "Aktif. Login meminta kode dari aplikasi authenticator.")}</p>
          <p className="muted">
            {tr(`Backup codes left: ${me.recovery_codes_left} of 10.`, `Sisa kode cadangan: ${me.recovery_codes_left} dari 10.`)}{" "}
            {me.recovery_codes_left <= 3 && tr("Make new ones soon.", "Segera buat yang baru.")}
          </p>
          <div className="field">
            <label htmlFor="regen-password">{tr("Password, to make new backup codes", "Password, untuk membuat kode cadangan baru")}</label>
            <input id="regen-password" type="password" autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} required />
          </div>
          {error && <p className="auth-error" role="alert">{error}</p>}
          <button type="submit" className="btn btn--secondary" disabled={!password}>
            {tr("Make new backup codes", "Buat kode cadangan baru")}
          </button>
        </form>
      </Card>
    );

  return (
    <Card title={<L en="Two-factor authentication (2FA)" id="Verifikasi dua langkah (2FA)" />}>
      {!setup ? (
        <div className="auth-form">
          <p className="muted">
            {me.mfa_required ? tr("Required for your role.", "Wajib untuk peran kamu.") : tr("Recommended. Protects your account if the password leaks.", "Disarankan. Melindungi akun bila password bocor.")}{" "}
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
          <p>{tr("1. Scan this QR code with your authenticator app.", "1. Pindai QR code ini dengan aplikasi authenticator.")}</p>
          <img className="auth-qr" src={setup.qr_svg} alt={tr("QR code for your authenticator app", "QR code untuk aplikasi authenticator")} width={180} height={180} />
          <button type="button" className="link-btn auth-link" onClick={() => setShowKey(!showKey)} aria-expanded={showKey}>
            {showKey ? tr("Hide setup key", "Sembunyikan kunci") : tr("Can't scan? Enter a setup key instead", "Tidak bisa pindai? Ketik kunci saja")}
          </button>
          {showKey && (
            <code className="auth-secret" aria-label={tr("Setup key", "Kunci pengaturan")}>
              {setup.secret.match(/.{1,4}/g)?.join(" ")}
            </code>
          )}
          <div className="field">
            <label htmlFor="mfa-code">{tr("2. Enter the 6-digit code shown in the app", "2. Masukkan kode 6 digit yang muncul di aplikasi")}</label>
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

function RecoveryCodes({ codes, onDone }: { codes: string[]; onDone: () => void }) {
  const tr = useL();
  const [copied, setCopied] = useState<"" | "ok" | "manual">("");
  const text = codes.join("\n");

  async function copy() {
    try {
      await navigator.clipboard.writeText(text);
      setCopied("ok");
    } catch {
      setCopied("manual");
    }
  }

  return (
    <section className="auth-codes" aria-labelledby="codes-title">
      <h2 id="codes-title">{tr("Save your 10 backup codes now", "Simpan 10 kode cadangan sekarang")}</h2>
      <p>
        {tr(
          "Each code signs you in once if you lose your phone. They are shown only this time: store them in a password manager or print and keep them somewhere safe.",
          "Setiap kode bisa dipakai login sekali bila HP hilang. Kode hanya ditampilkan kali ini: simpan di password manager, atau cetak dan simpan di tempat aman.",
        )}
      </p>
      <ol className="auth-code-list">
        {codes.map((c) => (
          <li key={c}>
            <code>{c}</code>
          </li>
        ))}
      </ol>
      {copied === "manual" && <textarea className="auth-code-text" readOnly value={text} rows={5} aria-label={tr("Backup codes", "Kode cadangan")} onFocus={(e) => e.currentTarget.select()} />}
      <div className="auth-actions">
        <button type="button" className="btn btn--secondary" onClick={copy}>
          {copied === "ok" ? tr("Copied", "Tersalin") : tr("Copy codes", "Salin kode")}
        </button>
        <button type="button" className="btn btn--primary" onClick={onDone}>
          {tr("I've saved them", "Sudah saya simpan")}
        </button>
      </div>
    </section>
  );
}

function SessionsCard({ me, onSignOutAll }: { me: Me; onSignOutAll: () => void }) {
  const tr = useL();
  const [confirming, setConfirming] = useState(false);
  return (
    <Card title={<L en="Signed-in devices" id="Perangkat yang login" />}>
      <div className="auth-form">
        <p>
          <span className="auth-count">{me.active_sessions}</span> {tr("active sessions, including this one.", "sesi aktif, termasuk yang ini.")}
        </p>
        <p className="muted">{tr("Lost a laptop or phone? Sign out everywhere, then change your password.", "Laptop atau HP hilang? Keluar dari semua perangkat, lalu ganti password.")}</p>
        {confirming ? (
          <div className="auth-actions">
            <button type="button" className="btn btn--danger" onClick={onSignOutAll}>
              {tr("Yes, sign out everywhere", "Ya, keluar dari semua")}
            </button>
            <button type="button" className="btn btn--secondary" onClick={() => setConfirming(false)}>
              {tr("Cancel", "Batal")}
            </button>
          </div>
        ) : (
          <button type="button" className="btn btn--secondary" onClick={() => setConfirming(true)}>
            {tr("Sign out of all devices", "Keluar dari semua perangkat")}
          </button>
        )}
      </div>
    </Card>
  );
}
