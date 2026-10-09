import type { ReactNode } from "react";
import Icon, { type IconName } from "./Icon";
import { L } from "../lib/i18n";
import { STATUS, type ContentStatus } from "../lib/demo";

export function PageHeader({ title, subtitle, actions }: { title: ReactNode; subtitle?: ReactNode; actions?: ReactNode }) {
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
      <span className="sim__tag">
        <L en="SIMULATION" id="SIMULASI" />
      </span>
      <L
        en="Sample data for UI preview. Business names are fictional and no AI model is called yet."
        id="Data contoh untuk pratinjau UI. Nama bisnis fiktif dan belum ada model AI yang dipanggil."
      />
    </div>
  );
}

export function Card({ title, action, children, flush }: { title?: ReactNode; action?: ReactNode; children: ReactNode; flush?: boolean }) {
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

export function Kpi({ label, value, hint }: { label: ReactNode; value: ReactNode; hint?: ReactNode }) {
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
  return (
    <span className={`badge badge--${s.tone}`}>
      <L en={s.en} id={s.id} />
    </span>
  );
}

export function AgentStatus({ status }: { status: "active" | "planned" }) {
  return (
    <span className={`dot-label dot-label--${status === "active" ? "success" : "offline"}`}>
      {status === "active" ? <L en="Active" id="Aktif" /> : <L en="Not active" id="Belum aktif" />}
    </span>
  );
}

export function Level({ level }: { level: string }) {
  return <span className="level">{level}</span>;
}

export function Progress({ value, total }: { value: number; total: number }) {
  const pct = total ? Math.round((value / total) * 100) : 0;
  return (
    <span className="progress">
      <span className="progress__bar">
        <span style={{ width: `${pct}%` }} />
      </span>
      <span className="progress__text">
        {value}/{total}
      </span>
    </span>
  );
}

export function Empty({ icon, title, body, action, heading: H = "h3" }: { icon: IconName; title: ReactNode; body: ReactNode; action?: ReactNode; heading?: "h1" | "h3" }) {
  return (
    <div className="empty">
      <span className="empty__icon">
        <Icon name={icon} size={22} />
      </span>
      <H>{title}</H>
      <p>{body}</p>
      {action}
    </div>
  );
}
