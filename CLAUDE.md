# CLAUDE.md — clau-ai-agents

> Peta repo untuk AI agent. Baca file ini dulu sebelum menjelajah repo. Last updated: 2026-10-07

## 1. Identitas

| Item | Nilai |
|---|---|
| Repo | `d34faiza-commits/clau-ai-agents` (private) |
| Peran | Platform: registry agent, backend FastAPI, frontend Next.js (scaffold) |
| Submodule | `core/` → clau-ai-core |
| Status | Backend v0.2.0 scaffold: belum ada database, auth, atau pemanggilan AI model |

## 2. Peta File

| Path | Fungsi |
|---|---|
| `agents/registry.json` | 12 agent → intent → skill/prompt/template di repo pilar; `default_forbidden_actions`; link `persona` & `evals` |
| `agents/personas/` | Kartu persona per agent (gaya bahasa, etika, batas & eskalasi, contoh) |
| `agents/evals/` | Kasus uji per agent + `run_evals.py` + rubrik "seperti manusia ahli" |
| `backend/app/main.py` | `GET /health`, `GET /agents`, `POST /route` (read-only, tanpa endpoint publish) |
| `backend/tests/` | Test API, konsistensi registry ↔ `core/orchestrator/router.md`, persona & eval |
| `frontend/` | Next.js App Router; halaman registry agent |
| `scripts/` | `sync-submodules.sh`, `check-core-pins.sh` |
| `SUBMODULE.md` | Panduan submodule & GitHub Actions |
| `.github/workflows/` | `ci.yml`, `cross-repo-validate.yml`, `sync-submodules.yml`, `notify-downstream.yml` |
| `docs/post-vps-checklist.md` | **Pengingat:** langkah wajib setelah VPS 1 & 2 siap (AI provider, eval 28 kasus, aktivasi pilar 2–4) |

> 🔔 **Pengingat untuk agent:** bila owner menyebut VPS sudah siap, buka `docs/post-vps-checklist.md` dan ingatkan langkah-langkahnya.

## 3. Command

```bash
git submodule update --init
cd backend && pip install -r requirements.txt && pytest
python agents/evals/run_evals.py --check
cd frontend && npm ci && npm run build
```

Spesifikasi UI/UX (Portal Klien & Studio) dan design tokens ada di repo arsip `CLAU-AI-CONTENT/design/`.

## Aturan Kerja untuk Agent

- Baca `core/AGENTS.md` (instruksi agent lintas repo) dan, untuk aturan induk, `core/AI-CONSTITUTION.md` + `core/AI-BOUNDARY.md`.
- **Otoritas perubahan:** dokumen berstatus Approved hanya diubah atas perintah **Pak Indra** atau **Dea Karisna (d34faiza)**.
- AI **tidak** publish, kirim ke pihak luar, atau self-approve. Review independen L2/L3 = manusia.
- **Jangan** commit data client nyata (brief, fact sheet, caption, harga, foto, data tamu), `.env`, atau credential. Data client nyata ada di Client Workspace (Drive), bukan repo.
- Label evidence dipakai persis: `DATA FINAL`, `ASSUMPTION`, `CLIENT CONFIRMATION`, `FIELD VERIFICATION`, `RISK`, `NEXT ACTION`.
- Commit message: `feat:`, `fix:`, `docs:`, `refactor:`, `chore:`, `test:`. Jalankan validator sebelum push.

- **Tidak boleh** ada endpoint/tombol publish ke platform sosial. Aturan approval (fakta dikonfirmasi, review independen) wajib dicek di server, bukan hanya di UI.
