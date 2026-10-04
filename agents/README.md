# Agents

Definisi agent platform CLAU AI. Setiap agent adalah **pemetaan**: intent (dari orchestrator di core) → skill/prompt/template di repo pilar. Aturan isi konten **tidak** ditulis di sini; agent membaca skill pilar dan tunduk pada `core/AI-CONSTITUTION.md`.

## Registry

Sumber tunggal: [registry.json](./registry.json).

| Field | Arti |
|---|---|
| `id` | Nama agent |
| `pillar` | Nomor pilar (1–5), lihat `core/docs/5-pillar-architecture.md` |
| `status` | `active` atau `planned`. Agent `planned` tidak boleh dijalankan; request-nya dieskalasi |
| `intents` | Intent dari `core/orchestrator/router.md` |
| `skill` / `prompt` / `template` | Artefak di `skill_repo` yang dipakai agent |
| `approval_min` | Level approval minimum (rules pilar bisa menaikkan) |
| `default_forbidden_actions` | Berlaku untuk **semua** agent: publish, kirim ke pihak luar, self-approve, ubah harga/ketersediaan, simpan credential |

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

`backend/tests/test_registry.py` mengecek bahwa intent di registry sama dengan tabel di `core/orchestrator/router.md` (bila submodule `core/` ter-init) dan bahwa setiap agent aktif punya artefak.
