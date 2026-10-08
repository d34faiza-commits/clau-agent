import Link from "next/link";
import Avatar from "./Avatar";
import Icon from "./Icon";
import { AgentStatus, Level } from "./ui";
import { L } from "../lib/i18n";
import type { Member } from "../lib/team";

export default function MemberCard({ m, compact }: { m: Member; compact?: boolean }) {
  return (
    <Link href={`/agents/${m.id}`} className="member" style={{ ["--hue" as string]: m.hue }}>
      <div className="member__head">
        <Avatar name={m.name} hue={m.hue} look={m.look} uniform={m.uniform} image={m.image} status={m.status} size="lg" />
        <div>
          <div className="member__name">{m.name}</div>
          <div className="member__role">
            <L en={m.role.en} id={m.role.id} />
          </div>
        </div>
      </div>
      <p className="member__headline">
        <L en={m.headline.en} id={m.headline.id} />
      </p>
      {!compact && (
        <p className="member__desc">
          <L en={m.tagline.en} id={m.tagline.id} />
        </p>
      )}
      <div>
        <div className="member__label">
          <L en="Capabilities" id="Kemampuan" />
        </div>
        <div className="tags">
          {m.capabilities.map((c) => (
            <span key={c.en} className="tag">
              <L en={c.en} id={c.id} />
            </span>
          ))}
        </div>
      </div>
      <div className="member__foot">
        <span style={{ display: "inline-flex", gap: 8, alignItems: "center" }}>
          <AgentStatus status={m.status} />
          <Level level={m.approval_min} />
        </span>
        <span className="member__open">
          <L en="Open agent" id="Buka agent" />
          <Icon name="arrowRight" size={14} />
        </span>
      </div>
    </Link>
  );
}
