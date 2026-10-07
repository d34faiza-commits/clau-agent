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
  headwear: Headwear;
  prop: Prop;
};

/** Seragam mengikuti status: Teal Laut untuk agent aktif, Batu (stone) untuk yang belum aktif. */
export type Uniform = { outfit: string; trim: string };
export const UNIFORM: Record<Agent["status"], Uniform> = {
  active: { outfit: "#0F766E", trim: "#134E4A" },
  planned: { outfit: "#78716C", trim: "#44403C" },
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

export const APPROVAL: Record<string, string> = {
  L1: "Dicek satu orang di tim",
  L2: "Dicek orang kedua (bukan pembuat brief)",
  L3: "Wajib persetujuan owner",
};

export const PILLARS: Record<number, string> = {
  1: "Marketing & Content",
  2: "Sales & Reservations",
  3: "Guest Experience & Reputation",
  4: "Operations",
  5: "Analytics & Insights",
};

// Warna kulit & rambut beragam; warna seragam diatur oleh UNIFORM (palet brand).
const SKIN = { light: "#F6D2B4", tan: "#E2A97E", brown: "#B97A52", deep: "#8A5534" };
const HAIR = { black: "#2B211C", brown: "#5A3A26", dark: "#3A2A22" };

const PROFILES: Record<string, Omit<Member, keyof Agent>> = {
  "caption-writer": {
    name: "Tara",
    role: "Penulis Caption",
    tagline: "Menulis caption Instagram, TikTok, dan Facebook dengan hook kuat dan satu ajakan yang jelas.",
    scene: "sawah",
    look: { skin: SKIN.tan, hair: HAIR.black, hairStyle: "bob", headwear: "none", prop: "pen" },
  },
  "reel-scripter": {
    name: "Raka",
    role: "Penulis Naskah Reel",
    tagline: "Menyusun naskah video pendek: hook 3 detik pertama, shot list, dan teks di layar.",
    scene: "pantai",
    look: { skin: SKIN.brown, hair: HAIR.black, hairStyle: "short", headwear: "cap", prop: "clapper" },
  },
  "story-writer": {
    name: "Sekar",
    role: "Penulis Stories",
    tagline: "Membuat rangkaian Stories 3–5 frame yang singkat, interaktif, dan mengajak follower ikut menjawab.",
    scene: "bukit",
    look: { skin: SKIN.light, hair: HAIR.brown, hairStyle: "bun", headwear: "none", prop: "phone" },
  },
  "listing-writer": {
    name: "Bayu",
    role: "Penulis Listing OTA",
    tagline: "Menulis deskripsi properti dan kamar yang lengkap, faktual, dan konsisten di semua OTA.",
    scene: "lobi",
    look: { skin: SKIN.tan, hair: HAIR.dark, hairStyle: "swoop", headwear: "glasses", prop: "tablet" },
  },
  "review-responder": {
    name: "Laras",
    role: "Penanggap Review",
    tagline: "Membalas review tamu dengan tenang dan tulus, dan tahu kapan harus melibatkan owner.",
    scene: "pantai",
    look: { skin: SKIN.brown, hair: "#115E59", hairStyle: "hijab", headwear: "headset", prop: "speech" },
  },
  "calendar-planner": {
    name: "Dimas",
    role: "Perencana Kalender Konten",
    tagline: "Menyusun kalender konten bulanan sesuai musim ramai, hari libur, dan ritme bisnis properti.",
    scene: "sawah",
    look: { skin: SKIN.light, hair: HAIR.black, hairStyle: "curly", headwear: "none", prop: "calendar" },
  },
  "campaign-planner": {
    name: "Ayu",
    role: "Perencana Campaign",
    tagline: "Merencanakan campaign musiman lengkap dengan tujuan, timeline, penawaran, dan risikonya.",
    scene: "bukit",
    look: { skin: SKIN.tan, hair: HAIR.brown, hairStyle: "long", headwear: "beret", prop: "megaphone" },
  },
  localizer: {
    name: "Nara",
    role: "Penyelaras Bahasa ID ↔ EN",
    tagline: "Menyelaraskan konten Indonesia dan Inggris tanpa mengubah makna, nada, atau klaim.",
    scene: "pantai",
    look: { skin: SKIN.deep, hair: HAIR.black, hairStyle: "curly", headwear: "glasses", prop: "globe" },
  },
  "report-builder": {
    name: "Galih",
    role: "Penyusun Laporan",
    tagline: "Merangkum performa bulanan jadi laporan singkat yang jujur pada angka dan mudah dipahami owner.",
    scene: "malam",
    look: { skin: SKIN.tan, hair: HAIR.dark, hairStyle: "short", headwear: "glasses", prop: "chart" },
  },
  "sales-assistant": {
    name: "Intan",
    role: "Asisten Reservasi",
    tagline: "Menyiapkan balasan inquiry: ketersediaan, harga, syarat, dan langkah booking yang jelas.",
    scene: "bukit",
    look: { skin: SKIN.light, hair: HAIR.black, hairStyle: "long", headwear: "headset", prop: "keycard" },
  },
  "guest-messenger": {
    name: "Sari",
    role: "Komunikasi Tamu",
    tagline: "Menyiapkan pesan pre-arrival dan in-stay yang hangat, dengan info yang tamu butuhkan.",
    scene: "lobi",
    look: { skin: SKIN.brown, hair: "#9A3412", hairStyle: "hijab", headwear: "none", prop: "bell" },
  },
  "sop-writer": {
    name: "Teguh",
    role: "Penulis SOP",
    tagline: "Menulis SOP langkah demi langkah dan checklist yang mudah diikuti semua staf.",
    scene: "sawah",
    look: { skin: SKIN.deep, hair: HAIR.black, hairStyle: "swoop", headwear: "none", prop: "clipboard" },
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
