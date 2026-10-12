# Backend (FastAPI scaffold)

API read-only di atas registry agent dan router statis. **Tidak ada** endpoint yang publish konten, mengirim pesan ke tamu, atau mengubah sistem client (`core/AI-CONSTITUTION.md` §4). Kontrak: `core/shared/api-contracts.md`.

## Jalankan

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload          # http://127.0.0.1:8000/docs
pytest                                  # test API + konsistensi registry ↔ core router
```

`requirements.txt` = semua dependency (termasuk test). `requirements-runtime.txt` = yang masuk image Docker saja; pin keduanya harus sama (dites `tests/test_env.py`). Image: `docker build -f backend/Dockerfile -t clau-backend .` dari root repo, atau `docker compose up` (lihat README root). Variabel environment: [`../.env.example`](../.env.example).

## Endpoint

| Method & path | Fungsi |
|---|---|
| `GET /health` | Status service |
| `GET /agents` | Daftar agent dari `../agents/registry.json` + forbidden actions |
| `GET /pillars` | 5 pilar dari `../agents/registry.json` (nama, status, repo) + id agent per pilar |
| `POST /route` | `{"intent": "caption"}` → agent, pilar, skill, repo, approval minimum, otonomi maksimum (`autonomy_max`), status |

## Keamanan

Input dibatasi, body ≤ 16 KB, Host divalidasi, header keamanan di setiap respons, tanpa CORS, error tanpa detail internal, `/docs` mati bila `CLAU_ENV=production`. Detail dan cara menjalankan di produksi: [`../docs/security.md`](../docs/security.md) § 3; tes: `tests/test_security.py`.

## Database

PostgreSQL 16 (SQLAlchemy 2 + Alembic + psycopg 3). Skema mengikuti kontrak [`core/shared/database-schema.md`](../core/shared/database-schema.md): 15 tabel di `app/db/models.py`, migrasi di `migrations/versions/`.

| Aturan (Constraint Wajib kontrak) | Ditegakkan oleh |
|---|---|
| Mode SIMULASI tidak pernah `Approved` | CHECK `ck_approvals_simulasi_not_approved` |
| Mode approval = mode draft | trigger `clau_approval_rules` |
| Approval L2/L3 butuh claim verification **independen** yang `Pass`/`Conditional` | trigger `clau_approval_rules` |
| Tidak ada catatan tayang tanpa approval `Approved` untuk versi draft yang sama | trigger `clau_publication_requires_approval` |
| `DATA FINAL` wajib sumber + tanggal sumber | CHECK `ck_claims_data_final_sourced` |
| Reviewer independen ≠ pembuat draft; agent tidak pernah independen | trigger `clau_qa_reviewer_not_author` + CHECK `ck_qa_records_independent_is_human` |
| Approval terikat versi: isi draft yang tersimpan tidak bisa diubah (revisi = versi baru) | trigger `clau_draft_version_immutable` |
| `audit_log` append-only (juga untuk pemilik tabel) | trigger + hak UPDATE/DELETE/TRUNCATE dicabut |
| Label evidence, kategori klaim, vertical, priority, level, peran: nilai persis | CHECK (sumber enum: `content-brief.schema.json`, priority engine, rule 08) |

Pelanggaran aturan = error SQLSTATE `23514` dengan pesan berawalan kode aturan (mis. `approval_needs_independent_review: …`), siap dipetakan ke error kontrak API.

**Role terpisah** (`app/db/bootstrap.py`, docs/security.md § 6): role migrasi = pemilik schema; role aplikasi = SELECT/INSERT/UPDATE/DELETE saja (tanpa CREATE/ALTER/DROP/TRUNCATE). Password SCRAM-SHA-256. Database tanpa port host.

```bash
# Dengan Docker (dari root repo): migrasi jalan otomatis di service `migrate`
docker compose run --rm backend python -m app.db.seed     # data contoh SIMULASI (idempoten)

# Ubah skema: ubah app/db/models.py, lalu buat migrasi baru (jangan ubah migrasi yang sudah di main)
CLAU_MIGRATION_DATABASE_URL=postgresql+psycopg://clau_migrator:<pw>@127.0.0.1:5432/clau \
  alembic revision --autogenerate -m "<ringkas>"
```

**Test database** (`tests/test_db.py`, 31 test) butuh PostgreSQL: set `CLAU_TEST_DB_ADMIN_URL` ke superuser Postgres sekali pakai, mis. `docker run -d -e POSTGRES_PASSWORD=x -p 127.0.0.1:55432:5432 postgres:16` lalu `CLAU_TEST_DB_ADMIN_URL=postgresql://postgres:x@127.0.0.1:55432/postgres pytest`. Tanpa variabel itu test database dilewati; di CI wajib (`CLAU_REQUIRE_DB_TESTS=1`). Test juga memastikan model = migrasi, migrasi bisa downgrade/upgrade, dan tabel = kontrak core.

## Belum Ada (Planned)

Autentikasi (Tahap 1 PR 2), endpoint requests/drafts/qa-records/approvals (PR 3), pemanggilan AI model (Tahap 2, VPS 2).
