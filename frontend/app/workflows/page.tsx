import Avatar from "../../components/Avatar";
import GenerateRun from "../../components/GenerateRun";
import Icon, { type IconName } from "../../components/Icon";
import { Card, PageHeader } from "../../components/ui";
import { L } from "../../lib/i18n";
import { monthlyRun } from "../../lib/run";
import { getMember } from "../../lib/team";

export const metadata = { title: "Workflows · CLAU" };

type Step = { en: string; id: string; bodyEn: string; bodyId: string; who: "ai" | "human" | "concept" | "system"; agents?: string[]; icon?: IconName };

const FLOW: Step[] = [
  { en: "Client data", id: "Data klien", bodyEn: "Voice Card, facilities, offers. Key facts are confirmed by the owner.", bodyId: "Voice Card, fasilitas, penawaran. Fakta penting dikonfirmasi owner.", who: "human", icon: "users" },
  { en: "Strategy", id: "Strategi", bodyEn: "Brand strategy role (Nova) is a concept. Today the owner sets the monthly focus.", bodyId: "Peran strategi brand (Nova) masih konsep. Saat ini owner menentukan fokus bulanan.", who: "concept", icon: "briefcase" },
  { en: "Content planning", id: "Perencanaan konten", bodyEn: "Monthly calendar and seasonal campaigns.", bodyId: "Kalender bulanan dan campaign musiman.", who: "ai", agents: ["calendar-planner", "campaign-planner"] },
  { en: "Copywriting", id: "Copywriting", bodyEn: "Captions, Stories, OTA listings and review replies.", bodyId: "Caption, Stories, listing OTA, dan balasan review.", who: "ai", agents: ["caption-writer", "story-writer", "listing-writer", "review-responder"] },
  { en: "Video", id: "Video", bodyEn: "Reel scripts and shot lists. Footage is shot by your team.", bodyId: "Naskah Reel dan shot list. Footage diambil oleh tim kamu.", who: "ai", agents: ["reel-scripter"] },
  { en: "Visuals", id: "Visual", bodyEn: "Visual direction role (Aruna) is a concept. Real property photos are used.", bodyId: "Peran arahan visual (Aruna) masih konsep. Foto properti asli yang dipakai.", who: "concept", icon: "sparkles" },
  { en: "Localization", id: "Lokalisasi", bodyEn: "English and Indonesian versions with the same meaning and claims.", bodyId: "Versi Inggris dan Indonesia dengan makna dan klaim yang sama.", who: "ai", agents: ["localizer"] },
  { en: "Quality control", id: "Quality control", bodyEn: "Automatic rule checks today. A QC agent (Dara) is a concept.", bodyId: "Saat ini cek aturan otomatis. Agent QC (Dara) masih konsep.", who: "system", icon: "shield" },
  { en: "Human approval", id: "Persetujuan manusia", bodyEn: "L1–L3 review. L2 and L3 need a second person.", bodyId: "Review L1–L3. L2 dan L3 wajib orang kedua.", who: "human", icon: "check" },
  { en: "Published", id: "Tayang", bodyEn: "Your team publishes in the official apps. AI never publishes.", bodyId: "Tim kamu mempublish di aplikasi resmi. AI tidak pernah publish.", who: "human", icon: "arrowRight" },
];

const WHO = {
  ai: { en: "AI team", id: "Tim AI" },
  human: { en: "Your team", id: "Tim kamu" },
  concept: { en: "Concept", id: "Konsep" },
  system: { en: "Automatic", id: "Otomatis" },
};

export default function Workflows() {
  return (
    <>
      <PageHeader
        title={<L en="Workflows" id="Alur kerja" />}
        subtitle={<L en="How your AI team and your people work together, from client data to published content." id="Cara tim AI dan tim kamu bekerja bersama, dari data klien sampai konten tayang." />}
        actions={<GenerateRun steps={monthlyRun()} label={{ en: "Preview a run", id: "Pratinjau alur" }} />}
      />
      <Card title={<L en="Monthly content workflow" id="Alur konten bulanan" />} flush>
        <ol className="flow">
          {FLOW.map((f) => (
            <li key={f.en}>
              {f.agents ? (
                <span className="stack-avatars">
                  {f.agents.slice(0, 2).map((a) => {
                    const m = getMember(a)!;
                    return <Avatar key={a} name={m.name} hue={m.hue} look={m.look} uniform={m.uniform} image={m.image} size="sm" />;
                  })}
                </span>
              ) : (
                <span className="flow__node"><Icon name={f.icon ?? "content"} size={18} /></span>
              )}
              <div>
                <h3>
                  <L en={f.en} id={f.id} />
                  {f.agents && <span className="muted" style={{ fontWeight: 500 }}> · {f.agents.map((a) => getMember(a)!.name).join(", ")}</span>}
                </h3>
                <p><L en={f.bodyEn} id={f.bodyId} /></p>
              </div>
              <span className={`who who--${f.who === "system" ? "ai" : f.who}`}><L en={WHO[f.who].en} id={WHO[f.who].id} /></span>
            </li>
          ))}
        </ol>
      </Card>
    </>
  );
}
