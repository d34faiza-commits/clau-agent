import Link from "next/link";
import { Card, PageHeader, Progress, SimNotice } from "../../components/ui";
import { CONTENT, PROJECTS, clientName } from "../../lib/demo";
import { D, L } from "../../lib/i18n";

export const metadata = { title: "Projects · CLAU" };

export default function Projects() {
  return (
    <>
      <PageHeader title={<L en="Projects" id="Proyek" />} subtitle={<L en="Monthly content packages and campaigns per client." id="Paket konten bulanan dan campaign per klien." />} />
      <SimNotice />
      <Card flush>
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th><L en="Project" id="Proyek" /></th>
                <th><L en="Client" id="Klien" /></th>
                <th><L en="Content" id="Konten" /></th>
                <th><L en="Progress" id="Progres" /></th>
                <th><L en="Due" id="Tenggat" /></th>
              </tr>
            </thead>
            <tbody>
              {PROJECTS.map((p) => {
                const items = CONTENT.filter((c) => c.project === p.id);
                const done = items.filter((c) => ["approved", "scheduled", "published"].includes(c.status)).length;
                return (
                  <tr key={p.id}>
                    <td className="cell-strong">{p.name}</td>
                    <td><Link href={`/clients/${p.client}`} className="link">{clientName(p.client)}</Link></td>
                    <td className="muted">{items.length}</td>
                    <td><Progress value={done} total={items.length} /></td>
                    <td className="nowrap muted"><D iso={p.due} /></td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </Card>
    </>
  );
}
