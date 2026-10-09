import Link from "next/link";
import { notFound } from "next/navigation";
import ClientTabs from "../../../components/ClientTabs";
import Icon from "../../../components/Icon";
import MemberCard from "../../../components/MemberCard";
import { Card, Empty, Kpi, Progress, SimNotice, StatusBadge } from "../../../components/ui";
import { CLIENTS, CONTENT, PROJECTS } from "../../../lib/demo";
import { D, L } from "../../../lib/i18n";
import { getMember } from "../../../lib/team";

export function generateStaticParams() {
  return CLIENTS.map((c) => ({ id: c.id }));
}

// Hanya klien di data; id lain langsung 404 tanpa render di server.
export const dynamicParams = false;

export async function generateMetadata({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const c = CLIENTS.find((x) => x.id === id);
  return { title: c ? `${c.name} · Clients · CLAU` : "CLAU" };
}

export default async function ClientPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const c = CLIENTS.find((x) => x.id === id);
  if (!c) notFound();
  const items = CONTENT.filter((x) => x.client === c.id).sort((a, b) => b.date.localeCompare(a.date));
  const done = items.filter((x) => ["approved", "scheduled", "published"].includes(x.status)).length;
  const agents = [...new Set(items.map((x) => x.agent))].map((a) => getMember(a)!);
  const projects = PROJECTS.filter((p) => p.client === c.id);

  const contentTable = (
    <Card flush>
      <div className="table-wrap">
        <table className="table">
          <thead>
            <tr>
              <th><L en="Content" id="Konten" /></th>
              <th><L en="Agent" id="Agent" /></th>
              <th><L en="Date" id="Tanggal" /></th>
              <th><L en="Status" id="Status" /></th>
            </tr>
          </thead>
          <tbody>
            {items.map((x) => (
              <tr key={x.id}>
                <td><span className="cell-strong">{x.title}</span><span className="cell-sub">{x.type}</span></td>
                <td className="muted">{getMember(x.agent)?.name}</td>
                <td className="nowrap muted"><D iso={x.date} /></td>
                <td><StatusBadge status={x.status} /></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );

  const soon = (en: string, idText: string) => (
    <Card>
      <Empty icon="inbox" title={<L en={en} id={idText} />} body={<L en="This section fills in once the backend and storage are connected." id="Bagian ini terisi setelah backend dan penyimpanan tersambung." />} />
    </Card>
  );

  return (
    <>
      <Link href="/clients" className="back">
        <Icon name="chevronLeft" size={16} /> <L en="Clients" id="Klien" />
      </Link>
      <div className="profile-head">
        <span className="client__mark" style={{ width: 64, height: 64, fontSize: 24, borderRadius: 18 }}>
          {c.name.replace(/^(Villa|Resto|Spa) Contoh /, "").charAt(0)}
        </span>
        <div>
          <h1 style={{ textTransform: "none", letterSpacing: "-0.01em" }}>{c.name}</h1>
          <p>{c.type} · {c.location}</p>
        </div>
        <div className="profile-head__meta">
          <span className={`badge ${c.status === "active" ? "badge--success" : "badge--warning"}`}>
            {c.status === "active" ? <L en="Active" id="Aktif" /> : <L en="Onboarding" id="Onboarding" />}
          </span>
        </div>
      </div>
      <SimNotice />

      <ClientTabs
        tabs={[
          {
            key: "overview",
            en: "Overview",
            id: "Ringkasan",
            body: (
              <>
                <div className="metric-row">
                  <Kpi label={<L en="Content" id="Konten" />} value={items.length} />
                  <Kpi label={<L en="Completed" id="Selesai" />} value={<Progress value={done} total={items.length} />} />
                  <Kpi label={<L en="AI agents assigned" id="Agent AI ditugaskan" />} value={agents.length} />
                </div>
                <div className="grid-2">
                  <Card title={<L en="Business information" id="Informasi bisnis" />} flush>
                    <dl className="facts">
                      <dt><L en="Business type" id="Jenis bisnis" /></dt><dd>{c.type}</dd>
                      <dt><L en="Location" id="Lokasi" /></dt><dd>{c.location}</dd>
                      <dt><L en="Target audience" id="Target audiens" /></dt><dd>{c.audience}</dd>
                      <dt><L en="Positioning" id="Positioning" /></dt><dd>{c.positioning}</dd>
                      <dt><L en="Services" id="Layanan" /></dt><dd>{c.services.join(", ")}</dd>
                      <dt>USP</dt><dd>{c.usp.join(", ")}</dd>
                    </dl>
                  </Card>
                  <Card title={<L en="Projects" id="Proyek" />} flush>
                    <ul className="list">
                      {projects.map((p) => (
                        <li key={p.id}>
                          <div className="list__main">
                            <span className="list__title">{p.name}</span>
                            <span className="list__sub"><L en="Due" id="Tenggat" /> <D iso={p.due} /></span>
                          </div>
                        </li>
                      ))}
                    </ul>
                  </Card>
                </div>
              </>
            ),
          },
          {
            key: "brand",
            en: "Brand",
            id: "Brand",
            body: (
              <div className="grid-2-even">
                <Card title={<L en="Brand voice" id="Brand voice" />}>
                  <div className="tags">{c.tone.map((t) => <span key={t} className="tag">{t}</span>)}</div>
                </Card>
                <Card title={<L en="Social accounts" id="Akun sosial" />}>
                  <div className="tags">{c.social.map((s) => <span key={s} className="tag">{s} · <L en="not connected" id="belum terhubung" /></span>)}</div>
                </Card>
              </div>
            ),
          },
          { key: "strategy", en: "Strategy", id: "Strategi", body: soon("No strategy document yet", "Belum ada dokumen strategi") },
          { key: "content", en: "Content", id: "Konten", body: contentTable },
          { key: "calendar", en: "Calendar", id: "Kalender", body: <Card><Empty icon="calendar" title={<L en="See the shared calendar" id="Lihat kalender bersama" />} body={<L en="Scheduled content for every client is on the Calendar page." id="Konten terjadwal semua klien ada di halaman Kalender." />} action={<Link href="/calendar" className="btn btn--secondary btn--sm"><L en="Open calendar" id="Buka kalender" /></Link>} /></Card> },
          { key: "media", en: "Media", id: "Media", body: soon("No media yet", "Belum ada media") },
          { key: "campaigns", en: "Campaigns", id: "Campaign", body: soon("No campaigns yet", "Belum ada campaign") },
          { key: "reports", en: "Reports", id: "Laporan", body: soon("No report yet", "Belum ada laporan") },
          {
            key: "team",
            en: "AI Team",
            id: "Tim AI",
            body: <div className="team-grid">{agents.map((m) => <MemberCard key={m.id} m={m} compact />)}</div>,
          },
        ]}
      />
    </>
  );
}
