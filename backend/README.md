# Backend (FastAPI)

API registry agent, router statis, login & kelola user (`/auth/*`, `/users`). **Tidak ada** endpoint yang publish konten, mengirim pesan ke tamu, atau mengubah sistem client (`core/AI-CONSTITUTION.md` §4). Kontrak: `core/shared/api-contracts.md`.

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

PostgreSQL 16 (SQLAlchemy 2 + Alembic + psycopg 3). Skema mengikuti kontrak [`core/shared/database-schema.md`](../core/shared/database-schema.md): 17 tabel di `app/db/models.py`, migrasi di `migrations/versions/`.

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

## Login & Hak Akses (0.5.0, diperkuat 0.6.0)

Kontrak endpoint: [`core/shared/api-contracts.md`](../core/shared/api-contracts.md). Kode: `app/auth/`.

| Aspek | Implementasi |
|---|---|
| Password | Argon2id (RFC 9106), min. 12 karakter, tidak memuat nama email (NIST SP 800-63B, tanpa aturan komposisi). Rehash otomatis bila parameter naik |
| Sesi | Token acak 256-bit di cookie `__Host-clau_session` (`HttpOnly; Secure; SameSite=Lax; Path=/`); database hanya menyimpan SHA-256-nya. Habis setelah 120 menit tidak aktif / 12 jam. Token baru setiap login, ganti password, dan aktifkan 2FA |
| CSRF | Header `X-CSRF-Token` = HMAC(`CLAU_SECRET_KEY`, token sesi) untuk semua POST/PUT/PATCH/DELETE; Origin & `Sec-Fetch-Site` lintas situs ditolak |
| Brute force | 5 gagal per email (juga email tidak terdaftar) = 429 selama 15 menit; akun terdaftar juga dikunci di database dan semua sesinya diputus. Respons **dan waktu respons** email tidak terdaftar/nonaktif = password salah (Argon2 selalu dijalankan). Password salah saat ganti password / buat kode cadangan juga dihitung. Hashing Argon2 dibatasi 3 bersamaan (`CLAU_HASH_CONCURRENCY`) agar banjir login tidak menghabiskan memori. Batas per IP di Nginx saat deploy |
| 2FA | TOTP (RFC 6238), **wajib untuk owner**, aktivasi lewat **QR code** (dibuat di server); secret terenkripsi AES-GCM terikat id user; kode tidak bisa dipakai ulang, juga saat dikirim bersamaan (UPDATE atomik). **10 kode cadangan** sekali pakai (HMAC, ditampilkan sekali; buat ulang dengan password). HP hilang tanpa kode cadangan: `python -m app.auth.cli reset-mfa --email …` di server |
| Perangkat | `Me.active_sessions`; **keluar dari semua perangkat** (`POST /auth/logout-all`). Sesi habis/dicabut dibersihkan saat login dan lewat `python -m app.auth.cli purge-sessions` (jadwalkan harian) |
| Akun | Tidak ada pendaftaran publik. Owner pertama: `python -m app.auth.cli create-owner --email … --name …` (password lewat prompt tersembunyi). User lain dibuat owner (`POST /users`) dengan password sementara yang wajib diganti |
| Hak akses | `app/auth/access.py`: peran dari `memberships`; staf agency melihat semua klien, `client_approver`/`viewer` klien hanya klien miliknya; level approval maksimal per klien. Owner tidak bisa menonaktifkan diri / menghapus owner terakhir (dijaga advisory lock Postgres, aman saat dua owner mengubah bersamaan). Halaman **`/users`** untuk owner |
| Password | Ditolak juga bila hanya kata umum + angka/simbol (`app/auth/common_passwords.txt`, mis. `Password2026!!`, `bismillah12345`) atau urutan angka/huruf |
| Fail closed | `CLAU_SECRET_KEY` kosong/pendek → 503 `auth_unavailable`; database tidak ada → 503 `database_unavailable` |
| Audit | `audit_log`: login, gagal login, logout, ganti password, 2FA aktif/reset, user dibuat/nonaktif/aktif, peran berubah |

```bash
# Owner pertama (sekali), dari root repo:
docker compose run --rm backend python -m app.auth.cli create-owner --email owner@contoh.id --name "Nama Owner"
# Login di http://127.0.0.1:3000 → aktifkan 2FA (wajib owner) → kelola user lewat API /users
```

Test: `tests/test_auth.py` (53 test ke PostgreSQL sungguhan, termasuk replay kode 2FA, rotasi sesi, CSRF, Origin, penguncian, owner terakhir, timing email, kode cadangan). Audit keamanan menyeluruh 2026-10-13: 22 temuan, semua ditutup di 0.6.0.

## Backup & Restore

```bash
scripts/db-backup.sh                                   # backups/clau-<UTC>.dump.enc + .hmac (chmod 600)
scripts/db-restore.sh --verify backups/clau-….dump.enc # uji restore ke database sementara (bulanan)
scripts/db-restore.sh --yes    backups/clau-….dump.enc # ganti isi database (backend dihentikan sementara)
```

`pg_dump` → AES-256 (PBKDF2 600.000 iterasi) dengan `CLAU_BACKUP_PASSPHRASE`, HMAC-SHA256 dicek sebelum restore (file diubah = ditolak). Passphrase disimpan owner terpisah dari backup; salin backup ke luar server (Backblaze B2). Dites di CI job `docker`.

## Belum Ada (Planned)

Endpoint requests/drafts/qa-records/approvals (Tahap 1 PR 3), pemanggilan AI model (Tahap 2, VPS 2).
