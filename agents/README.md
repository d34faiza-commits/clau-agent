# Agents

Definisi agent platform CLAU AI. Setiap agent adalah **pemetaan**: intent (dari orchestrator di core) → skill/prompt/template di repo pilar. Aturan isi konten **tidak** ditulis di sini; agent membaca skill pilar dan tunduk pada `core/AI-CONSTITUTION.md`.

## Registry

Sumber tunggal: [registry.json](./registry.json).

### `pillars`

Daftar 5 pilar (`id`, `name.en`/`name.id`, `status`, `repo`). Nama, status, dan repo harus sama dengan tabel **5 Pilar CLAU AI** di `core/README.md` (dicek test). Frontend dan `GET /pillars` membaca dari sini; jangan hardcode nama pilar di kode.

| # | Pilar | Status | Repo |
|---|---|---|---|
| 1 | Marketing & Content | `active` | clau-ai-marketing |
| 2 | Sales & Reservations | `planned` | — |
| 3 | Guest Experience & Reputation | `planned` | — |
| 4 | Operations | `planned` | — |
| 5 | Analytics & Insights | `planned` (intent `report` sementara memakai template Pilar 1) | — |

### `agents`

| Field | Arti |
|---|---|
| `id` | Nama agent |
| `pillar` | Nomor pilar (1–5), lihat `core/docs/5-pillar-architecture.md` |
| `status` | `active` atau `planned`. Agent `planned` tidak boleh dijalankan; request-nya dieskalasi |
| `intents` | Intent dari `core/orchestrator/router.md` |
| `skill` / `prompt` / `template` | Artefak di `skill_repo` yang dipakai agent |
| `approval_min` | Level approval minimum (rules pilar bisa menaikkan) |
| `default_forbidden_actions` | Berlaku untuk **semua** agent: publish, kirim ke pihak luar, self-approve, ubah harga/ketersediaan, simpan credential |
| `persona` | Kartu persona: keahlian, gaya bahasa, batas & eskalasi, contoh bagus vs buruk ([personas/](./personas/README.md)) |
| `evals` | Kasus uji agent ([evals/](./evals/README.md)) |

## Agent Aktif (Pilar 1)

| Agent | Intent | Artefak |
|---|---|---|
| caption-writer | `caption` | skill `draft-caption` |
| reel-scripter | `reel-script` | skill `draft-reel-script` |
| story-writer | `stories` | prompt `stories/stories-sequence` |
| listing-writer | `ota-listing` | skill `write-ota-listing` |
| review-responder | `review-reply` | skill `reply-guest-review` |
| calendar-planner | `content-calendar` | skill `build-content-calendar` |
| campaign-planner | `seasonal-campaign` | skill `plan-seasonal-campaign` |
| localizer | `localize` | skill `localize-content` |
| report-builder | `report` | template `monthly-report` (sementara di Pilar 1) |

Agent `planned`: sales-assistant (Pilar 2), guest-messenger (Pilar 3), sop-writer (Pilar 4).

## Konsistensi

`backend/tests/test_registry.py` mengecek bahwa intent di registry sama dengan tabel di `core/orchestrator/router.md` (bila submodule `core/` ter-init) , bahwa setiap agent aktif punya artefak, dan bahwa `pillars` sama dengan tabel 5 pilar di `core/README.md` (agent aktif di pilar yang masih planned hanya boleh memakai artefak Pilar 1). `backend/tests/test_personas_evals.py` mengecek setiap agent punya kartu persona dan kasus uji yang valid (`python agents/evals/run_evals.py --check`).

## Persona & Eval

Agent menulis seperti **staf ahli yang hangat dan berpengalaman** di bidangnya, dengan suara brand client, tanpa pernah mengaku manusia. Detail: [personas/README.md](./personas/README.md) (12 kartu) dan [evals/README.md](./evals/README.md) (28 kasus + rubrik penilaian manusia).
