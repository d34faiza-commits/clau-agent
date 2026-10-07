import Link from "next/link";
import { AgentStatus, Level, Monogram, PageHeader } from "../../components/ui";
import { PILLARS, getTeam, type Member } from "../../lib/team";

export const metadata = { title: "Agent AI · CLAU" };

function AgentCard({ m }: { m: Member }) {
  const planned = m.status === "planned";
  return (
    <Link href={`/agents/${m.id}`} className="agent">
      <div className="agent__head">
        <Monogram name={m.name} muted={planned} />
        <div>
          <div className="agent__name">{m.name}</div>
          <div className="agent__role">{m.role}</div>
        </div>
      </div>
      <p className="agent__desc">{m.tagline}</p>
      <div className="tags">
        {m.focus.map((f) => (
          <span key={f} className="tag">
            {f}
          </span>
        ))}
      </div>
      <div className="agent__foot">
        <AgentStatus status={m.status} />
        <Level level={m.approval_min} />
      </div>
      <span className="agent__pillar">{PILLARS[m.pillar]}</span>
    </Link>
  );
}

export default function Agents() {
  const team = getTeam();
  const active = team.filter((m) => m.status === "active");
  const planned = team.filter((m) => m.status === "planned");
  return (
    <>
      <PageHeader
        title="Agent AI"
        subtitle={`${active.length} agent aktif, ${planned.length} belum aktif. Semua agent hanya menyiapkan draft untuk direview manusia.`}
      />
      <div className="section-label">Aktif</div>
      <div className="agent-grid">
        {active.map((m) => (
          <AgentCard key={m.id} m={m} />
        ))}
      </div>
      <div className="section-label">Belum aktif · menunggu aktivasi pilar</div>
      <div className="agent-grid">
        {planned.map((m) => (
          <AgentCard key={m.id} m={m} />
        ))}
      </div>
    </>
  );
}
