import Link from "next/link";
import { Card, PageHeader, Progress, SimNotice } from "../../components/ui";
import { CONTENT, PROJECTS, clientName, fmtDate } from "../../lib/demo";

export const metadata = { title: "Proyek · CLAU" };

export default function Projects() {
  return (
    <>
      <PageHeader title="Proyek" subtitle="Paket konten bulanan dan campaign per klien." />
      <SimNotice />
      <Card flush>
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th>Proyek</th>
                <th>Klien</th>
                <th>Konten</th>
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
                    <td className="cell-strong">{p.name}</td>
                    <td>
                      <Link href={`/clients/${p.client}`} className="link">
                        {clientName(p.client)}
                      </Link>
                    </td>
                    <td className="muted">{items.length}</td>
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
    </>
  );
}
