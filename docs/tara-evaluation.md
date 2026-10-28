# Tara — isolated evaluation runner

Status: **staging tools**, not production worker integration. Perintah Pak Indra
2026-10-28: maksimalkan Pilar 1 sesuai realita manusia. Provider tetap `fake` pada
worker produksi; modul ini hanya menerima ID dari 60 input SIMULASI yang dipin H2.
Tidak menerima file brief klien, tidak membaca database, tidak menulis approval.

## Prepare without API cost

Build artifact dari `clau-market` pada commit H2 yang sudah direview:

```bash
python scripts/tara_bundle.py check
python scripts/tara_bundle.py build --output /tmp/clau-tara-bundle
```

Di `clau-agent/backend`, dependency evaluasi ada di `requirements.txt`:

```bash
python -m app.ai.tara_eval \
  --bundle /tmp/clau-tara-bundle \
  --expected-digest '<digest dari release H2 yang dipercaya>' \
  --output /private/tara-review-packet
```

Digest harus berasal dari commit/release yang direview, bukan hanya disalin dari
artifact asing. Loader menolak checksum berbeda, duplicate JSON, path traversal,
symlink dan file berlebih. Konteks hanya memilih knowledge vertical dan platform
terkait. Hash context terpisah dari hash bundle/model. Review packet tetap kosong
untuk hasil/skor manusia; menyiapkan packet tidak berarti evaluasi sudah dijalankan.

## Real model on synthetic inputs

Provider Claude mengikuti rancangan sebelumnya; pilihan model **belum ditetapkan**.
Owner mengisi file privat berikut setelah akun, rate, budget, data-retention dan
model snapshot diverifikasi. Jangan menaruh API key di file ini atau chat; key
disediakan lewat secret manager environment worker evaluasi (`ANTHROPIC_API_KEY`).

```json
{
  "mode": "SIMULASI",
  "owner_approved": false,
  "decision_ref": "",
  "retention_review_ref": "",
  "operator_ref": "",
  "budget_micro_usd": null,
  "max_calls": 1,
  "input_micro_usd_per_million": null,
  "output_micro_usd_per_million": null,
  "model_settings": {
    "provider": "anthropic",
    "model": "MODEL_SNAPSHOT_TO_BE_CONFIRMED",
    "temperature_milli": 0,
    "effort": "default",
    "max_output_tokens": 4096,
    "structured_output": true
  }
}
```

```bash
python -m app.ai.tara_eval \
  --bundle /tmp/clau-tara-bundle --expected-digest '<trusted digest>' \
  --config /private/tara-provider.json --case tara-001 \
  --output /private/tara-run-001 --run-real
python -m app.ai.tara_eval_report /private/tara-run-001
```

Model/settings menjadi fingerprint baru pada evaluation manifest; tidak mempromosikan
deployment bundle. Gunakan model snapshot: response model berbeda ditolak. Sesudah
satu call sehat, naikkan `max_calls` dan budget secara eksplisit untuk 60 kasus.
Tanpa `--case`, seluruh matrix dipakai. Config lokal adalah catatan keputusan owner,
bukan pengganti authorization multi-user; jalankan hanya oleh operator terotorisasi.

Rate wajib integer micro-USD per juta token sesuai rate akun aktual; tidak ada harga
default. Reservation adalah estimasi konservatif, **bukan hard cap tagihan provider**;
atur juga budget akun provider. Timeout/error/usage tidak diketahui menghentikan batch,
tanpa retry otomatis atau menganggap biaya nol. Tolakan/truncation tetap mencatat usage
bila tersedia. Tidak ada caching/tools eksternal dalam adapter evaluasi ini.

Output/schema asli selalu divalidasi lokal; schema subset dikirim memakai
`output_config.format` sesuai [structured outputs](https://platform.claude.com/docs/en/build-with-claude/structured-outputs).
[Messages API](https://platform.claude.com/docs/en/api/overview) memakai fixed HTTPS endpoint,
TLS verification dan tanpa redirect. Error body/prompt/key tidak dicetak. File hasil
0600, direktori 0700, metadata console tanpa isi. Tidak ada panggilan nyata yang dianggap
lulus hanya karena adapter/mock tests lulus.

## Review dan batas hasil

Mechanical checks: schema, outcome, style unik, bahasa, panjang editorial, hashtag,
kata terlarang, alt-text IDs, duplicate copy, fact-key provenance. **Belum semantic
claim reconciliation**: model dapat menghilangkan klaim atau menautkan key benar ke
kalimat salah. Semua semantic/consent/cultural checks tetap manusia; `production_ready`
selalu false sampai H3/H4 dan pilot H7 terpenuhi.

Reviewer independen mengisi `human_review` pada hasil privat, menyebut `reviewer_ref`,
`reviewed_at`, `output_sha256` yang sama dengan output yang dibaca, delapan `scores` (1–5): empathy, naturalness, voice_match,
factual_accuracy, usefulness, cultural_sensitivity, clarity, honest_persuasion.
Catat enam hitungan `critical`: critical_hallucination, claim_without_provenance,
cross_client_leakage, privacy_consent_violation, injection_success,
bilingual_factual_mismatch. Reviewer tidak boleh sama dengan operator.
Skor/review terkait persis file output itu; perubahan output membutuhkan review ulang.

Report menghitung denominator seluruh kasus yang direncanakan, termasuk file yang
hilang/gagal. 60 kasus: satu schema failure gagal target 99%. Missing review/unknown
cost tidak diloloskan. Human review tidak dapat dibuat otomatis oleh runner.

## Sebelum menghubungkan production

H3/H4 masih membutuhkan migrasi outcome non-draft/AgentRun, brief+Voice Card+asset
context authoritative, provenance terbaru, scoped tools, evidence immutable yang
terikat content hash, UI reviewer dan gate database. Ini mengikuti migration map
di core `shared/runtime/README.md`; jangan menyimpan clarification sebagai draft kosong
atau menjadikan mechanical pass sebagai approval. Belum ada server/klien yang diaktifkan.
