import Link from "next/link";
import Avatar from "../../components/Avatar";
import { PageHeader, Progress, SimNotice } from "../../components/ui";
import { CLIENTS, CONTENT, formatOf } from "../../lib/demo";
import { D, L } from "../../lib/i18n";
import { getMember } from "../../lib/team";

export const metadata = { title: "Clients · CLAU" };

export default function Clients() {
  return (
    <>
      <PageHeader
        title={<L en="Clients" id="Klien" />}
        subtitle={<L en="Every client gets a dedicated AI marketing team." id="Setiap klien punya tim marketing AI sendiri." />}
        actions={
          <button type="button" className="btn btn--primary" disabled title="Available once the backend is connected">
            + <L en="Add client" id="Tambah klien" />
          </button>
        }
      />
      <SimNotice />
      <div className="client-grid">
        {CLIENTS.map((c) => {
          const items = CONTENT.filter((x) => x.client === c.id);
          const done = items.filter((x) => ["approved", "scheduled", "published"].includes(x.status)).length;
          const agents = [...new Set(items.map((x) => x.agent))].map((a) => getMember(a)!);
          return (
            <Link key={c.id} href={`/clients/${c.id}`} className="client">
              <div className="client__head">
                <span className="client__mark">{c.name.replace(/^(Villa|Resto|Spa) Contoh /, "").charAt(0)}</span>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div className="client__name">{c.name}</div>
                  <div className="client__meta">{c.type} · {c.location}</div>
                </div>
                <span className={`badge ${c.status === "active" ? "badge--success" : "badge--warning"}`}>
                  {c.status === "active" ? <L en="Active" id="Aktif" /> : <L en="Onboarding" id="Onboarding" />}
                </span>
              </div>
              <div className="client__stats">
                <div><b>{items.length}</b><span><L en="Content" id="Konten" /></span></div>
                <div><b>{items.filter((x) => formatOf(x.type) === "reel").length}</b><span>Reels</span></div>
                <div><b>{items.filter((x) => formatOf(x.type) === "story").length}</b><span>Stories</span></div>
              </div>
              <div>
                <div className="client__meta" style={{ marginBottom: 6 }}><L en="Content completed" id="Konten selesai" /></div>
                <Progress value={done} total={items.length} />
              </div>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 8 }}>
                <span className="client__meta"><L en={`AI team: ${agents.length} agents`} id={`Tim AI: ${agents.length} agent`} /></span>
                <span className="stack-avatars">{agents.slice(0, 5).map((m) => <Avatar key={m.id} name={m.name} hue={m.hue} look={m.look} uniform={m.uniform} size="sm" />)}</span>
              </div>
              <div className="client__meta"><L en="Last activity" id="Aktivitas terakhir" />: <D iso={c.lastActivity} /></div>
            </Link>
          );
        })}
      </div>
    </>
  );
}
