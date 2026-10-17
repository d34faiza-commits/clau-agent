// Tipe & helper AI menulis draft (kontrak core/shared/api-contracts.md 0.9.0 § AI Menulis Draft). UI hanya
// menampilkan; aturan (siapa boleh meminta, batas biaya, level minimum, peminta = pembuat) dicek backend & database.
import type { DraftSummary } from "./workflow";

export type AiJobStatus = "queued" | "running" | "succeeded" | "failed" | "cancelled";
export type AiJob = {
  id: number; request_id: number; client_code: string; agent_id: string; intent: string; kind: string; status: AiJobStatus;
  attempts: number; max_attempts: number; error_code: string | null; fact_sheet_id: number | null; draft_id: number | null;
  requested_by: number | null; created_at: string; finished_at: string | null;
};
export type AiBudget = { scope: string; month: string; limit_micro_usd: number; alert_at_pct: number; updated_by: number | null; updated_at: string | null };
export type AiUsage = {
  month: string; total_micro_usd: number; calls: number;
  budgets: (AiBudget & { spent_micro_usd: number; alert: boolean })[];
  by_client: { client_code: string; cost_micro_usd: number; calls: number }[];
  by_agent: { agent_id: string; cost_micro_usd: number; calls: number }[];
};

export const ACTIVE_JOB = new Set<AiJobStatus>(["queued", "running"]);

/** Draft agent (ditulis AI) punya created_by null; pembuatnya untuk aturan rule 08 = peminta job. */
export function draftAuthor(draft: Pick<DraftSummary, "id" | "created_by" | "agent_id">, jobs: AiJob[]): number | null {
  if (draft.created_by !== null || !draft.agent_id) return draft.created_by;
  return jobs.find((j) => j.draft_id === draft.id)?.requested_by ?? null;
}

/** Kode `ai_jobs.error_code` (daftar tetap di database-schema) → penjelasan untuk staf. */
export const JOB_ERROR: Record<string, [string, string]> = {
  provider_error: ["The AI service returned an error.", "Layanan AI mengembalikan error."],
  provider_unavailable: ["The AI service was unavailable (tried 3 times).", "Layanan AI tidak tersedia (sudah dicoba 3 kali)."],
  refused: ["The AI declined this request. Rephrase the request text.", "AI menolak permintaan ini. Ubah teks permintaannya."],
  invalid_output: ["The AI's answer couldn't be used (for example, too many claims).", "Jawaban AI tidak bisa dipakai (misalnya klaim terlalu banyak)."],
  budget_exceeded: ["This month's AI budget was reached.", "Batas biaya AI bulan ini tercapai."],
  request_closed: ["The request was closed while the AI was writing.", "Permintaan ditutup saat AI sedang menulis."],
  fact_sheet_missing: ["The client has no approved fact sheet anymore.", "Klien tidak lagi punya fact sheet yang disetujui."],
  worker_timeout: ["The AI worker stopped responding (tried 3 times).", "Worker AI berhenti merespons (sudah dicoba 3 kali)."],
  ai_disabled: ["AI was switched off by the owner.", "AI dimatikan owner."],
  cancelled_by_user: ["Cancelled.", "Dibatalkan."],
};

export const JOB_STATUS: Record<AiJobStatus, [string, string]> = {
  queued: ["Waiting in line", "Menunggu antrean"],
  running: ["AI is writing…", "AI sedang menulis…"],
  succeeded: ["Draft ready", "Draft siap"],
  failed: ["Failed", "Gagal"],
  cancelled: ["Cancelled", "Dibatalkan"],
};

export const JOB_TONE: Record<AiJobStatus, string> = { queued: "neutral", running: "info", succeeded: "success", failed: "warning", cancelled: "neutral" };

/** Mikro-USD → "$1.23" (dua desimal; di bawah 1 sen tetap terlihat). */
export function usd(micro: number): string {
  const v = micro / 1_000_000;
  if (micro > 0 && v < 0.01) return "< $0.01";
  return `$${v.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

/** Bulan berjalan dalam WITA, format YYYY-MM (sama dengan backend). */
export function currentMonth(): string {
  const wita = new Date(Date.now() + 8 * 3600_000);
  return `${wita.getUTCFullYear()}-${String(wita.getUTCMonth() + 1).padStart(2, "0")}`;
}
