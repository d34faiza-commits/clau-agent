# Post-VPS Checklist — Setelah VPS 1 & VPS 2 Siap

> **Pengingat untuk owner & AI agent.** Kerjakan daftar ini segera setelah VPS 1 (dashboard) dan VPS 2 (otak AI) selesai di-setup. Dicatat 2026-10-07 atas permintaan Dea Karisna. Task board: TASK-035–039 (repo `CLAU-AI-CONTENT`; TASK-034 selesai).

## Keputusan setup VPS yang sudah disepakati (2026-10-06)

| # | Keputusan |
|---|---|
| 1 | Tidak ada `api.` publik. Browser → `app.` (VPS 1); Next.js server memanggil VPS 2 lewat Tailscale |
| 2 | Yang di-deploy: repo `clau-ai-agents` (frontend → VPS 1, backend → VPS 2); panduan di `clau-ai-agents/docs/deploy/` |
| 3 | Versi ikut repo: Next.js 16 + Node 22 LTS, Python 3.12, PostgreSQL 16, Redis 7 (semua di-pin) |
| 4 | Nama pilar ikut `clau-ai-core` (AI-CONSTITUTION §2): AI Marketing, AI Sales, AI Admin, AI Business Intelligence, AI Automation |
| 5 | Aturan data per AI provider (Restricted tidak pernah dikirim; data tamu disamarkan; panggilan AI dicatat). **NEXT ACTION:** belum tertulis di AI-BOUNDARY (1.2.0); wajib ditambahkan (perintah owner) sebelum langkah 1 di bawah |
| 6 | Backup VPS 1 = config tanpa `.env`; backup VPS 2 = DB terenkripsi tiap 6 jam + Backblaze B2 (Object Lock) + uji restore mingguan; pemulihan manual `clau-vps2-restore` ([`deploy/vps-2-setup.md`](./deploy/vps-2-setup.md) § 5) |

## Setelah VPS siap

- [ ] **0. Keamanan dulu.** Penuhi aturan wajib di [`security.md` § 6](./security.md#6-aturan-wajib-sebelum-vps-2-login-database-ai-whatsapp) (HTTPS, query berparameter, CSRF, otorisasi di server, allowlist SSRF, secret) sebelum login, database, atau data client dipakai.
- [ ] **1. Hubungkan backend ke model AI.** API key hanya di VPS 2 (`.env` permission 600). Terapkan aturan data per provider (keputusan #5).
- [ ] **2. Jalankan 33 kasus eval ke output nyata.**
  - Generate output untuk setiap kasus di `agents/evals/cases/*.json`.
  - Cek otomatis: `python agents/evals/run_evals.py --agent <id> --outputs outputs.json`.
  - Nilai dengan rubrik di `agents/evals/README.md` oleh owner atau orang yang pernah bekerja di front office/guest relations (bukan pembuat prompt).
  - Lulus: deterministik PASS + rata-rata rubrik ≥ 4, tidak ada dimensi < 3.
- [ ] **3. Tambahkan kasus dari percakapan nyata** yang sudah dianonimkan (tanpa nama tamu, nomor kamar, tanggal menginap, nama properti client).
- [ ] **4. Aktivasi pilar 2–5** (AI Sales, AI Admin, AI Business Intelligence, AI Automation) setelah workflow & skill pilarnya di-approve owner: ubah status agent **dan** `pillars` (status + repo) di `agents/registry.json`, tabel pilar di `core/README.md` + `core/docs/5-pillar-architecture.md`, dan `core/orchestrator/router.md`, lalu jalankan eval agent terkait. Level A (kirim otomatis) hanya per intent & per client sesuai AI-CONSTITUTION §4a. Task: TASK-035–039 di board `CLAU-AI-CONTENT/tasks/`.
- [ ] **5. TASK-032 (dynamic approval level)** diimplementasikan saat backend mulai menyimpan draft & approval.
