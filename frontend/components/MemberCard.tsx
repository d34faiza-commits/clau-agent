import Link from "next/link";
import Character from "./Character";
import Icon from "./Icon";
import { AgentStatus, Level } from "./ui";
import { L } from "../lib/i18n";
import type { Member } from "../lib/team";

export default function MemberCard({ m, compact }: { m: Member; compact?: boolean }) {
  return (
    <Link href={`/agents/${m.id}`} className="member" style={{ ["--hue" as string]: m.hue }}>
      <div
        className="member__portrait"
        style={{ background: `linear-gradient(170deg, color-mix(in srgb, ${m.hue} 8%, var(--color-surface)), color-mix(in srgb, ${m.hue} 22%, var(--color-surface)))` }}
      >
        {m.image ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={m.image} alt="" className="member__img" loading="lazy" style={m.uniform.muted ? { filter: `saturate(${1 - m.uniform.muted})` } : undefined} />
        ) : (
          <div className="member__figure">
            <Character look={m.look} uniform={m.uniform} />
          </div>
        )}
        <span className={`member__status member__status--${m.status}`} aria-hidden="true" />
      </div>
      <div className="member__head">
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
