import Link from "next/link";
import Avatar from "../../components/Avatar";
import { AgentStatus, Card, Level, PageHeader } from "../../components/ui";
import { L } from "../../lib/i18n";
import { evalCaseCount } from "../../lib/persona";
import { PILLARS, getTeam } from "../../lib/team";

export const metadata = { title: "Agents · CLAU" };

export default function Agents() {
  const team = getTeam();
  return (
    <>
      <PageHeader
        title={<L en="Agents" id="Agent" />}
        subtitle={<L en="Directory of every agent: role, pillar, approval level and test coverage." id="Direktori semua agent: peran, pilar, level persetujuan, dan cakupan uji." />}
      />
      <Card flush>
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th><L en="Agent" id="Agent" /></th>
                <th><L en="Pillar" id="Pilar" /></th>
                <th><L en="Status" id="Status" /></th>
                <th><L en="Approval" id="Approval" /></th>
                <th><L en="Test cases" id="Kasus uji" /></th>
                <th aria-label="Open" />
              </tr>
            </thead>
            <tbody>
              {team.map((m) => (
                <tr key={m.id}>
                  <td>
                    <Link href={`/agents/${m.id}`} className="cell-agent">
                      <Avatar name={m.name} hue={m.hue} size="sm" />
                      <span>
                        <span className="cell-strong">{m.name}</span>
                        <span className="cell-sub"><L en={m.role.en} id={m.role.id} /></span>
                      </span>
                    </Link>
                  </td>
                  <td className="muted"><L en={PILLARS[m.pillar].en} id={PILLARS[m.pillar].id} /></td>
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
    </>
  );
}
