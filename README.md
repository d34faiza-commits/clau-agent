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
├── README.md · ACKNOWLEDGMENT.md · LICENSE
├── core/                 # submodule → clau-ai-core
├── agents/
│   ├── README.md
│   └── registry.json     # agent → intent → skill/prompt/template di repo pilar
├── backend/              # FastAPI: /health, /agents, /route (read-only)
│   ├── app/main.py · requirements.txt · pytest.ini
│   └── tests/            # test API + konsistensi registry ↔ core router
├── frontend/             # Next.js 16 (App Router): halaman registry agent
│   ├── app/layout.tsx · app/page.tsx · next.config.mjs · package.json · package-lock.json · tsconfig.json
└── .github/workflows/ci.yml   # pytest backend + build frontend
```

## Setup

```bash
git clone --recurse-submodules https://github.com/d34faiza-commits/clau-ai-agents.git
cd clau-ai-agents

# Backend
cd backend && pip install -r requirements.txt && pytest && uvicorn app.main:app --reload

# Frontend (terminal lain)
cd frontend && npm install && npm run dev
```

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
