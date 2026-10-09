import Preferences from "../../components/Preferences";
import { Card, PageHeader } from "../../components/ui";
import { L } from "../../lib/i18n";

export const metadata = { title: "Settings · CLAU" };

const INTEGRATIONS = ["Instagram", "TikTok", "Google Business", "WhatsApp Business"];

export default function Settings() {
  return (
    <>
      <PageHeader title={<L en="Settings" id="Pengaturan" />} subtitle={<L en="Workspace preferences. Workspace changes are available after sign-in is live." id="Preferensi workspace. Perubahan workspace tersedia setelah login aktif." />} />
      <div className="grid-2-even">
        <div className="stack">
          <Card title={<L en="Preferences" id="Preferensi" />} flush>
            <Preferences />
          </Card>
          <Card title={<L en="Workspace" id="Workspace" />} flush>
            <dl className="facts">
              <dt><L en="Name" id="Nama" /></dt><dd>CLAU AI · Content Studio</dd>
              <dt><L en="Time zone" id="Zona waktu" /></dt><dd>WITA (UTC+8)</dd>
              <dt><L en="Mode" id="Mode" /></dt><dd><span className="badge badge--warning"><L en="Preview · Simulation" id="Pratinjau · Simulasi" /></span></dd>
            </dl>
          </Card>
        </div>
        <Card title={<L en="Integrations" id="Integrasi" />} flush>
          <ul className="list">
            {INTEGRATIONS.map((i) => (
              <li key={i}>
                <div className="list__main">
                  <span className="list__title">{i}</span>
                  <span className="list__sub"><L en="Used for report data. Publishing stays with your team." id="Dipakai untuk data laporan. Publish tetap oleh tim kamu." /></span>
                </div>
                <span className="badge badge--neutral"><L en="Not connected" id="Belum terhubung" /></span>
              </li>
            ))}
          </ul>
        </Card>
      </div>
    </>
  );
}
