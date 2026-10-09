import registry from "../../agents/registry.json";

export type Agent = {
  id: string;
  /** Nama agent; sumber: `agents/registry.json` (disetujui Dea Karisna, 2026-10-07). */
  display_name: string;
  pillar: number;
  status: "active" | "planned";
  intents: string[];
  approval_min: string;
  /** Avatar 3D; `crop` dipakai UI, `figure` mendeskripsikan figur (dicek test_avatars). */
  avatar: { crop: string; master: string; figure: "female" | "male" };
};

export type Text = { en: string; id: string };

// Karakter agent (gaya v1): ciri fisik + alat kerja. Seragam mengikuti status.
export type HairStyle = "short" | "swoop" | "bob" | "bun" | "long" | "curly" | "hijab";
export type Headwear = "none" | "glasses" | "headset" | "beret" | "cap";
export type Prop = "pen" | "clapper" | "phone" | "tablet" | "calendar" | "megaphone" | "globe" | "chart" | "keycard" | "bell" | "clipboard" | "speech";
export type Look = { skin: string; hair: string; hairStyle: HairStyle; headwear: Headwear; prop: Prop };
export type Uniform = { outfit: string; trim: string };
export const UNIFORM: Record<"active" | "planned" | "concept", Uniform> = {
  active: { outfit: "#0F766E", trim: "#134E4A" },
  planned: { outfit: "#64748B", trim: "#334155" },
  concept: { outfit: "#94A3B8", trim: "#64748B" },
};
const SKIN = { light: "#F6D2B4", tan: "#E2A97E", brown: "#B97A52", deep: "#8A5534" };
const HAIR = { black: "#2B211C", brown: "#5A3A26", dark: "#3A2A22" };

export type Member = Agent & {
  /** = `display_name` di registry. */
  name: string;
  role: Text;
  /** Satu kalimat "Your ... specialist." */
  headline: Text;
  tagline: Text;
  capabilities: Text[];
  /** Aksen avatar. Satu nada per agent, tetap dalam keluarga navy/teal/biru. */
  hue: string;
  look: Look;
  uniform: Uniform;
  /** Figur 3D agent (`public/agents/<id>.webp`, crop kepala & bahu dari `agents/avatars/<id>.webp`). */
  image: string;
};

/** Agent konsep dari brief v3. BELUM ada di registry, belum punya persona/eval, tidak bisa dijalankan. */
export type ConceptAgent = { name: string; role: Text; tagline: Text; look: Look; uniform: Uniform; image?: string };

export type Pillar = { id: number; name: Text; status: "active" | "planned"; repo: string | null };

/** Nama & status 5 pilar; sumber: `agents/registry.json` → `pillars` (dicek test_registry terhadap README clau-ai-core). */
export const PILLAR_LIST: Pillar[] = (registry as { pillars: Pillar[] }).pillars;
export const PILLARS: Record<number, Text> = Object.fromEntries(PILLAR_LIST.map((p) => [p.id, p.name]));

export const APPROVAL: Record<string, Text> = {
  L1: { en: "Checked by one team member", id: "Dicek satu orang di tim" },
  L2: { en: "Checked by a second person (not the brief author)", id: "Dicek orang kedua (bukan pembuat brief)" },
  L3: { en: "Owner approval required", id: "Wajib persetujuan owner" },
};

const t = (en: string, id: string): Text => ({ en, id });

const PROFILES: Record<string, Omit<Member, keyof Agent | "name" | "uniform" | "image">> = {
  "caption-writer": {
    role: t("AI Copywriter", "AI Copywriter"),
    headline: t("Your social content specialist.", "Spesialis konten sosial kamu."),
    tagline: t("Writes Instagram, TikTok and Facebook captions with a strong hook and one clear call to action.", "Menulis caption Instagram, TikTok, dan Facebook dengan hook kuat dan satu ajakan yang jelas."),
    capabilities: [t("Captions", "Caption"), t("Hooks", "Hook"), t("CTA", "CTA"), t("Bilingual copy", "Copy dua bahasa")],
    hue: "#0F766E",
    look: { skin: SKIN.tan, hair: HAIR.black, hairStyle: "bob", headwear: "none", prop: "pen" },
  },
  "reel-scripter": {
    role: t("AI Reels Strategist", "AI Reels Strategist"),
    headline: t("Your short-video specialist.", "Spesialis video pendek kamu."),
    tagline: t("Plans Reels with a 3-second hook, a shot list and on-screen text.", "Menyusun Reels dengan hook 3 detik, shot list, dan teks di layar."),
    capabilities: [t("Hooks", "Hook"), t("Shot lists", "Shot list"), t("Video scripts", "Naskah video"), t("Reels concepts", "Konsep Reels")],
    hue: "#0E7490",
    look: { skin: SKIN.brown, hair: HAIR.black, hairStyle: "short", headwear: "cap", prop: "clapper" },
  },
  "story-writer": {
    role: t("AI Stories Specialist", "AI Stories Specialist"),
    headline: t("Your daily engagement specialist.", "Spesialis interaksi harian kamu."),
    tagline: t("Builds short, interactive 3–5 frame Stories sequences.", "Membuat rangkaian Stories 3–5 frame yang singkat dan interaktif."),
    capabilities: [t("Stories", "Stories"), t("Polls & stickers", "Polling & stiker"), t("Engagement", "Interaksi")],
    hue: "#0369A1",
    look: { skin: SKIN.light, hair: HAIR.brown, hairStyle: "bun", headwear: "none", prop: "phone" },
  },
  "listing-writer": {
    role: t("AI Listing Specialist", "AI Listing Specialist"),
    headline: t("Your OTA listing specialist.", "Spesialis listing OTA kamu."),
    tagline: t("Writes complete, factual property and room descriptions that stay consistent across OTAs.", "Menulis deskripsi properti dan kamar yang lengkap, faktual, dan konsisten di semua OTA."),
    capabilities: [t("Room descriptions", "Deskripsi kamar"), t("Facilities", "Fasilitas"), t("OTA consistency", "Konsistensi OTA")],
    hue: "#1E3A5F",
    look: { skin: SKIN.tan, hair: HAIR.dark, hairStyle: "swoop", headwear: "glasses", prop: "tablet" },
  },
  "review-responder": {
    role: t("AI Review Specialist", "AI Review Specialist"),
    headline: t("Your guest reputation specialist.", "Spesialis reputasi tamu kamu."),
    tagline: t("Drafts calm, sincere replies to guest reviews and escalates serious cases to the owner.", "Menyiapkan balasan review yang tenang dan tulus, dan meneruskan kasus berat ke owner."),
    capabilities: [t("Google & OTA reviews", "Review Google & OTA"), t("Apologies", "Permintaan maaf"), t("Escalation", "Eskalasi")],
    hue: "#4338CA",
    look: { skin: SKIN.brown, hair: "#115E59", hairStyle: "hijab", headwear: "headset", prop: "speech" },
  },
  "calendar-planner": {
    role: t("AI Content Planner", "AI Content Planner"),
    headline: t("Your content calendar specialist.", "Spesialis kalender konten kamu."),
    tagline: t("Plans the monthly calendar around high season, public holidays and your business rhythm.", "Menyusun kalender bulanan sesuai musim ramai, hari libur, dan ritme bisnis."),
    capabilities: [t("Monthly calendar", "Kalender bulanan"), t("Content pillars", "Pilar konten"), t("Holidays", "Hari libur")],
    hue: "#047857",
    look: { skin: SKIN.light, hair: HAIR.black, hairStyle: "curly", headwear: "none", prop: "calendar" },
  },
  "campaign-planner": {
    role: t("AI Campaign Strategist", "AI Campaign Strategist"),
    headline: t("Your seasonal campaign specialist.", "Spesialis campaign musiman kamu."),
    tagline: t("Plans seasonal campaigns with goals, timeline, offer terms and risks.", "Merencanakan campaign musiman lengkap dengan tujuan, timeline, syarat penawaran, dan risiko."),
    capabilities: [t("Campaign plans", "Rencana campaign"), t("KPIs", "KPI"), t("Timelines", "Timeline")],
    hue: "#6D28D9",
    look: { skin: SKIN.tan, hair: HAIR.brown, hairStyle: "long", headwear: "beret", prop: "megaphone" },
  },
  localizer: {
    role: t("AI Localization Specialist", "AI Localization Specialist"),
    headline: t("Your bilingual content specialist.", "Spesialis konten dua bahasa kamu."),
    tagline: t("Aligns Indonesian and English content without changing meaning, tone or claims.", "Menyelaraskan konten Indonesia dan Inggris tanpa mengubah makna, nada, atau klaim."),
    capabilities: [t("ID ↔ EN", "ID ↔ EN"), t("Local terms", "Istilah lokal"), t("Claim consistency", "Konsistensi klaim")],
    hue: "#0D9488",
    look: { skin: SKIN.deep, hair: HAIR.black, hairStyle: "curly", headwear: "glasses", prop: "globe" },
  },
  "report-builder": {
    role: t("AI Insights Analyst", "AI Insights Analyst"),
    headline: t("Your reporting specialist.", "Spesialis laporan kamu."),
    tagline: t("Turns monthly performance into a short, honest report the owner can read in 30 seconds.", "Merangkum performa bulanan jadi laporan singkat dan jujur yang bisa dibaca owner dalam 30 detik."),
    capabilities: [t("Monthly report", "Laporan bulanan"), t("Metrics", "Metrik"), t("Recommendations", "Rekomendasi")],
    hue: "#155E75",
    look: { skin: SKIN.tan, hair: HAIR.dark, hairStyle: "short", headwear: "glasses", prop: "chart" },
  },
  "sales-assistant": {
    role: t("AI Reservations Assistant", "AI Reservations Assistant"),
    headline: t("Your inquiry specialist.", "Spesialis inquiry kamu."),
    tagline: t("Drafts replies to inquiries: availability, rates, terms and booking steps.", "Menyiapkan balasan inquiry: ketersediaan, harga, syarat, dan langkah booking."),
    capabilities: [t("DM & WhatsApp inquiries", "Inquiry DM & WhatsApp"), t("Rates & terms", "Harga & syarat"), t("Booking steps", "Langkah booking")],
    hue: "#64748B",
    look: { skin: SKIN.light, hair: HAIR.black, hairStyle: "long", headwear: "headset", prop: "keycard" },
  },
  "guest-messenger": {
    role: t("AI Guest Messaging Specialist", "AI Guest Messaging Specialist"),
    headline: t("Your guest communication specialist.", "Spesialis komunikasi tamu kamu."),
    tagline: t("Drafts warm pre-arrival and in-stay messages with the information guests need.", "Menyiapkan pesan pre-arrival dan in-stay yang hangat dengan info yang tamu butuhkan."),
    capabilities: [t("Pre-arrival", "Pre-arrival"), t("Check-in info", "Info check-in"), t("Follow-up", "Follow-up")],
    hue: "#64748B",
    look: { skin: SKIN.brown, hair: "#9A3412", hairStyle: "hijab", headwear: "none", prop: "bell" },
  },
  "sop-writer": {
    role: t("AI SOP Specialist", "AI SOP Specialist"),
    headline: t("Your operations documentation specialist.", "Spesialis dokumentasi operasional kamu."),
    tagline: t("Writes step-by-step SOPs and checklists every staff member can follow.", "Menulis SOP langkah demi langkah dan checklist yang mudah diikuti semua staf."),
    capabilities: [t("SOPs", "SOP"), t("Checklists", "Checklist"), t("Safety standards", "Standar keselamatan")],
    hue: "#64748B",
    look: { skin: SKIN.deep, hair: HAIR.black, hairStyle: "swoop", headwear: "none", prop: "clipboard" },
  },
};

export const CONCEPT_AGENTS: ConceptAgent[] = [
  { name: "Nova", role: t("AI Brand Strategist", "AI Brand Strategist"), tagline: t("Brand positioning and monthly content strategy.", "Positioning brand dan strategi konten bulanan."), look: { skin: SKIN.light, hair: HAIR.brown, hairStyle: "bob", headwear: "glasses", prop: "chart" }, uniform: UNIFORM.concept, image: "/agents/concept-nova.webp" },
  { name: "Aruna", role: t("AI Visual Director", "AI Visual Director"), tagline: t("Visual concepts and shot direction for photos and video.", "Konsep visual dan arahan foto serta video."), look: { skin: SKIN.tan, hair: HAIR.black, hairStyle: "long", headwear: "beret", prop: "phone" }, uniform: UNIFORM.concept, image: "/agents/concept-aruna.webp" },
  { name: "Dara", role: t("AI Quality Controller", "AI Quality Controller"), tagline: t("Pre-checks every draft against brand and claim rules before human review.", "Cek awal setiap draft terhadap aturan brand dan klaim sebelum review manusia."), look: { skin: SKIN.brown, hair: HAIR.dark, hairStyle: "bun", headwear: "none", prop: "clipboard" }, uniform: UNIFORM.concept, image: "/agents/concept-dara.webp" },
];

export function getTeam(): Member[] {
  return (registry.agents as Agent[]).map((a) => {
    const profile = PROFILES[a.id];
    if (!profile) throw new Error(`frontend/lib/team.ts: profile for agent '${a.id}' is missing`);
    return { ...a, ...profile, name: a.display_name, uniform: UNIFORM[a.status], image: `/${a.avatar.crop.replace(/^frontend\/public\//, "")}` };
  });
}

export function getMember(id: string): Member | undefined {
  return getTeam().find((m) => m.id === id);
}
