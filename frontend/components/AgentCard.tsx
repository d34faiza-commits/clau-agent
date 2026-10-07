import Link from "next/link";
import Character from "./Character";
import Scene from "./Scene";
import type { Member } from "../lib/team";

export default function AgentCard({ member }: { member: Member }) {
  const planned = member.status === "planned";
  return (
    <Link href={`/agents/${member.id}`} className="agent-card" aria-label={`${member.name}, ${member.role}`}>
      <div className="agent-card__stage">
        <Scene scene={member.scene} uid={`card-${member.id}`} />
        <div className="agent-card__character">
          <Character look={member.look} uid={`card-${member.id}`} />
        </div>
        <span className={`chip ${planned ? "chip--planned" : "chip--active"}`}>{planned ? "Segera hadir" : "Aktif"}</span>
      </div>
      <div className="agent-card__body">
        <h3>
          {member.name} <span className="ai-tag">Agent AI</span>
        </h3>
        <p className="agent-card__role">{member.role}</p>
        <p className="agent-card__tagline">{member.tagline}</p>
      </div>
    </Link>
  );
}
