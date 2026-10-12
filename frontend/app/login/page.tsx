"use client";

import { useEffect, useState, type FormEvent } from "react";
import { Card, PageHeader } from "../../components/ui";
import { api, safeNext, type Me } from "../../lib/auth";
import { L, useL } from "../../lib/i18n";

export default function LoginPage() {
  const tr = useL();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [code, setCode] = useState("");
  const [needCode, setNeedCode] = useState(false);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [next, setNext] = useState("/");

  useEffect(() => {
    document.title = "Login · CLAU AI";
    setNext(safeNext(new URLSearchParams(window.location.search).get("next")));
  }, []);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    const r = await api<Me>("auth/login", { method: "POST", body: { email, password, ...(needCode ? { totp_code: code } : {}) } });
    setBusy(false);
    if (r.ok) {
      window.location.assign(r.data.next === "ready" ? next : "/account");
      return;
    }
    if (r.code === "mfa_required") {
      setNeedCode(true);
      return;
    }
    setError(r.message);
  }

  return (
    <>
      <PageHeader title={<L en="Sign in" id="Masuk" />} subtitle={<L en="Agency staff and client approvers. Accounts are created by the owner." id="Staf agency dan approver klien. Akun dibuat oleh owner." />} />
      <div style={{ maxWidth: 420 }}>
        <Card>
          <form onSubmit={submit} className="auth-form" noValidate>
            <div className="field">
              <label htmlFor="email">Email</label>
              <input id="email" type="email" autoComplete="username" required value={email} onChange={(e) => setEmail(e.target.value)} disabled={needCode} />
            </div>
            <div className="field">
              <label htmlFor="password">
                <L en="Password" id="Password" />
              </label>
              <input id="password" type="password" autoComplete="current-password" required value={password} onChange={(e) => setPassword(e.target.value)} disabled={needCode} />
            </div>
            {needCode && (
              <div className="field">
                <label htmlFor="code">
                  <L en="6-digit code from your authenticator app" id="Kode 6 digit dari aplikasi authenticator" />
                </label>
                <input id="code" inputMode="numeric" autoComplete="one-time-code" pattern="[0-9]*" maxLength={6} required autoFocus value={code} onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))} />
              </div>
            )}
            {error && (
              <p className="auth-error" role="alert">
                {error}
              </p>
            )}
            <button type="submit" className="btn btn--primary" disabled={busy || !email || !password || (needCode && code.length !== 6)}>
              {busy ? tr("Checking…", "Memeriksa…") : needCode ? tr("Verify", "Verifikasi") : tr("Sign in", "Masuk")}
            </button>
          </form>
        </Card>
      </div>
    </>
  );
}
