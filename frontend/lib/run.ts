import type { RunStep } from "../components/GenerateRun";
import { getMember } from "./team";

function agent(id: string) {
  const m = getMember(id);
  return m ? { name: m.name, hue: m.hue } : undefined;
}

/** Alur "konten bulanan" memakai agent yang benar-benar ada di registry. */
export function monthlyRun(): RunStep[] {
  return [
    { key: "ctx", en: "Client context loaded", id: "Konteks klien dimuat", subEn: "Voice Card and owner-confirmed facts", subId: "Voice Card dan fakta yang dikonfirmasi owner" },
    { key: "plan", agent: agent("calendar-planner"), en: "Dimas · Content Planner", id: "Dimas · Content Planner", subEn: "Monthly plan and content pillars", subId: "Rencana bulanan dan pilar konten" },
    { key: "copy", agent: agent("caption-writer"), en: "Tara · Copywriter", id: "Tara · Copywriter", subEn: "Captions, hooks and CTAs", subId: "Caption, hook, dan CTA" },
    { key: "reel", agent: agent("reel-scripter"), en: "Raka · Reels Strategist", id: "Raka · Reels Strategist", subEn: "Reel scripts and shot lists", subId: "Naskah Reel dan shot list" },
    { key: "loc", agent: agent("localizer"), en: "Nara · Localization", id: "Nara · Localization", subEn: "English and Indonesian versions", subId: "Versi Inggris dan Indonesia" },
    { key: "qc", en: "Automatic checks", id: "Cek otomatis", subEn: "Banned phrases, unproven claims, length, CTA", subId: "Frasa terlarang, klaim tanpa bukti, panjang, CTA" },
    { key: "human", human: true, en: "Human approval", id: "Persetujuan manusia", subEn: "Your team reviews before anything is published", subId: "Tim kamu mereview sebelum apa pun tayang" },
  ];
}
