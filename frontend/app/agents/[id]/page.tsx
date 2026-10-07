import Link from "next/link";
import { notFound } from "next/navigation";
import Icon from "../../../components/Icon";
import { AgentStatus, Card, Level, Monogram } from "../../../components/ui";
import { getPersona } from "../../../lib/persona";
import { APPROVAL, PILLARS, getMember, getTeam } from "../../../lib/team";

export function generateStaticParams() {
  return getTeam().map((m) => ({ id: m.id }));
}

export async function generateMetadata({ params }: { params: Promise<{ id: string }> }) {
  const m = getMember((await params).id);
  return { title: m ? `${m.name} · ${m.role} · CLAU` : "CLAU" };
}

export default async function AgentPage({ params }: { params: Promise<{ id: string }> }) {
  const m = getMember((await params).id);
  if (!m) notFound();
  const persona = getPersona(m.id);
  const planned = m.status === "planned";

  return (
    <>
      <Link href="/agents" className="back">
        <Icon name="chevronLeft" size={16} /> Agent AI
      </Link>
      <div className="profile-head">
        <Monogram name={m.name} size="lg" muted={planned} />
        <div>
          <h1>{m.name}</h1>
          <p>
            {m.role} · {PILLARS[m.pillar]}
          </p>
        </div>
        <div className="profile-head__meta">
          <AgentStatus status={m.status} />
          <Level level={m.approval_min} />
        </div>
      </div>

      {planned && (
        <div className="sim" role="note">
          <span className="sim__tag">BELUM AKTIF</span>
          Gaya bahasa dan batas kerja {m.name} sudah disepakati, tetapi agent ini belum dijalankan. Permintaan untuk tugas ini
          diteruskan ke owner.
        </div>
      )}

      <div className="grid-2">
        <div className="stack">
          <Card title="Profil" flush>
            <dl className="facts">
              <dt>Tugas</dt>
              <dd>{m.tagline}</dd>
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
              <dd>
                <b>{m.approval_min}</b> · {APPROVAL[m.approval_min] ?? ""}
              </dd>
            </dl>
          </Card>
          {persona.escalation.length > 0 && (
            <Card title={`Kapan ${m.name} berhenti dan menyerahkan ke manusia`}>
              <ul className="bullets">
                {persona.escalation.map((e) => (
                  <li key={e}>{e}</li>
                ))}
              </ul>
            </Card>
          )}
        </div>
        <div className="stack">
          <Card title="Keahlian">
            <div className="tags">
              {persona.skills.map((s) => (
                <span key={s} className="tag">
                  {s}
                </span>
              ))}
            </div>
          </Card>
          <Card title="Batas kerja">
            <ul className="bullets">
              <li>Hanya menyiapkan draft</li>
              <li>Tidak publish atau mengirim pesan ke tamu</li>
              <li>Tidak menyetujui pekerjaannya sendiri</li>
              <li>Tidak mengaku sebagai staf manusia</li>
            </ul>
          </Card>
        </div>
      </div>
    </>
  );
}
