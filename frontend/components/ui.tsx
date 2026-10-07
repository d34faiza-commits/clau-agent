import type { ReactNode } from "react";
import Icon, { type IconName } from "./Icon";
import { STATUS, type ContentStatus } from "../lib/demo";

export function PageHeader({ title, subtitle, actions }: { title: string; subtitle?: string; actions?: ReactNode }) {
  return (
    <div className="page-head">
      <div>
        <h1>{title}</h1>
        {subtitle && <p>{subtitle}</p>}
      </div>
      {actions && <div className="page-head__actions">{actions}</div>}
    </div>
  );
}

export function SimNotice() {
  return (
    <div className="sim" role="note">
      <span className="sim__tag">SIMULASI</span>
      Data di halaman ini adalah contoh fiktif untuk pratinjau UI, bukan hasil bisnis nyata.
    </div>
  );
}

export function Card({ title, action, children, flush }: { title?: string; action?: ReactNode; children: ReactNode; flush?: boolean }) {
  return (
    <section className={`panel${flush ? " panel--flush" : ""}`}>
      {(title || action) && (
        <header className="panel__head">
          {title && <h2>{title}</h2>}
          {action}
        </header>
      )}
      {children}
    </section>
  );
}

export function Kpi({ label, value, hint }: { label: string; value: ReactNode; hint?: string }) {
  return (
    <div className="kpi">
      <span className="kpi__label">{label}</span>
      <span className="kpi__value">{value}</span>
      {hint && <span className="kpi__hint">{hint}</span>}
    </div>
  );
}

export function StatusBadge({ status }: { status: ContentStatus }) {
  const s = STATUS[status];
  return <span className={`badge badge--${s.tone}`}>{s.label}</span>;
}

export function AgentStatus({ status }: { status: "active" | "planned" }) {
  return (
    <span className={`dot-label dot-label--${status === "active" ? "success" : "offline"}`}>
      {status === "active" ? "Aktif" : "Belum aktif"}
    </span>
  );
}

export function Level({ level }: { level: string }) {
  return (
    <span className="level" title={`Level persetujuan ${level}`}>
      {level}
    </span>
  );
}

export function Monogram({ name, size = "md", muted }: { name: string; size?: "sm" | "md" | "lg"; muted?: boolean }) {
  return (
    <span className={`mono mono--${size}${muted ? " mono--muted" : ""}`} aria-hidden="true">
      {name.charAt(0)}
    </span>
  );
}

export function Progress({ value, total }: { value: number; total: number }) {
  const pct = total ? Math.round((value / total) * 100) : 0;
  return (
    <span className="progress" title={`${value} dari ${total} konten`}>
      <span className="progress__bar">
        <span style={{ width: `${pct}%` }} />
      </span>
      <span className="progress__text">
        {value}/{total}
      </span>
    </span>
  );
}

export function Empty({ icon, title, body, action }: { icon: IconName; title: string; body: string; action?: ReactNode }) {
  return (
    <div className="empty">
      <span className="empty__icon">
        <Icon name={icon} size={22} />
      </span>
      <h3>{title}</h3>
      <p>{body}</p>
      {action}
    </div>
  );
}
