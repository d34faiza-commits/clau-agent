import { Card, PageHeader } from "../../components/ui";

export const metadata = { title: "Pengaturan · CLAU" };

const INTEGRATIONS = ["Instagram", "TikTok", "Google Business", "WhatsApp Business"];

export default function Settings() {
  return (
    <>
      <PageHeader title="Pengaturan" subtitle="Konfigurasi workspace. Perubahan tersedia setelah login & backend aktif." />
      <div className="grid-2-even">
        <Card title="Workspace" flush>
          <dl className="facts">
            <dt>Nama</dt>
            <dd>CLAU AI Content Studio</dd>
            <dt>Zona waktu</dt>
            <dd>WITA (UTC+8)</dd>
            <dt>Bahasa</dt>
            <dd>Indonesia, English</dd>
            <dt>Mode</dt>
            <dd>
              <span className="badge badge--warning">Pratinjau · Simulasi</span>
            </dd>
          </dl>
        </Card>
        <Card title="Integrasi" flush>
          <ul className="list">
            {INTEGRATIONS.map((i) => (
              <li key={i}>
                <div className="list__main">
                  <span className="list__title">{i}</span>
                  <span className="list__sub">Dipakai untuk data laporan. Publish tetap dilakukan manusia.</span>
                </div>
                <span className="badge badge--neutral">Belum terhubung</span>
              </li>
            ))}
          </ul>
        </Card>
      </div>
    </>
  );
}
