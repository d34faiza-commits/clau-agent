import registry from "../../agents/registry.json";

export type Agent = {
  id: string;
  pillar: number;
  status: "active" | "planned";
  intents: string[];
  approval_min: string;
};

export type Member = Agent & {
  /** Nama panggilan agent (disetujui Dea Karisna, 2026-10-07). */
  name: string;
  role: string;
  tagline: string;
  focus: string[];
};

export const PILLARS: Record<number, string> = {
  1: "Marketing & Content",
  2: "Sales & Reservations",
  3: "Guest Experience & Reputation",
  4: "Operations",
  5: "Analytics & Insights",
};

export const APPROVAL: Record<string, string> = {
  L1: "Dicek satu orang di tim",
  L2: "Dicek orang kedua (bukan pembuat brief)",
  L3: "Wajib persetujuan owner",
};

const PROFILES: Record<string, Omit<Member, keyof Agent>> = {
  "caption-writer": {
    name: "Tara",
    role: "AI Copywriter",
    tagline: "Caption Instagram, TikTok, dan Facebook dengan hook kuat dan satu ajakan yang jelas.",
    focus: ["Caption", "Hook", "CTA", "Bilingual"],
  },
  "reel-scripter": {
    name: "Raka",
    role: "AI Reels Strategist",
    tagline: "Naskah video pendek: hook 3 detik pertama, shot list, dan teks di layar.",
    focus: ["Hook visual", "Shot list", "Naskah pendek"],
  },
  "story-writer": {
    name: "Sekar",
    role: "AI Stories Writer",
    tagline: "Rangkaian Stories 3–5 frame yang singkat dan interaktif.",
    focus: ["Stories", "Sticker", "Interaksi"],
  },
  "listing-writer": {
    name: "Bayu",
    role: "AI OTA Listing Writer",
    tagline: "Deskripsi properti dan kamar yang lengkap, faktual, dan konsisten di semua OTA.",
    focus: ["Deskripsi kamar", "Fasilitas", "Konsistensi OTA"],
  },
  "review-responder": {
    name: "Laras",
    role: "AI Review Responder",
    tagline: "Balasan review tamu yang tenang dan tulus, dengan eskalasi kasus berat ke owner.",
    focus: ["Review Google/OTA", "Permintaan maaf", "Eskalasi"],
  },
  "calendar-planner": {
    name: "Dimas",
    role: "AI Content Planner",
    tagline: "Kalender konten bulanan sesuai musim ramai, hari libur, dan ritme bisnis.",
    focus: ["Kalender bulanan", "Pilar konten", "Hari libur"],
  },
  "campaign-planner": {
    name: "Ayu",
    role: "AI Campaign Strategist",
    tagline: "Campaign musiman lengkap dengan tujuan, timeline, penawaran, dan risiko.",
    focus: ["Campaign musiman", "KPI", "Timeline"],
  },
  localizer: {
    name: "Nara",
    role: "AI Localizer ID ↔ EN",
    tagline: "Menyelaraskan konten Indonesia dan Inggris tanpa mengubah makna atau klaim.",
    focus: ["Lokalisasi", "Istilah lokal", "Konsistensi klaim"],
  },
  "report-builder": {
    name: "Galih",
    role: "AI Report Analyst",
    tagline: "Laporan bulanan singkat yang jujur pada angka dan mudah dipahami owner.",
    focus: ["Ringkasan", "Metrik", "Rekomendasi"],
  },
  "sales-assistant": {
    name: "Intan",
    role: "AI Reservation Assistant",
    tagline: "Draft balasan inquiry: ketersediaan, harga, syarat, dan langkah booking.",
    focus: ["Inquiry DM/WA", "Harga & syarat", "Langkah booking"],
  },
  "guest-messenger": {
    name: "Sari",
    role: "AI Guest Messenger",
    tagline: "Pesan pre-arrival dan in-stay yang hangat, dengan info yang tamu butuhkan.",
    focus: ["Pre-arrival", "Info check-in", "Follow-up"],
  },
  "sop-writer": {
    name: "Teguh",
    role: "AI SOP Writer",
    tagline: "SOP langkah demi langkah dan checklist yang mudah diikuti semua staf.",
    focus: ["SOP", "Checklist", "Standar keselamatan"],
  },
};

export function getTeam(): Member[] {
  return (registry.agents as Agent[]).map((a) => {
    const profile = PROFILES[a.id];
    if (!profile) throw new Error(`frontend/lib/team.ts: profil untuk agent '${a.id}' belum ada`);
    return { ...a, ...profile };
  });
}

export function getMember(id: string): Member | undefined {
  return getTeam().find((m) => m.id === id);
}
