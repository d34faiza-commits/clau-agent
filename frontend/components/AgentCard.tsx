import Link from "next/link";
import Character from "./Character";
import Scene from "./Scene";
import { PILLARS, UNIFORM, type Member } from "../lib/team";

export default function AgentCard({ member }: { member: Member }) {
  const planned = member.status === "planned";
  return (
    <Link href={`/agents/${member.id}`} className="card" aria-label={`${member.name}, ${member.role}`}>
      <div className="card__stage">
        <Scene scene={member.scene} uid={`card-${member.id}`} muted={planned} />
        <div className="card__character">
          <Character look={member.look} uniform={UNIFORM[member.status]} uid={`card-${member.id}`} />
        </div>
      </div>
      <div className="card__body">
        <div className="card__meta">
          <span className={`status ${planned ? "status--planned" : "status--active"}`}>
            {planned ? "Segera hadir" : "Aktif"}
          </span>
          <span className="card__level">
            Agent AI · {member.approval_min}
          </span>
        </div>
        <h3 className="card__name">{member.name}</h3>
        <p className="card__role">{member.role}</p>
        <p className="card__tagline">{member.tagline}</p>
        <p className="card__pillar">
          Pilar {member.pillar} · {PILLARS[member.pillar]}
        </p>
      </div>
    </Link>
  );
}
