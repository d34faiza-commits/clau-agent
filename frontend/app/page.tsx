import Link from "next/link";
import { AgentStatus, Card, Kpi, Level, Monogram, PageHeader, Progress, SimNotice, StatusBadge } from "../components/ui";
import { CLIENTS, CONTENT, PROJECTS, SIM_DATE, clientName, fmtDate } from "../lib/demo";
import { getTeam } from "../lib/team";

export default function Dashboard() {
  const team = getTeam();
  const pending = CONTENT.filter((c) => c.status === "ai_review" || c.status === "human_review");
  const published = CONTENT.filter((c) => c.status === "published");
  const upcoming = CONTENT.filter((c) => (c.status === "scheduled" || c.status === "approved") && c.date >= SIM_DATE)
    .sort((a, b) => a.date.localeCompare(b.date))
    .slice(0, 5);
  const agentLoad = team
    .map((m) => ({ m, n: CONTENT.filter((c) => c.agent === m.id && c.status !== "published").length }))
    .filter((x) => x.m.status === "active")
    .sort((a, b) => b.n - a.n)
    .slice(0, 5);

  return (
    <>
      <PageHeader
        title="Selamat datang kembali"
        subtitle={`Ringkasan workspace per ${fmtDate(SIM_DATE)}`}
        actions={
          <Link href="/content?new=1" className="btn btn--primary">
            + Buat konten
          </Link>
        }
      />
      <SimNotice />

      <div className="kpis">
        <Kpi label="Klien aktif" value={CLIENTS.filter((c) => c.status === "active").length} hint={`${CLIENTS.length} klien total`} />
        <Kpi label="Konten bulan ini" value={CONTENT.length} hint="Semua status" />
        <Kpi label="Menunggu review" value={pending.length} hint="Cek otomatis + review manusia" />
        <Kpi label="Tayang" value={published.length} hint="Dipublish oleh tim" />
      </div>

      <div className="grid-2">
        <div className="stack">
          <Card title="Proyek terbaru" action={<Link href="/projects" className="link">Lihat semua</Link>} flush>
            <div className="table-wrap">
              <table className="table">
                <thead>
                  <tr>
                    <th>Klien</th>
                    <th>Proyek</th>
                    <th>Progres</th>
                    <th>Tenggat</th>
                  </tr>
                </thead>
                <tbody>
                  {PROJECTS.map((p) => {
                    const items = CONTENT.filter((c) => c.project === p.id);
                    const done = items.filter((c) => ["approved", "scheduled", "published"].includes(c.status)).length;
                    return (
                      <tr key={p.id}>
                        <td className="cell-strong">{clientName(p.client)}</td>
                        <td>{p.name}</td>
                        <td>
                          <Progress value={done} total={items.length} />
                        </td>
                        <td className="nowrap muted">{fmtDate(p.due)}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </Card>

          <Card title="Perlu tindakan" action={<Link href="/content" className="link">Buka konten</Link>} flush>
            <ul className="list">
              {pending.map((c) => (
                <li key={c.id}>
                  <div className="list__main">
                    <span className="list__title">{c.title}</span>
                    <span className="list__sub">
                      {c.type} · {clientName(c.client)}
                    </span>
                  </div>
                  <Level level={c.level} />
                  <StatusBadge status={c.status} />
                </li>
              ))}
            </ul>
          </Card>
        </div>

        <div className="stack">
          <Card title="Aktivitas agent AI" action={<Link href="/agents" className="link">Semua agent</Link>} flush>
            <ul className="list">
              {agentLoad.map(({ m, n }) => (
                <li key={m.id}>
                  <Monogram name={m.name} size="sm" />
                  <div className="list__main">
                    <span className="list__title">{m.name}</span>
                    <span className="list__sub">{m.role}</span>
                  </div>
                  <span className="muted nowrap">{n} draft</span>
                </li>
              ))}
            </ul>
          </Card>

          <Card title="Jadwal tayang" action={<Link href="/calendar" className="link">Kalender</Link>} flush>
            <ul className="list">
              {upcoming.map((c) => {
                const [, mo, d] = c.date.split("-");
                return (
                  <li key={c.id}>
                    <span className="date-chip">
                      <b>{Number(d)}</b>
                      <span>{["", "Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"][Number(mo)]}</span>
                    </span>
                    <div className="list__main">
                      <span className="list__title">{c.title}</span>
                      <span className="list__sub">
                        {c.type} · {clientName(c.client)}
                      </span>
                    </div>
                  </li>
                );
              })}
            </ul>
          </Card>

          <Card title="Status tim">
            <div className="kv">
              <dt>Agent aktif</dt>
              <dd>
                <AgentStatus status="active" /> {team.filter((m) => m.status === "active").length}
              </dd>
              <dt>Belum aktif</dt>
              <dd>
                <AgentStatus status="planned" /> {team.filter((m) => m.status === "planned").length}
              </dd>
            </div>
          </Card>
        </div>
      </div>
    </>
  );
}
