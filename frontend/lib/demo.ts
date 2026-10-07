// DATA SIMULASI untuk pratinjau UI. Semua nama properti fiktif dan mengandung "Contoh".
// Angka di sini bukan hasil bisnis nyata. Ganti dengan data backend setelah VPS 2 tersambung.

export const SIM_DATE = "2026-10-07";

export type ContentStatus = "draft" | "ai_review" | "human_review" | "approved" | "scheduled" | "published";

export const STATUS: Record<ContentStatus, { label: string; tone: "neutral" | "info" | "warning" | "success" | "brand" | "navy" }> = {
  draft: { label: "Draft", tone: "neutral" },
  ai_review: { label: "Cek otomatis", tone: "info" },
  human_review: { label: "Review manusia", tone: "warning" },
  approved: { label: "Disetujui", tone: "success" },
  scheduled: { label: "Terjadwal", tone: "brand" },
  published: { label: "Tayang", tone: "navy" },
};

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
    audience: "Wisatawan Australia, pasangan & keluarga kecil",
    positioning: "Villa mewah yang santai",
    tone: ["Elegan", "Santai", "Hangat", "Premium"],
    services: ["Villa private pool", "Sarapan di villa", "Antar-jemput bandara"],
    usp: ["Sisi Uluwatu yang tenang", "Pemandangan matahari terbenam"],
    social: ["Instagram", "Google Business"],
    lastActivity: "2026-10-07",
  },
  {
    id: "resto-contoh-canggu",
    name: "Resto Contoh Canggu",
    type: "Restaurant",
    location: "Canggu, Bali",
    status: "active",
    audience: "Digital nomad & wisatawan muda",
    positioning: "Brunch kasual dekat pantai",
    tone: ["Ramah", "Santai", "Energik"],
    services: ["Brunch", "Kopi spesialti", "Private event"],
    usp: ["Bahan lokal", "Buka sejak pagi"],
    social: ["Instagram", "TikTok", "Google Business"],
    lastActivity: "2026-10-06",
  },
  {
    id: "spa-contoh-ubud",
    name: "Spa Contoh Ubud",
    type: "Spa & Wellness",
    location: "Ubud, Bali",
    status: "onboarding",
    audience: "Wisatawan wellness internasional",
    positioning: "Spa tenang di tengah sawah",
    tone: ["Tenang", "Hangat", "Profesional"],
    services: ["Pijat tradisional", "Paket couple", "Yoga pagi"],
    usp: ["Pemandangan sawah", "Terapis bersertifikat"],
    social: ["Instagram"],
    lastActivity: "2026-10-03",
  },
];

export type Project = { id: string; client: string; name: string; due: string };

export const PROJECTS: Project[] = [
  { id: "p1", client: "villa-contoh-uluwatu", name: "Konten Oktober 2026", due: "2026-10-31" },
  { id: "p2", client: "villa-contoh-uluwatu", name: "Campaign Akhir Tahun", due: "2026-11-30" },
  { id: "p3", client: "resto-contoh-canggu", name: "Konten Oktober 2026", due: "2026-10-31" },
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
  { id: "c02", title: "Pagi di villa: sarapan di tepi kolam", type: "Instagram Reel", client: "villa-contoh-uluwatu", project: "p1", status: "published", created: "2026-09-29", date: "2026-10-04", agent: "reel-scripter", level: "L2" },
  { id: "c03", title: "3 hal yang tamu sukai dari Uluwatu", type: "Story", client: "villa-contoh-uluwatu", project: "p1", status: "scheduled", created: "2026-10-03", date: "2026-10-09", agent: "story-writer", level: "L1" },
  { id: "c04", title: "Deskripsi villa untuk Booking.com", type: "OTA Listing", client: "villa-contoh-uluwatu", project: "p1", status: "human_review", created: "2026-10-05", date: "2026-10-10", agent: "listing-writer", level: "L2" },
  { id: "c05", title: "Balasan review Google bintang 4", type: "Google Business", client: "villa-contoh-uluwatu", project: "p1", status: "approved", created: "2026-10-06", date: "2026-10-08", agent: "review-responder", level: "L1" },
  { id: "c06", title: "Sunset dari ruang tamu", type: "Instagram Post", client: "villa-contoh-uluwatu", project: "p1", status: "scheduled", created: "2026-10-04", date: "2026-10-12", agent: "caption-writer", level: "L1" },
  { id: "c07", title: "Rencana campaign Natal & Tahun Baru", type: "Campaign", client: "villa-contoh-uluwatu", project: "p2", status: "human_review", created: "2026-10-06", date: "2026-10-15", agent: "campaign-planner", level: "L2" },
  { id: "c08", title: "Kalender konten November", type: "Kalender", client: "villa-contoh-uluwatu", project: "p2", status: "draft", created: "2026-10-07", date: "2026-10-20", agent: "calendar-planner", level: "L1" },
  { id: "c09", title: "Brunch weekend: menu baru", type: "Instagram Post", client: "resto-contoh-canggu", project: "p3", status: "published", created: "2026-09-30", date: "2026-10-03", agent: "caption-writer", level: "L1" },
  { id: "c10", title: "Behind the bar: kopi pagi", type: "Instagram Reel", client: "resto-contoh-canggu", project: "p3", status: "ai_review", created: "2026-10-07", date: "2026-10-11", agent: "reel-scripter", level: "L2" },
  { id: "c11", title: "Promo private event (WhatsApp)", type: "WhatsApp Promo", client: "resto-contoh-canggu", project: "p3", status: "human_review", created: "2026-10-06", date: "2026-10-13", agent: "caption-writer", level: "L2" },
  { id: "c12", title: "Menu dalam bahasa Inggris", type: "Lokalisasi", client: "resto-contoh-canggu", project: "p3", status: "approved", created: "2026-10-05", date: "2026-10-09", agent: "localizer", level: "L1" },
  { id: "c13", title: "Polling Stories: kopi atau teh?", type: "Story", client: "resto-contoh-canggu", project: "p3", status: "scheduled", created: "2026-10-05", date: "2026-10-14", agent: "story-writer", level: "L1" },
  { id: "c14", title: "Laporan performa September", type: "Laporan", client: "resto-contoh-canggu", project: "p3", status: "published", created: "2026-10-01", date: "2026-10-02", agent: "report-builder", level: "L1" },
  { id: "c15", title: "Perkenalan spa di tengah sawah", type: "Instagram Post", client: "spa-contoh-ubud", project: "p4", status: "draft", created: "2026-10-07", date: "2026-10-18", agent: "caption-writer", level: "L1" },
  { id: "c16", title: "Paket couple: deskripsi listing", type: "OTA Listing", client: "spa-contoh-ubud", project: "p4", status: "ai_review", created: "2026-10-07", date: "2026-10-21", agent: "listing-writer", level: "L2" },
];

export function clientName(id: string): string {
  return CLIENTS.find((c) => c.id === id)?.name ?? id;
}

export function projectName(id: string): string {
  return PROJECTS.find((p) => p.id === id)?.name ?? id;
}

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"];
export function fmtDate(iso: string): string {
  const [y, m, d] = iso.split("-").map(Number);
  return `${d} ${MONTHS[m - 1]} ${y}`;
}
