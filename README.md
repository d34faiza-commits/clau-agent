# clau-ai-agents

**Platform CLAU AI**: tempat agent menjalankan skill dari repo pilar untuk bisnis hospitality Indonesia. Repo ini berisi kode (frontend Next.js, backend FastAPI) dan **registry agent**. Aturan isi konten tidak ditulis di sini; aturan ada di [clau-ai-core](https://github.com/d34faiza-commits/clau-ai-core) (submodule `core/`) dan repo pilar.

> **Status:** Private — v0.1.0, **scaffold** (split dari `CLAU-AI-CONTENT`, 2026-10-04). Belum ada database, autentikasi, atau pemanggilan AI model.

## Prinsip Platform

- Agent **menyiapkan draft**; publish, kirim ke tamu, ubah harga/ketersediaan, dan approval tetap dilakukan **manusia** (`core/AI-CONSTITUTION.md` §4).
- Tidak ada credential akun client di platform; integrasi mengikuti `core/shared/integrations.md`.
- Routing mengikuti `core/orchestrator/router.md`; registry di-test agar konsisten dengan router.

## Struktur

```text
clau-ai-agents/
├── README.md · SUBMODULE.md · ACKNOWLEDGMENT.md · LICENSE
├── core/                 # submodule → clau-ai-core
├── agents/
│   ├── README.md
│   └── registry.json     # agent → intent → skill/prompt/template di repo pilar
├── backend/              # FastAPI: /health, /agents, /pillars, /route (read-only)
│   ├── app/main.py · requirements.txt · pytest.ini
│   └── tests/            # test API + konsistensi registry ↔ core router
├── frontend/             # Next.js 16 (App Router): halaman registry agent
│   ├── app/layout.tsx · app/page.tsx · next.config.mjs · package.json · package-lock.json · tsconfig.json
├── scripts/              # sync-submodules.sh, check-core-pins.sh, deploy/ (VPS 1)
├── docker-compose.yml    # backend + frontend dalam container (port hanya 127.0.0.1)
├── .env.example          # semua variabel environment (tanpa secret); salin ke .env
└── .github/workflows/    # ci.yml, cross-repo-validate.yml, sync-submodules.yml, notify-downstream.yml, main-guard.yml
```

## Setup

Panduan submodule (update, sync, troubleshooting, GitHub Actions): [SUBMODULE.md](./SUBMODULE.md).

```bash
git clone --recurse-submodules https://github.com/d34faiza-commits/clau-ai-agents.git
cd clau-ai-agents

# Backend
cd backend && pip install -r requirements.txt && pytest && uvicorn app.main:app --reload

# Frontend (terminal lain)
cd frontend && npm install && npm run dev
```

### Docker (database + backend + frontend)

```bash
scripts/init-env.sh                        # sekali: .env (chmod 600) + password database acak
docker compose up -d --build --wait        # db → migrate → backend http://127.0.0.1:8000 · frontend http://127.0.0.1:3000
docker compose run --rm backend python -m app.db.seed   # opsional: 4 klien fiktif SIMULASI
docker compose down                        # data tetap di volume db-data (hapus total: down -v)
```

- **Database:** PostgreSQL 16 tanpa port host. Service `migrate` (sekali jalan) membuat role & database lalu menjalankan migrasi Alembic; backend memakai **role aplikasi** tanpa hak DDL dan tidak pernah menerima password admin. Skema = `core/shared/database-schema.md`; Constraint Wajib ditegakkan di database (CHECK + trigger). Detail: [backend/README.md](./backend/README.md#database).

- **Environment:** semua variabel ada di [`.env.example`](./.env.example) beserta artinya. `.env` tidak di-commit; secret (password database, API key AI, WhatsApp) hanya di `.env` lokal/server, tidak pernah di repo ([docs/security.md](./docs/security.md) § 6). Test `backend/tests/test_env.py` memastikan setiap variabel yang dibaca kode tercantum dan tidak ada secret di template.
- **Image:** `backend/Dockerfile` (Python 3.12, dependency runtime saja: `backend/requirements-runtime.txt`) dan `frontend/Dockerfile` (Node 22, Next.js output standalone). Base image dipin ke digest dan diperbarui Dependabot. Build context = root repo dengan `.dockerignore` allowlist, jadi `.env`, `.git`, dan `core/` tidak pernah ikut ke image.
- **Pengamanan container:** user non-root, filesystem read-only, tanpa capability Linux, `no-new-privileges`, batas memori & proses, port hanya di `127.0.0.1` (publik lewat Nginx + TLS). Dicek job CI `docker`.
- **VPS 1** tetap memakai deploy tarik + systemd ([docs/deploy/vps-1-setup.md](./docs/deploy/vps-1-setup.md)); compose ini dipakai untuk kerja lokal dan menjadi dasar deploy VPS 2.

## Roadmap Platform

| Tahap | Isi | Status |
|---|---|---|
| 0 | Scaffold + registry + router statis | ✅ Repo ini |
| 1 | Form request → `POST /requests` + priority engine | Planned |
| 2 | Pemanggilan AI model per skill, simpan draft + tabel klaim | Planned |
| 3 | QA record + approval workflow (review independen L2/L3) | Planned |
| 4 | Database sesuai `core/shared/database-schema.md` | Planned |

Setiap tahap tetap Level 1 otomasi (manusia yang publish), kecuali owner menyetujui level lebih tinggi lewat revisi Constitution.

## Lisensi

Proprietary, private use. Lihat [LICENSE](./LICENSE).
