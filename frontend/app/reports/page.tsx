import { AgentStatus, Card, Empty, Kpi, PageHeader, SimNotice } from "../../components/ui";
import { CLIENTS, CONTENT, STATUS, STATUS_ORDER } from "../../lib/demo";
import { L } from "../../lib/i18n";
import { PILLAR_LIST, getMember, getTeam } from "../../lib/team";

export const metadata = { title: "Reports · CLAU" };

function Bars({ rows }: { rows: { key: string; label: React.ReactNode; title: string; value: number }[] }) {
  const max = Math.max(1, ...rows.map((r) => r.value));
  return (
    <div className="bars">
      {rows.map((r) => (
        <div key={r.key} className="bar-row" title={`${r.title}: ${r.value}`}>
          <span className="bar-row__label">{r.label}</span>
          <span className="bar-row__track" aria-hidden="true"><span className="bar-row__fill" style={{ width: `${(r.value / max) * 100}%` }} /></span>
          <span className="bar-row__val">{r.value}</span>
        </div>
      ))}
    </div>
  );
}

export default function Reports() {
  // The pillar whose agent writes this report (report-builder), read from the registry.
  const reportPillar = getTeam().find((m) => m.id === "report-builder")?.pillar;
  const approved = CONTENT.filter((c) => ["approved", "scheduled", "published"].includes(c.status)).length;
  const published = CONTENT.filter((c) => c.status === "published").length;
  const byAgent = [...new Set(CONTENT.map((c) => c.agent))].map((a) => ({ key: a, label: getMember(a)!.name, title: getMember(a)!.name, value: CONTENT.filter((c) => c.agent === a).length })).sort((a, b) => b.value - a.value);
  return (
    <>
      <PageHeader title={<L en="Reports" id="Laporan" />} subtitle={<L en="Content production · October 2026" id="Produksi konten · Oktober 2026" />} />
      <SimNotice />
      <div className="kpis">
        <Kpi label={<L en="Content produced" id="Konten diproduksi" />} value={CONTENT.length} />
        <Kpi label={<L en="Approved" id="Disetujui" />} value={approved} hint={<L en="Incl. scheduled & published" id="Termasuk terjadwal & tayang" />} />
        <Kpi label={<L en="Published" id="Tayang" />} value={published} />
        <Kpi label={<L en="Approval rate" id="Rasio persetujuan" />} value={`${Math.round((approved / CONTENT.length) * 100)}%`} />
      </div>
      <div className="grid-2-even">
        <Card title={<L en="Content by status" id="Konten per status" />}>
          <Bars rows={STATUS_ORDER.map((s) => ({ key: s, label: <L en={STATUS[s].en} id={STATUS[s].id} />, title: STATUS[s].en, value: CONTENT.filter((c) => c.status === s).length }))} />
        </Card>
        <Card title={<L en="Content by AI agent" id="Konten per agent AI" />}>
          <Bars rows={byAgent} />
        </Card>
      </div>
      <div className="mt">
        <Card flush title={<L en="By pillar" id="Per pilar" />}>
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th><L en="Pillar" id="Pilar" /></th>
                  <th><L en="Status" id="Status" /></th>
                  <th><L en="This period" id="Periode ini" /></th>
                </tr>
              </thead>
              <tbody>
                {PILLAR_LIST.map((p) => (
                  <tr key={p.id}>
                    <td>{p.id} · <L en={p.name.en} id={p.name.id} /></td>
                    <td><AgentStatus status={p.status} /></td>
                    <td className="muted">
                      {p.id === 1 ? (
                        <L en={`${CONTENT.length} content items`} id={`${CONTENT.length} konten`} />
                      ) : p.id === reportPillar ? (
                        <L en="This report (Pillar 1 template)" id="Laporan ini (template Pilar 1)" />
                      ) : (
                        <L en="No data: pillar not active" id="Belum ada data: pilar belum aktif" />
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      </div>
      <div className="grid-2-even mt">
        <Card title={<L en="Content by client" id="Konten per klien" />}>
          <Bars rows={CLIENTS.map((c) => ({ key: c.id, label: c.name, title: c.name, value: CONTENT.filter((x) => x.client === c.id).length }))} />
        </Card>
        <Card title={<L en="Reach, engagement, clicks & leads" id="Reach, engagement, klik & leads" />}>
          <Empty icon="link" title={<L en="Not connected yet" id="Belum terhubung" />} body={<L en="Performance numbers appear only when real data from Instagram, Google Business or OTAs is connected. CLAU never invents results." id="Angka performa hanya muncul jika data asli dari Instagram, Google Business, atau OTA tersambung. CLAU tidak pernah mengarang hasil." />} />
        </Card>
      </div>
    </>
  );
}
