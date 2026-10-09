// DATA SIMULASI (SIMULATION) untuk pratinjau UI. Semua nama properti fiktif dan mengandung "Contoh".
// Angka di sini bukan hasil bisnis nyata. Ganti dengan data backend setelah VPS 2 tersambung.

export const SIM_DATE = "2026-10-07";

export type ContentStatus = "draft" | "ai_review" | "human_review" | "approved" | "scheduled" | "published";

export type Tone = "neutral" | "info" | "warning" | "success" | "brand" | "navy";
export const STATUS: Record<ContentStatus, { en: string; id: string; tone: Tone }> = {
  draft: { en: "Draft", id: "Draft", tone: "neutral" },
  ai_review: { en: "AI review", id: "Cek AI", tone: "info" },
  human_review: { en: "Human review", id: "Review manusia", tone: "warning" },
  approved: { en: "Approved", id: "Disetujui", tone: "success" },
  scheduled: { en: "Scheduled", id: "Terjadwal", tone: "brand" },
  published: { en: "Published", id: "Tayang", tone: "navy" },
};

export type Format = "post" | "reel" | "story" | "google" | "whatsapp" | "blog" | "other";
export const FORMATS: Record<Format, { en: string; id: string }> = {
  post: { en: "Posts", id: "Post" },
  reel: { en: "Reels", id: "Reels" },
  story: { en: "Stories", id: "Stories" },
  google: { en: "Google", id: "Google" },
  whatsapp: { en: "WhatsApp", id: "WhatsApp" },
  blog: { en: "Blog", id: "Blog" },
  other: { en: "Other", id: "Lainnya" },
};
const FORMAT_OF: Record<string, Format> = {
  "Instagram Post": "post",
  "Instagram Reel": "reel",
  Story: "story",
  "Google Business": "google",
  "WhatsApp Promo": "whatsapp",
  Blog: "blog",
};
/** Jenis konten untuk form "Buat konten": semua jenis yang dihasilkan agent, urut per format. */
export const CONTENT_TYPES = [...Object.keys(FORMAT_OF), "OTA Listing", "Campaign", "Calendar", "Localization", "Report"];
export function formatOf(type: string): Format {
  return FORMAT_OF[type] ?? "other";
}

export const STATUS_ORDER: ContentStatus[] = ["draft", "ai_review", "human_review", "approved", "scheduled", "published"];

export type Client = {
  id: string;
  name: string;
  type: string;
  location: string;
  status: "active" | "onboarding";
  audience: string;
  positioning: string;
  tone: string[];
  services: string[];
  usp: string[];
  social: string[];
  lastActivity: string;
};

export const CLIENTS: Client[] = [
  {
    id: "villa-contoh-uluwatu",
    name: "Villa Contoh Uluwatu",
    type: "Villa",
    location: "Uluwatu, Bali",
    status: "active",
    audience: "Australian travellers, couples & small families",
    positioning: "Luxury relaxed villa",
    tone: ["Elegant", "Relaxed", "Warm", "Premium"],
    services: ["Private pool villa", "In-villa breakfast", "Airport transfer"],
    usp: ["The quiet side of Uluwatu", "Sunset views"],
    social: ["Instagram", "Google Business"],
    lastActivity: "2026-10-07",
  },
  {
    id: "resto-contoh-canggu",
    name: "Resto Contoh Canggu",
    type: "Restaurant",
    location: "Canggu, Bali",
    status: "active",
    audience: "Digital nomads & young travellers",
    positioning: "Casual brunch near the beach",
    tone: ["Friendly", "Relaxed", "Energetic"],
    services: ["Brunch", "Specialty coffee", "Private events"],
    usp: ["Local ingredients", "Open from early morning"],
    social: ["Instagram", "TikTok", "Google Business"],
    lastActivity: "2026-10-06",
  },
  {
    id: "spa-contoh-ubud",
    name: "Spa Contoh Ubud",
    type: "Spa & Wellness",
    location: "Ubud, Bali",
    status: "onboarding",
    audience: "International wellness travellers",
    positioning: "A calm spa in the rice fields",
    tone: ["Calm", "Warm", "Professional"],
    services: ["Traditional massage", "Couples package", "Morning yoga"],
    usp: ["Rice field views", "Certified therapists"],
    social: ["Instagram"],
    lastActivity: "2026-10-03",
  },
];

export type Project = { id: string; client: string; name: string; due: string };

export const PROJECTS: Project[] = [
  { id: "p1", client: "villa-contoh-uluwatu", name: "October 2026 content", due: "2026-10-31" },
  { id: "p2", client: "villa-contoh-uluwatu", name: "Year-end campaign", due: "2026-11-30" },
  { id: "p3", client: "resto-contoh-canggu", name: "October 2026 content", due: "2026-10-31" },
  { id: "p4", client: "spa-contoh-ubud", name: "Onboarding & Voice Card", due: "2026-10-20" },
];

export type ContentItem = {
  id: string;
  title: string;
  type: string;
  client: string;
  project: string;
  status: ContentStatus;
  created: string;
  date: string;
  agent: string;
  level: "L1" | "L2" | "L3";
};

export const CONTENT: ContentItem[] = [
  { id: "c01", title: "Wake up to the quiet side of Uluwatu", type: "Instagram Post", client: "villa-contoh-uluwatu", project: "p1", status: "published", created: "2026-09-28", date: "2026-10-02", agent: "caption-writer", level: "L1" },
  { id: "c02", title: "Morning at the villa: breakfast by the pool", type: "Instagram Reel", client: "villa-contoh-uluwatu", project: "p1", status: "published", created: "2026-09-29", date: "2026-10-04", agent: "reel-scripter", level: "L2" },
  { id: "c03", title: "3 things guests love about Uluwatu", type: "Story", client: "villa-contoh-uluwatu", project: "p1", status: "scheduled", created: "2026-10-03", date: "2026-10-09", agent: "story-writer", level: "L1" },
  { id: "c04", title: "Villa description for Booking.com", type: "OTA Listing", client: "villa-contoh-uluwatu", project: "p1", status: "human_review", created: "2026-10-05", date: "2026-10-10", agent: "listing-writer", level: "L2" },
  { id: "c05", title: "Reply to a 4-star Google review", type: "Google Business", client: "villa-contoh-uluwatu", project: "p1", status: "approved", created: "2026-10-06", date: "2026-10-08", agent: "review-responder", level: "L1" },
  { id: "c06", title: "Sunset from the living room", type: "Instagram Post", client: "villa-contoh-uluwatu", project: "p1", status: "scheduled", created: "2026-10-04", date: "2026-10-12", agent: "caption-writer", level: "L1" },
  { id: "c07", title: "Christmas & New Year campaign plan", type: "Campaign", client: "villa-contoh-uluwatu", project: "p2", status: "human_review", created: "2026-10-06", date: "2026-10-15", agent: "campaign-planner", level: "L2" },
  { id: "c08", title: "November content calendar", type: "Calendar", client: "villa-contoh-uluwatu", project: "p2", status: "draft", created: "2026-10-07", date: "2026-10-20", agent: "calendar-planner", level: "L1" },
  { id: "c09", title: "Weekend brunch: new menu", type: "Instagram Post", client: "resto-contoh-canggu", project: "p3", status: "published", created: "2026-09-30", date: "2026-10-03", agent: "caption-writer", level: "L1" },
  { id: "c10", title: "Behind the bar: morning coffee", type: "Instagram Reel", client: "resto-contoh-canggu", project: "p3", status: "ai_review", created: "2026-10-07", date: "2026-10-11", agent: "reel-scripter", level: "L2" },
  { id: "c11", title: "Private event promo (WhatsApp)", type: "WhatsApp Promo", client: "resto-contoh-canggu", project: "p3", status: "human_review", created: "2026-10-06", date: "2026-10-13", agent: "caption-writer", level: "L2" },
  { id: "c12", title: "Menu in English", type: "Localization", client: "resto-contoh-canggu", project: "p3", status: "approved", created: "2026-10-05", date: "2026-10-09", agent: "localizer", level: "L1" },
  { id: "c13", title: "Stories poll: coffee or tea?", type: "Story", client: "resto-contoh-canggu", project: "p3", status: "scheduled", created: "2026-10-05", date: "2026-10-14", agent: "story-writer", level: "L1" },
  { id: "c14", title: "September performance report", type: "Report", client: "resto-contoh-canggu", project: "p3", status: "published", created: "2026-10-01", date: "2026-10-02", agent: "report-builder", level: "L1" },
  { id: "c15", title: "Meet the spa in the rice fields", type: "Instagram Post", client: "spa-contoh-ubud", project: "p4", status: "draft", created: "2026-10-07", date: "2026-10-18", agent: "caption-writer", level: "L1" },
  { id: "c16", title: "Couples package: listing description", type: "OTA Listing", client: "spa-contoh-ubud", project: "p4", status: "ai_review", created: "2026-10-07", date: "2026-10-21", agent: "listing-writer", level: "L2" },
];

/** Isi pratinjau untuk beberapa konten (fiktif, tanpa klaim bisnis). */
export const PREVIEW: Record<string, { hook: string; caption: string; cta: string; hashtags: string[] }> = {
  c01: {
    hook: "Wake up to the quiet side of Uluwatu.",
    caption: "Slow mornings, a private pool and the sound of the ocean below. This is how the day starts at Villa Contoh Uluwatu.",
    cta: "Save this for your next Bali escape.",
    hashtags: ["#Uluwatu", "#BaliVilla", "#SlowTravel"],
  },
  c06: {
    hook: "The best seat for sunset is the living room.",
    caption: "Floor-to-ceiling windows, a warm breeze and golden light every evening. No need to go anywhere.",
    cta: "Send this to the person you'd watch it with.",
    hashtags: ["#UluwatuSunset", "#BaliVilla"],
  },
  c09: {
    hook: "Weekend brunch just got a new menu.",
    caption: "Fresh local ingredients, specialty coffee and a table near the beach. See you this Saturday.",
    cta: "Save the menu for the weekend.",
    hashtags: ["#Canggu", "#BaliBrunch"],
  },
};

/** Aktivitas agent (SIMULASI). */
export const ACTIVITY: { agent: string; state: "working" | "done"; en: string; id: string; when: string }[] = [
  { agent: "caption-writer", state: "working", en: "Writing captions for Villa Contoh Uluwatu", id: "Menulis caption untuk Villa Contoh Uluwatu", when: "now" },
  { agent: "reel-scripter", state: "working", en: "Preparing a Reel script for Resto Contoh Canggu", id: "Menyiapkan naskah Reel untuk Resto Contoh Canggu", when: "now" },
  { agent: "calendar-planner", state: "working", en: "Planning the November content calendar", id: "Menyusun kalender konten November", when: "now" },
  { agent: "listing-writer", state: "done", en: "Completed the Booking.com listing draft", id: "Menyelesaikan draft listing Booking.com", when: "12m" },
  { agent: "review-responder", state: "done", en: "Drafted a reply to a 4-star Google review", id: "Menyiapkan balasan review Google bintang 4", when: "40m" },
  { agent: "localizer", state: "done", en: "Localized the brunch menu into English", id: "Melokalisasi menu brunch ke bahasa Inggris", when: "2h" },
];

export function clientName(id: string): string {
  return CLIENTS.find((c) => c.id === id)?.name ?? id;
}

export function projectName(id: string): string {
  return PROJECTS.find((p) => p.id === id)?.name ?? id;
}
