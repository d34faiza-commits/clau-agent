import { Card, Empty, Kpi, PageHeader, SimNotice } from "../../components/ui";
import { CLIENTS, CONTENT, STATUS, STATUS_ORDER } from "../../lib/demo";

export const metadata = { title: "Laporan · CLAU" };

function Bars({ rows }: { rows: { label: string; value: number }[] }) {
  const max = Math.max(1, ...rows.map((r) => r.value));
  return (
    <div className="bars" role="table" aria-label="Diagram batang">
      {rows.map((r) => (
        <div key={r.label} className="bar-row" role="row" title={`${r.label}: ${r.value}`}>
          <span className="bar-row__label" role="cell">
            {r.label}
          </span>
          <span className="bar-row__track" aria-hidden="true">
            <span className="bar-row__fill" style={{ display: "block", width: `${(r.value / max) * 100}%` }} />
          </span>
          <span className="bar-row__val" role="cell">
            {r.value}
          </span>
        </div>
      ))}
    </div>
  );
}

export default function Reports() {
  const approved = CONTENT.filter((c) => ["approved", "scheduled", "published"].includes(c.status)).length;
  const published = CONTENT.filter((c) => c.status === "published").length;
  return (
    <>
      <PageHeader title="Laporan" subtitle="Produksi konten Oktober 2026" />
      <SimNotice />
      <div className="kpis">
        <Kpi label="Konten diproduksi" value={CONTENT.length} />
        <Kpi label="Konten disetujui" value={approved} hint="Termasuk terjadwal & tayang" />
        <Kpi label="Konten tayang" value={published} />
        <Kpi label="Rasio persetujuan" value={`${Math.round((approved / CONTENT.length) * 100)}%`} />
      </div>
      <div className="grid-2-even">
        <Card title="Konten per status">
          <Bars rows={STATUS_ORDER.map((s) => ({ label: STATUS[s].label, value: CONTENT.filter((c) => c.status === s).length }))} />
        </Card>
        <Card title="Konten per klien">
          <Bars rows={CLIENTS.map((c) => ({ label: c.name, value: CONTENT.filter((x) => x.client === c.id).length }))} />
        </Card>
      </div>
      <div style={{ marginTop: 16 }}>
        <Card title="Engagement, reach, klik, dan leads">
          <Empty
            icon="link"
            title="Belum terhubung ke platform"
            body="Angka engagement tidak ditampilkan sampai data asli dari Instagram, Google Business, atau OTA tersedia. CLAU tidak mengarang hasil bisnis."
          />
        </Card>
      </div>
    </>
  );
}
