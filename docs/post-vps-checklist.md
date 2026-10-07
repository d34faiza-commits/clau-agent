# Post-VPS Checklist — Setelah VPS 1 & VPS 2 Siap

> **Pengingat untuk owner & AI agent.** Kerjakan daftar ini segera setelah VPS 1 (dashboard) dan VPS 2 (otak AI) selesai di-setup. Dicatat 2026-10-07 atas permintaan Dea Karisna. Task board: TASK-034 (repo `CLAU-AI-CONTENT`).

## Keputusan setup VPS yang sudah disepakati (2026-10-06)

| # | Keputusan |
|---|---|
| 1 | Tidak ada `api.` publik. Browser → `app.` (VPS 1); Next.js server memanggil VPS 2 lewat Tailscale |
| 2 | Yang di-deploy: repo `clau-ai-agents` (frontend → VPS 1, backend → VPS 2); panduan di `clau-ai-agents/docs/deploy/` |
| 3 | Versi ikut repo: Next.js 16 + Node 22 LTS, Python 3.12, PostgreSQL 16, Redis 7 (semua di-pin) |
| 4 | Nama pilar ikut `clau-ai-core`: Marketing, Sales, Guest Experience, Operations, Analytics |
| 5 | Aturan data per AI provider ditambahkan ke AI-BOUNDARY (Restricted tidak pernah dikirim; data tamu disamarkan; panggilan AI dicatat) |
| 6 | Backup VPS 1 = config tanpa `.env`; backup VPS 2 = DB terenkripsi + config ke Backblaze B2 + tes restore bulanan |

## Setelah VPS siap

- [ ] **1. Hubungkan backend ke model AI.** API key hanya di VPS 2 (`.env` permission 600). Terapkan aturan data per provider (keputusan #5).
- [ ] **2. Jalankan 28 kasus eval ke output nyata.**
  - Generate output untuk setiap kasus di `agents/evals/cases/*.json`.
  - Cek otomatis: `python agents/evals/run_evals.py --agent <id> --outputs outputs.json`.
  - Nilai dengan rubrik di `agents/evals/README.md` oleh owner atau orang yang pernah bekerja di front office/guest relations (bukan pembuat prompt).
  - Lulus: deterministik PASS + rata-rata rubrik ≥ 4, tidak ada dimensi < 3.
- [ ] **3. Tambahkan kasus dari percakapan nyata** yang sudah dianonimkan (tanpa nama tamu, nomor kamar, tanggal menginap, nama properti client).
- [ ] **4. Aktivasi pilar 2–4** (Sales, Guest Experience, Operations) setelah workflow & skill pilarnya di-approve owner: ubah status di `agents/registry.json` dan `core/orchestrator/router.md`, lalu jalankan eval agent terkait.
- [ ] **5. TASK-032 (dynamic approval level)** diimplementasikan saat backend mulai menyimpan draft & approval.
