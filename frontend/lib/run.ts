import type { RunStep } from "../components/GenerateRun";
import { getMember } from "./team";

function agent(id: string) {
  const m = getMember(id);
  return m ? { name: m.name, hue: m.hue, look: m.look, uniform: m.uniform, image: m.image } : undefined;
}

/** Judul langkah dari registry ("Tara · Copywriter"), supaya ikut berubah bila nama/peran agent diganti. */
function step(key: string, id: string, subEn: string, subId: string): RunStep {
  const m = getMember(id);
  const role = (r: string) => r.replace(/^AI /, "");
  return { key, agent: agent(id), en: m ? `${m.name} · ${role(m.role.en)}` : id, id: m ? `${m.name} · ${role(m.role.id)}` : id, subEn, subId };
}

/** Alur "konten bulanan" memakai agent yang benar-benar ada di registry. */
export function monthlyRun(): RunStep[] {
  return [
    { key: "ctx", en: "Client context loaded", id: "Konteks klien dimuat", subEn: "Voice Card and owner-confirmed facts", subId: "Voice Card dan fakta yang dikonfirmasi owner" },
    step("plan", "calendar-planner", "Monthly plan and content pillars", "Rencana bulanan dan pilar konten"),
    step("copy", "caption-writer", "Captions, hooks and CTAs", "Caption, hook, dan CTA"),
    step("reel", "reel-scripter", "Reel scripts and shot lists", "Naskah Reel dan shot list"),
    step("loc", "localizer", "English and Indonesian versions", "Versi Inggris dan Indonesia"),
    { key: "qc", en: "Automatic checks", id: "Cek otomatis", subEn: "Banned phrases, unproven claims, length, CTA", subId: "Frasa terlarang, klaim tanpa bukti, panjang, CTA" },
    { key: "human", human: true, en: "Human approval", id: "Persetujuan manusia", subEn: "Your team reviews before anything is published", subId: "Tim kamu mereview sebelum apa pun tayang" },
  ];
}
