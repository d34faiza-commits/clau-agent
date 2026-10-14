"use client";

import type { ReactNode } from "react";
import { Card } from "./ui";
import { useL, useLang } from "../lib/i18n";
import { STATUS_LABEL, STATUS_TONE, safeHref, type SessionState } from "../lib/workflow";

/** Pesan pengganti isi halaman saat belum login / backend belum aktif (pratinjau VPS 1). */
export function SessionGate({ state, error }: { state: SessionState; error?: string }) {
  const tr = useL();
  if (state === "loading") return null;
  const text = {
    "signed-out": tr("Please sign in.", "Silakan masuk."),
    setup: tr("Finish your account setup first (new password, 2FA for owners).", "Selesaikan pengaturan akun dulu (password baru, 2FA untuk owner)."),
    unavailable: tr("Sign-in is not active on this server yet (preview with sample data).", "Login belum aktif di server ini (pratinjau dengan data contoh)."),
    ready: "",
  }[state];
  return (
    <Card>
      <p className="muted">{text}</p>
      {error && <p className="auth-error" role="alert">{error}</p>}
    </Card>
  );
}

export function StatusPill({ status }: { status: string }) {
  const { lang } = useLang();
  const label = STATUS_LABEL[status]?.[lang === "id" ? 1 : 0] ?? status;
  return <span className={`badge badge--${STATUS_TONE[status] ?? "neutral"}`}>{label}</span>;
}

export function RefLink({ value }: { value: string | null }) {
  if (!value) return <span className="muted">—</span>;
  const href = safeHref(value);
  return href ? (
    <a className="link" href={href} target="_blank" rel="noopener noreferrer nofollow">{value}</a>
  ) : (
    <code className="wf-ref">{value}</code>
  );
}

export function Notice({ msg }: { msg: { ok: boolean; text: string } | null }) {
  if (!msg) return null;
  return (
    <p className={msg.ok ? "auth-ok" : "auth-error"} role={msg.ok ? "status" : "alert"}>
      {msg.text}
    </p>
  );
}

export function Field({ id, label, children, hint }: { id: string; label: ReactNode; children: ReactNode; hint?: ReactNode }) {
  return (
    <div className="field">
      <label htmlFor={id}>{label}</label>
      {children}
      {hint && <span className="muted wf-hint">{hint}</span>}
    </div>
  );
}
