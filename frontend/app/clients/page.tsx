import Link from "next/link";
import { Monogram, PageHeader, Progress, SimNotice } from "../../components/ui";
import { CLIENTS, CONTENT, PROJECTS, fmtDate } from "../../lib/demo";

export const metadata = { title: "Klien · CLAU" };

export default function Clients() {
  return (
    <>
      <PageHeader
        title="Klien"
        subtitle="Bisnis hospitality yang kontennya dikelola di workspace ini."
        actions={
          <button type="button" className="btn btn--primary" disabled title="Tersedia setelah backend tersambung">
            + Tambah klien
          </button>
        }
      />
      <SimNotice />
      <div className="client-grid">
        {CLIENTS.map((c) => {
          const items = CONTENT.filter((x) => x.client === c.id);
          const done = items.filter((x) => ["approved", "scheduled", "published"].includes(x.status)).length;
          const project = PROJECTS.find((p) => p.client === c.id);
          return (
            <Link key={c.id} href={`/clients/${c.id}`} className="client">
              <div className="client__head">
                <Monogram name={c.name.replace(/^(Villa|Resto|Spa) /, "")} />
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div className="client__name">{c.name}</div>
                  <div className="client__meta">
                    {c.type} · {c.location}
                  </div>
                </div>
                <span className={`badge ${c.status === "active" ? "badge--success" : "badge--warning"}`}>
                  {c.status === "active" ? "Aktif" : "Onboarding"}
                </span>
              </div>
              <dl className="kv">
                <dt>Proyek</dt>
                <dd>{project?.name ?? "—"}</dd>
                <dt>Aktivitas</dt>
                <dd>{fmtDate(c.lastActivity)}</dd>
              </dl>
              <div>
                <div className="client__meta" style={{ marginBottom: 6 }}>
                  Konten selesai
                </div>
                <Progress value={done} total={items.length} />
              </div>
            </Link>
          );
        })}
      </div>
    </>
  );
}
