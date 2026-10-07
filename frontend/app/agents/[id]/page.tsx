import Link from "next/link";
import { notFound } from "next/navigation";
import Character from "../../../components/Character";
import Scene from "../../../components/Scene";
import { getPersona } from "../../../lib/persona";
import { PILLARS, getMember, getTeam } from "../../../lib/team";

const APPROVAL: Record<string, string> = {
  L1: "L1 · dicek satu orang di tim kamu",
  L2: "L2 · dicek oleh orang kedua yang bukan pembuat brief",
  L3: "L3 · wajib persetujuan owner",
};

export function generateStaticParams() {
  return getTeam().map((m) => ({ id: m.id }));
}

export async function generateMetadata({ params }: { params: Promise<{ id: string }> }) {
  const m = getMember((await params).id);
  return { title: m ? `${m.name} · ${m.role} · CLAU AI` : "CLAU AI" };
}

export default async function AgentPage({ params }: { params: Promise<{ id: string }> }) {
  const member = getMember((await params).id);
  if (!member) notFound();
  const persona = getPersona(member.id);
  const planned = member.status === "planned";
  const pillar = PILLARS[member.pillar];

  return (
    <section className="detail">
      <div className="container">
        <Link href="/" className="back">
          ← Kembali ke tim
        </Link>
        <div className="detail__grid">
          <div className="detail__stage">
            <Scene scene={member.scene} uid={`detail-${member.id}`} />
            <div className="detail__character">
              <Character look={member.look} uid={`detail-${member.id}`} size={300} />
            </div>
          </div>

          <div className="detail__info">
            <p className="eyebrow">
              Pilar {member.pillar} · {pillar}
            </p>
            <h1>
              {member.name} <span className="ai-tag ai-tag--lg">Agent AI</span>
            </h1>
            <p className="detail__role">{member.role}</p>
            <p className="lead lead--dark">{member.tagline}</p>

            {planned && (
              <div className="note note--warning">
                <b>Segera hadir.</b> Gaya bahasa dan batas kerja {member.name} sudah disepakati, tetapi agent ini belum
                dijalankan. Permintaan untuk tugas ini sementara diteruskan ke owner.
              </div>
            )}

            <dl className="facts">
              {persona.like && (
                <>
                  <dt>Bekerja seperti</dt>
                  <dd>{persona.like}</dd>
                </>
              )}
              {persona.audience && (
                <>
                  <dt>Menulis untuk</dt>
                  <dd>{persona.audience}</dd>
                </>
              )}
              <dt>Persetujuan minimum</dt>
              <dd>{APPROVAL[member.approval_min] ?? member.approval_min}</dd>
            </dl>

            {persona.skills.length > 0 && (
              <>
                <h2 className="h-small">Keahlian</h2>
                <ul className="pills">
                  {persona.skills.map((s) => (
                    <li key={s}>{s}</li>
                  ))}
                </ul>
              </>
            )}

            {persona.escalation.length > 0 && (
              <>
                <h2 className="h-small">Kapan {member.name} berhenti dan bertanya ke manusia</h2>
                <ul className="list">
                  {persona.escalation.map((e) => (
                    <li key={e}>{e}</li>
                  ))}
                </ul>
              </>
            )}

            <div className="note">
              {member.name} adalah agent AI, bukan staf manusia. {member.name} hanya menyiapkan <b>draft</b>: tidak
              pernah publish, mengirim pesan ke tamu, atau menyetujui pekerjaannya sendiri.
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
