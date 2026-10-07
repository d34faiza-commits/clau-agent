import Link from "next/link";
import { notFound } from "next/navigation";
import Icon from "../../../components/Icon";
import { Card, Empty, Monogram, SimNotice, StatusBadge } from "../../../components/ui";
import { CLIENTS, CONTENT, fmtDate } from "../../../lib/demo";
import { getMember } from "../../../lib/team";

export function generateStaticParams() {
  return CLIENTS.map((c) => ({ id: c.id }));
}

export default async function ClientPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const c = CLIENTS.find((x) => x.id === id);
  if (!c) notFound();
  const items = CONTENT.filter((x) => x.client === c.id).sort((a, b) => b.date.localeCompare(a.date));

  return (
    <>
      <Link href="/clients" className="back">
        <Icon name="chevronLeft" size={16} /> Klien
      </Link>
      <div className="profile-head">
        <Monogram name={c.name.replace(/^(Villa|Resto|Spa) /, "")} size="lg" />
        <div>
          <h1>{c.name}</h1>
          <p>
            {c.type} · {c.location}
          </p>
        </div>
        <div className="profile-head__meta">
          <span className={`badge ${c.status === "active" ? "badge--success" : "badge--warning"}`}>
            {c.status === "active" ? "Aktif" : "Onboarding"}
          </span>
        </div>
      </div>
      <SimNotice />

      <div className="grid-2">
        <div className="stack">
          <Card title="Informasi bisnis" flush>
            <dl className="facts">
              <dt>Jenis bisnis</dt>
              <dd>{c.type}</dd>
              <dt>Lokasi</dt>
              <dd>{c.location}</dd>
              <dt>Target audiens</dt>
              <dd>{c.audience}</dd>
              <dt>Positioning</dt>
              <dd>{c.positioning}</dd>
              <dt>Layanan</dt>
              <dd>{c.services.join(", ")}</dd>
              <dt>Keunggulan (USP)</dt>
              <dd>{c.usp.join(", ")}</dd>
            </dl>
          </Card>
          <Card title="Riwayat konten" flush>
            <div className="table-wrap">
              <table className="table">
                <thead>
                  <tr>
                    <th>Konten</th>
                    <th>Agent</th>
                    <th>Tanggal</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {items.map((x) => (
                    <tr key={x.id}>
                      <td>
                        <span className="cell-strong">{x.title}</span>
                        <span className="cell-sub">{x.type}</span>
                      </td>
                      <td className="muted">{getMember(x.agent)?.name}</td>
                      <td className="nowrap muted">{fmtDate(x.date)}</td>
                      <td>
                        <StatusBadge status={x.status} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        </div>
        <div className="stack">
          <Card title="Brand voice">
            <div className="tags">
              {c.tone.map((t) => (
                <span key={t} className="tag">
                  {t}
                </span>
              ))}
            </div>
          </Card>
          <Card title="Akun sosial">
            <div className="tags">
              {c.social.map((s) => (
                <span key={s} className="tag">
                  {s} · belum terhubung
                </span>
              ))}
            </div>
          </Card>
          <Card title="Media library">
            <Empty icon="inbox" title="Belum ada media" body="Foto dan video properti asli akan tersimpan di sini setelah penyimpanan file aktif." />
          </Card>
        </div>
      </div>
    </>
  );
}
