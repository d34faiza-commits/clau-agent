import registry from "../../agents/registry.json";

export type HairStyle = "short" | "swoop" | "bob" | "bun" | "long" | "curly" | "hijab";
export type Headwear = "none" | "glasses" | "headset" | "beret" | "cap";
export type Prop =
  | "pen"
  | "clapper"
  | "phone"
  | "tablet"
  | "calendar"
  | "megaphone"
  | "globe"
  | "chart"
  | "keycard"
  | "bell"
  | "clipboard"
  | "speech";
export type Scene = "sawah" | "bukit" | "pantai" | "lobi" | "malam";

export type Look = {
  skin: string;
  hair: string;
  hairStyle: HairStyle;
  outfit: string;
  trim: string;
  headwear: Headwear;
  prop: Prop;
};

export type Agent = {
  id: string;
  pillar: number;
  status: "active" | "planned";
  intents: string[];
  approval_min: string;
};

export type Member = Agent & {
  /** Nama panggilan karakter. Draft UI, menunggu approval owner. */
  name: string;
  role: string;
  tagline: string;
  scene: Scene;
  look: Look;
};

export const PILLARS: Record<number, string> = {
  1: "Marketing & Content",
  2: "Sales & Reservations",
  3: "Guest Experience & Reputation",
  4: "Operations",
  5: "Analytics & Insights",
};

// Warna kulit & rambut beragam; seragam memakai palet brand (primary teal, secondary oranye, chart).
const SKIN = { light: "#F6D2B4", tan: "#E2A97E", brown: "#B97A52", deep: "#8A5534" };
const HAIR = { black: "#2B211C", brown: "#5A3A26", dark: "#3A2A22" };

const PROFILES: Record<string, Omit<Member, keyof Agent>> = {
  "caption-writer": {
    name: "Tara",
    role: "Penulis Caption",
    tagline: "Menulis caption Instagram, TikTok, dan Facebook dengan hook kuat dan satu ajakan yang jelas.",
    scene: "sawah",
    look: { skin: SKIN.tan, hair: HAIR.black, hairStyle: "bob", outfit: "#14B8A6", trim: "#0F766E", headwear: "none", prop: "pen" },
  },
  "reel-scripter": {
    name: "Raka",
    role: "Penulis Naskah Reel",
    tagline: "Menyusun naskah video pendek: hook 3 detik pertama, shot list, dan teks di layar.",
    scene: "pantai",
    look: { skin: SKIN.brown, hair: HAIR.black, hairStyle: "short", outfit: "#FB923C", trim: "#C2410C", headwear: "cap", prop: "clapper" },
  },
  "story-writer": {
    name: "Sekar",
    role: "Penulis Stories",
    tagline: "Membuat rangkaian Stories 3–5 frame yang singkat, interaktif, dan mengajak follower ikut menjawab.",
    scene: "bukit",
    look: { skin: SKIN.light, hair: HAIR.brown, hairStyle: "bun", outfit: "#6366F1", trim: "#4338CA", headwear: "none", prop: "phone" },
  },
  "listing-writer": {
    name: "Bayu",
    role: "Penulis Listing OTA",
    tagline: "Menulis deskripsi properti dan kamar yang lengkap, faktual, dan konsisten di semua OTA.",
    scene: "lobi",
    look: { skin: SKIN.tan, hair: HAIR.dark, hairStyle: "swoop", outfit: "#0F766E", trim: "#042F2E", headwear: "glasses", prop: "tablet" },
  },
  "review-responder": {
    name: "Laras",
    role: "Penanggap Review",
    tagline: "Membalas review tamu dengan tenang dan tulus, dan tahu kapan harus melibatkan owner.",
    scene: "pantai",
    look: { skin: SKIN.brown, hair: "#14B8A6", hairStyle: "hijab", outfit: "#115E59", trim: "#042F2E", headwear: "headset", prop: "speech" },
  },
  "calendar-planner": {
    name: "Dimas",
    role: "Perencana Kalender Konten",
    tagline: "Menyusun kalender konten bulanan sesuai musim ramai, hari libur, dan ritme bisnis properti.",
    scene: "sawah",
    look: { skin: SKIN.light, hair: HAIR.black, hairStyle: "curly", outfit: "#EAB308", trim: "#A16207", headwear: "none", prop: "calendar" },
  },
  "campaign-planner": {
    name: "Ayu",
    role: "Perencana Campaign",
    tagline: "Merencanakan campaign musiman lengkap dengan tujuan, timeline, penawaran, dan risikonya.",
    scene: "bukit",
    look: { skin: SKIN.tan, hair: HAIR.brown, hairStyle: "long", outfit: "#F97316", trim: "#9A3412", headwear: "beret", prop: "megaphone" },
  },
  localizer: {
    name: "Nara",
    role: "Penyelaras Bahasa ID ↔ EN",
    tagline: "Menyelaraskan konten Indonesia dan Inggris tanpa mengubah makna, nada, atau klaim.",
    scene: "pantai",
    look: { skin: SKIN.deep, hair: HAIR.black, hairStyle: "curly", outfit: "#2DD4BF", trim: "#0F766E", headwear: "glasses", prop: "globe" },
  },
  "report-builder": {
    name: "Galih",
    role: "Penyusun Laporan",
    tagline: "Merangkum performa bulanan jadi laporan singkat yang jujur pada angka dan mudah dipahami owner.",
    scene: "malam",
    look: { skin: SKIN.tan, hair: HAIR.dark, hairStyle: "short", outfit: "#6366F1", trim: "#3730A3", headwear: "glasses", prop: "chart" },
  },
  "sales-assistant": {
    name: "Intan",
    role: "Asisten Reservasi",
    tagline: "Menyiapkan balasan inquiry: ketersediaan, harga, syarat, dan langkah booking yang jelas.",
    scene: "bukit",
    look: { skin: SKIN.light, hair: HAIR.black, hairStyle: "long", outfit: "#0D9488", trim: "#134E4A", headwear: "headset", prop: "keycard" },
  },
  "guest-messenger": {
    name: "Sari",
    role: "Komunikasi Tamu",
    tagline: "Menyiapkan pesan pre-arrival dan in-stay yang hangat, dengan info yang tamu butuhkan.",
    scene: "lobi",
    look: { skin: SKIN.brown, hair: "#FB923C", hairStyle: "hijab", outfit: "#C2410C", trim: "#7C2D12", headwear: "none", prop: "bell" },
  },
  "sop-writer": {
    name: "Teguh",
    role: "Penulis SOP",
    tagline: "Menulis SOP langkah demi langkah dan checklist yang mudah diikuti semua staf.",
    scene: "sawah",
    look: { skin: SKIN.deep, hair: HAIR.black, hairStyle: "swoop", outfit: "#57534E", trim: "#292524", headwear: "none", prop: "clipboard" },
  },
};

export function getTeam(): Member[] {
  return (registry.agents as Agent[]).map((a) => {
    const profile = PROFILES[a.id];
    if (!profile) throw new Error(`frontend/lib/team.ts: profil karakter untuk agent '${a.id}' belum ada`);
    return { ...a, ...profile };
  });
}

export function getMember(id: string): Member | undefined {
  return getTeam().find((m) => m.id === id);
}
