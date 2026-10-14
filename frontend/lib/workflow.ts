// Tipe & helper workflow (kontrak core/shared/api-contracts.md 0.7.0–0.8.0). Aturan di sini hanya untuk
// menampilkan tombol yang relevan; keputusan sebenarnya selalu dicek backend dan database (rule 08).
import { useEffect, useState } from "react";
import { api, type Me, type Membership } from "./auth";

export type Page<T> = { items: T[]; total: number; limit: number; offset: number };
export type Client = { client_code: string; vertical: string; business_type: string; location_area: string | null; approver_role: string; simulation: boolean };
export type WfRequest = {
  id: number; client_code: string; intent: string; pillar: number; agent: string | null; approval_min: string; text: string;
  deadline: string | null; impact: number; risk: number; priority: string; priority_score: number; status: string;
  requested_by: number | null; requested_by_role: string; created_at: string;
};
export type Claim = { id?: number; text: string; category: string; evidence_label: string; source?: string | null; source_date?: string | null; implied?: boolean; fact_key?: string | null };
export type DraftSummary = {
  id: number; request_id: number; client_code: string; brief_id: string | null; fact_sheet_id: number | null; skill: string;
  version: number; mode: "NYATA" | "SIMULASI"; created_by: number | null; agent_id: string | null; created_at: string; latest: boolean;
};
export type Draft = DraftSummary & { content: string; claims: Claim[] };
export type QARecord = { id: number; draft_id: number; gate: string; result: string; reviewer_id: number | null; reviewer_role: string; independent: boolean; created_at: string };
export type Approval = { id: number; draft_id: number; level: string; decision: string; approver_id: number; approver_role: string; channel_ref: string | null; mode: string; decided_at: string };
export type FactAnswer = {
  id: number; fact_sheet_id: number; fact_key: string; decision: "confirmed" | "corrected"; value_before: string | null; value_after: string | null;
  confirmed_by: number; confirmed_by_role: string | null; channel_ref: string | null; confirmed_at: string;
};
export type FactSheet = {
  id: number; client_code: string; version: number; document_ref: string; created_by: number | null; created_at: string;
  approved_at: string | null; approved_by: number | null; approved_by_role: string | null; approval_ref: string | null;
  status: "pending" | "ready" | "approved"; facts_total: number; facts_answered: number;
};
export type Fact = { fact_key: string; category: string; label: string; value: string; status: "pending" | "confirmed" | "corrected"; current_value: string; answers: FactAnswer[] };
export type FactSheetDetail = FactSheet & { facts: Fact[] };
export type Agent = { id: string; display_name: string; intents: string[]; status: string; approval_min: string; pillar: number };

export const LEVELS = ["L1", "L2", "L3"] as const;
export const EVIDENCE_LABELS = ["DATA FINAL", "ASSUMPTION", "CLIENT CONFIRMATION", "FIELD VERIFICATION", "RISK", "NEXT ACTION"] as const;
export const CLAIM_CATEGORIES = [
  "facility", "location", "price", "rating", "certification", "halal-dietary", "food-beverage",
  "treatment", "experience", "capacity", "safety", "license", "itinerary", "other",
] as const;
export const FACTUAL = CLAIM_CATEGORIES.filter((c) => c !== "experience" && c !== "other");
export const QA_GATES = ["claim-verification", "content-review", "privacy-rights-review", "visual-ai-review", "publication-checklist"] as const;
export const QA_RESULTS = ["Pass", "Conditional", "Fail", "N/A"] as const;
export const DECISIONS = ["Approved", "Revise", "Rejected"] as const;
export const VERTICALS = ["accommodation", "food-beverage", "spa-wellness", "experience", "wedding-event", "travel-tour"] as const;
export const FACT_KEY_RE = /^[a-z0-9]+([._-][a-z0-9]+)*$/;
// Referensi bukti/dokumen yang diterima backend (skema aman).
// Tanpa spasi, karakter kontrol, dan karakter tak terlihat (zero-width, bidi) yang memalsukan tampilan link.
export const REF_RE = /^(https:\/\/|mailto:|workspace:\/\/)[^\s\x00-\x1f\x7f-\x9f\u200b-\u200f\u202a-\u202e\u2060-\u2069\ufeff]+$/;

export const AGENCY_WRITERS = new Set(["owner", "content_lead", "content_staff"]);
export const SENIOR = new Set(["owner", "content_lead"]);

/** Peran & batas level untuk satu klien: membership agency diutamakan, lalu scope klien (sama dengan backend). */
export function memberFor(me: Me, client: string): Membership | undefined {
  return me.user.memberships.find((m) => m.scope === "agency") ?? me.user.memberships.find((m) => m.scope === client);
}

export function roleFor(me: Me, client: string): string {
  return memberFor(me, client)?.role ?? "";
}

/** Link hanya untuk https/mailto; workspace:// (arsip internal) ditampilkan sebagai teks. */
export function safeHref(ref: string | null | undefined): string | null {
  return ref && /^(https:\/\/|mailto:)/.test(ref) && REF_RE.test(ref) ? ref : null;
}

export function formatDate(iso: string | null, lang: string): string {
  if (!iso) return "—";
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleString(lang === "id" ? "id-ID" : "en-GB", { dateStyle: "medium", timeStyle: iso.length > 10 ? "short" : undefined, timeZone: "Asia/Makassar" });
}

export type SessionState = "loading" | "ready" | "signed-out" | "unavailable" | "setup";

/** Sesi login: halaman workflow hanya untuk user yang sudah siap (password diganti, 2FA owner aktif). */
export function useSession(): { me: Me | null; state: SessionState } {
  const [me, setMe] = useState<Me | null>(null);
  const [state, setState] = useState<SessionState>("loading");
  useEffect(() => {
    api<Me>("auth/me").then((r) => {
      if (!r.ok) return setState(r.status === 401 ? "signed-out" : "unavailable");
      setMe(r.data);
      setState(r.data.next === "ready" ? "ready" : "setup");
    });
  }, []);
  return { me, state };
}

export const STATUS_TONE: Record<string, string> = {
  open: "neutral", in_progress: "info", approved: "success", rejected: "warning", closed: "neutral",
  pending: "neutral", ready: "info", confirmed: "success", corrected: "warning",
  Approved: "success", Revise: "warning", Rejected: "warning",
  Pass: "success", Conditional: "info", Fail: "warning", "N/A": "neutral",
};

export const STATUS_LABEL: Record<string, [string, string]> = {
  open: ["Open", "Baru"], in_progress: ["In progress", "Dikerjakan"], approved: ["Approved", "Disetujui"],
  rejected: ["Rejected", "Ditolak"], closed: ["Closed", "Ditutup"],
  pending: ["Waiting for client", "Menunggu klien"], ready: ["Ready to approve", "Siap disetujui"],
  confirmed: ["Confirmed", "Benar"], corrected: ["Corrected", "Dikoreksi"],
  Approved: ["Approved", "Disetujui"], Revise: ["Revise", "Revisi"], Rejected: ["Rejected", "Ditolak"],
};
