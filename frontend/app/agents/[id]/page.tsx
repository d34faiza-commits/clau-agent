import Link from "next/link";
import { notFound } from "next/navigation";
import Avatar from "../../../components/Avatar";
import Icon from "../../../components/Icon";
import { AgentStatus, Card, Empty, Kpi, Level, StatusBadge } from "../../../components/ui";
import { CONTENT, clientName } from "../../../lib/demo";
import { D, L } from "../../../lib/i18n";
import { evalCaseCount, getPersona } from "../../../lib/persona";
import { APPROVAL, PILLARS, getMember, getTeam } from "../../../lib/team";
import registry from "../../../../agents/registry.json";

export function generateStaticParams() {
  return getTeam().map((m) => ({ id: m.id }));
}

export async function generateMetadata({ params }: { params: Promise<{ id: string }> }) {
  const m = getMember((await params).id);
  return { title: m ? `${m.name} · ${m.role.en} · CLAU` : "CLAU" };
}

export default async function AgentPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const m = getMember(id);
  if (!m) notFound();
  const persona = getPersona(m.id);
  const planned = m.status === "planned";
  const items = CONTENT.filter((c) => c.agent === m.id);
  const current = items.filter((c) => ["draft", "ai_review", "human_review"].includes(c.status));
  const outputs = items.filter((c) => ["approved", "scheduled", "published"].includes(c.status));
  const reg = (registry.agents as { id: string; skill: string | null; skill_repo?: string; intents: string[] }[]).find((a) => a.id === m.id);

  return (
    <>
      <Link href="/team" className="back">
        <Icon name="chevronLeft" size={16} /> <L en="My AI Team" id="Tim AI Saya" />
      </Link>
      <div className="profile-head" style={{ ["--hue" as string]: m.hue }}>
        <Avatar name={m.name} hue={m.hue} size="lg" status={m.status} />
        <div>
          <h1>{m.name}</h1>
          <div className="profile-head__role"><L en={m.role.en} id={m.role.id} /></div>
          <p><L en={m.headline.en} id={m.headline.id} /> <L en={m.tagline.en} id={m.tagline.id} /></p>
        </div>
        <div className="profile-head__meta">
          <AgentStatus status={m.status} />
          <Level level={m.approval_min} />
        </div>
      </div>

      {planned && (
        <div className="sim" role="note">
          <span className="sim__tag"><L en="NOT ACTIVE" id="BELUM AKTIF" /></span>
          <L
            en={`${m.name}'s voice and boundaries are agreed, but this agent does not run yet. Requests for this task go to the owner.`}
            id={`Gaya bahasa dan batas kerja ${m.name} sudah disepakati, tetapi agent ini belum dijalankan. Permintaan untuk tugas ini diteruskan ke owner.`}
          />
        </div>
      )}

      <div className="metric-row">
        <Kpi label={<L en="Current tasks" id="Tugas berjalan" />} value={current.length} hint={<L en="Simulation" id="Simulasi" />} />
        <Kpi label={<L en="Outputs this month" id="Output bulan ini" />} value={outputs.length} hint={<L en="Approved, scheduled or published · simulation" id="Disetujui, terjadwal, atau tayang · simulasi" />} />
        <Kpi label={<L en="Quality" id="Kualitas" />} value={<span style={{ fontSize: 18 }}><L en="Not measured yet" id="Belum diukur" /></span>} hint={<L en={`${evalCaseCount(m.id)} test cases ready · scored after the AI backend is live`} id={`${evalCaseCount(m.id)} kasus uji siap · dinilai setelah backend AI aktif`} />} />
      </div>

      <div className="grid-2">
        <div className="stack">
          <Card title={<L en="Current tasks" id="Tugas berjalan" />} flush>
            {current.length === 0 ? (
              <Empty icon="inbox" title={<L en="No tasks assigned" id="Belum ada tugas" />} body={<L en={`${m.name} has nothing in progress right now.`} id={`${m.name} sedang tidak mengerjakan apa pun.`} />} />
            ) : (
              <ul className="list">
                {current.map((c) => (
                  <li key={c.id}>
                    <div className="list__main">
                      <span className="list__title">{c.title}</span>
                      <span className="list__sub">{c.type} · {clientName(c.client)}</span>
                    </div>
                    <StatusBadge status={c.status} />
                  </li>
                ))}
              </ul>
            )}
          </Card>
          <Card title={<L en="Recent outputs" id="Output terbaru" />} flush>
            {outputs.length === 0 ? (
              <Empty icon="content" title={<L en="No outputs yet" id="Belum ada output" />} body={<L en="Approved work will appear here." id="Hasil yang disetujui akan muncul di sini." />} />
            ) : (
              <ul className="list">
                {outputs.map((c) => (
                  <li key={c.id}>
                    <div className="list__main">
                      <span className="list__title">{c.title}</span>
                      <span className="list__sub">{clientName(c.client)} · <D iso={c.date} /></span>
                    </div>
                    <StatusBadge status={c.status} />
                  </li>
                ))}
              </ul>
            )}
          </Card>
          <Card title={<L en="Instructions & behavior" id="Instruksi & perilaku" />} flush>
            <dl className="facts">
              {persona.like && (<><dt><L en="Works like" id="Bekerja seperti" /></dt><dd>{persona.like}</dd></>)}
              {persona.audience && (<><dt><L en="Writes for" id="Menulis untuk" /></dt><dd>{persona.audience}</dd></>)}
              <dt><L en="Approval" id="Persetujuan" /></dt>
              <dd><b>{m.approval_min}</b> · <L en={APPROVAL[m.approval_min].en} id={APPROVAL[m.approval_min].id} /></dd>
              <dt><L en="Never" id="Tidak pernah" /></dt>
              <dd><L en="Publishes, messages guests, approves its own work or claims to be human." id="Publish, mengirim pesan ke tamu, menyetujui pekerjaannya sendiri, atau mengaku manusia." /></dd>
            </dl>
            <p className="note" style={{ padding: "10px 18px", margin: 0, borderTop: "1px solid var(--color-border)" }}>
              <L en="Source: persona card (written in Indonesian)." id="Sumber: kartu persona." />
            </p>
          </Card>
        </div>
        <div className="stack">
          <Card title={<L en="Capabilities" id="Kemampuan" />}>
            <div className="tags">
              {m.capabilities.map((c) => (<span key={c.en} className="tag"><L en={c.en} id={c.id} /></span>))}
            </div>
          </Card>
          {persona.escalation.length > 0 && (
            <Card title={<L en={`When ${m.name} stops and hands over`} id={`Kapan ${m.name} berhenti dan menyerahkan`} />}>
              <ul className="bullets">
                {persona.escalation.map((e) => (<li key={e}>{e}</li>))}
              </ul>
            </Card>
          )}
          <Card title={<L en="Connected workflows" id="Alur kerja terhubung" />} flush>
            <dl className="facts">
              <dt><L en="Pillar" id="Pilar" /></dt>
              <dd><L en={PILLARS[m.pillar].en} id={PILLARS[m.pillar].id} /></dd>
              <dt><L en="Intent" id="Intent" /></dt>
              <dd>{reg?.intents.join(", ")}</dd>
              <dt><L en="Skill" id="Skill" /></dt>
              <dd>{reg?.skill ? `${reg.skill} (${reg.skill_repo})` : <L en="Not built yet" id="Belum dibuat" />}</dd>
            </dl>
          </Card>
        </div>
      </div>
    </>
  );
}
