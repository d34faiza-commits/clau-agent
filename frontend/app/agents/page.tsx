import Link from "next/link";
import Avatar from "../../components/Avatar";
import { AgentStatus, Card, Level, PageHeader } from "../../components/ui";
import { L } from "../../lib/i18n";
import { evalCaseCount } from "../../lib/persona";
import { PILLAR_LIST, getTeam } from "../../lib/team";

export const metadata = { title: "Agents · CLAU" };

export default function Agents() {
  const team = getTeam();
  return (
    <>
      <PageHeader
        title={<L en="Agents" id="Agent" />}
        subtitle={<L en="Directory of every agent: role, pillar, approval level and test coverage." id="Direktori semua agent: peran, pilar, level persetujuan, dan cakupan uji." />}
      />
      {PILLAR_LIST.map((p) => (
        <section key={p.id}>
          <div className="section-label">
            <L en={`Pillar ${p.id} · ${p.name.en}`} id={`Pilar ${p.id} · ${p.name.id}`} />{" "}
            <AgentStatus status={p.status} />
          </div>
          {p.status === "planned" && (
            <p className="note" style={{ margin: "-4px 0 12px" }}>
              {team.some((m) => m.pillar === p.id && m.status === "active") ? (
                <L en="Pillar not active yet. Its active agent temporarily uses a Pillar 1 template." id="Pilar belum aktif. Agent aktifnya sementara memakai template Pilar 1." />
              ) : (
                <L en="Requests for this pillar are escalated to the owner until the pillar is approved." id="Permintaan untuk pilar ini dieskalasi ke owner sampai pilarnya disetujui." />
              )}
            </p>
          )}
          <Card flush>
            <div className="table-wrap">
              <table className="table" style={{ tableLayout: "fixed" }}>
                <colgroup>
                  <col style={{ width: "40%" }} />
                  <col style={{ width: "20%" }} />
                  <col style={{ width: "15%" }} />
                  <col style={{ width: "15%" }} />
                  <col style={{ width: "10%" }} />
                </colgroup>
                <thead>
                  <tr>
                    <th><L en="Agent" id="Agent" /></th>
                    <th><L en="Status" id="Status" /></th>
                    <th><L en="Approval" id="Approval" /></th>
                    <th><L en="Test cases" id="Kasus uji" /></th>
                    <th><span className="sr-only"><L en="Open" id="Buka" /></span></th>
                  </tr>
                </thead>
                <tbody>
                  {team.filter((m) => m.pillar === p.id).map((m) => (
                    <tr key={m.id}>
                      <td>
                        <Link href={`/agents/${m.id}`} className="cell-agent">
                          <Avatar name={m.name} hue={m.hue} look={m.look} uniform={m.uniform} image={m.image} size="sm" decorative />
                          <span>
                            <span className="cell-strong">{m.name}</span>
                            <span className="cell-sub"><L en={m.role.en} id={m.role.id} /></span>
                          </span>
                        </Link>
                      </td>
                      <td><AgentStatus status={m.status} /></td>
                      <td><Level level={m.approval_min} /></td>
                      <td className="muted">{evalCaseCount(m.id)}</td>
                      <td>
                        <Link href={`/agents/${m.id}`} className="link"><L en="Open" id="Buka" /></Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        </section>
      ))}
    </>
  );
}
