# Keamanan Platform CLAU AI

> Status per 2026-10-13: VPS 1 = pratinjau frontend (HTTP via IP, tanpa backend, tanpa login, data SIMULASI). Backend 0.6.0 (PostgreSQL 16, login + 2FA, `/users`, backup terenkripsi) sudah dibangun dan dites lokal/CI, **belum di-deploy** (menunggu VPS 2 + domain/HTTPS). Belum ada pemanggilan model AI. Dokumen ini mencatat ancaman yang sudah ditangani, cara memasang perlindungan di server, dan **aturan wajib** sebelum fitur berisiko (login, data client, AI, WhatsApp) dibangun di VPS 2.

## 1. Ringkasan Audit 2026-10-09

| Serangan | Status sekarang | Alasan / perlindungan |
|---|---|---|
| SQL injection | Tertutup | Semua query lewat SQLAlchemy berparameter; role aplikasi tanpa hak DDL (§ Database). Input `/route` dibatasi pola `^[a-z0-9-]+$` (≤ 64) |
| SSRF | Tertutup | Server tidak pernah mengambil URL dari input. Optimizer `/_next/image` dimatikan (`images.unoptimized`) |
| CSRF / XSRF | Tertutup (backend 0.5.0+) | Token CSRF terikat sesi (HMAC) + cek `Origin`/`Sec-Fetch-Site` + cookie `SameSite=Lax`. VPS 1: Nginx hanya menerima GET/HEAD |
| XSS | Terlindungi | React meng-escape semua teks; satu-satunya `dangerouslySetInnerHTML` adalah skrip tema konstan. CSP membatasi script ke domain sendiri |
| Clickjacking | Tertutup | `X-Frame-Options: DENY` + CSP `frame-ancestors 'none'` |
| Path traversal | Tertutup | Id agent divalidasi sebelum membaca file persona/eval; route dinamis hanya id dari registry (`dynamicParams = false`) |
| Host header injection / DNS rebinding | Tertutup (backend) | `TrustedHostMiddleware` (`CLAU_ALLOWED_HOSTS`) |
| DoS ringan (flood, slowloris, body besar) | Dibatasi | Nginx: rate limit, batas koneksi, body 16 KB, timeout pendek. Backend: body ≤ 16 KB, wajib `Content-Length` |
| Kebocoran informasi | Tertutup | Tanpa `X-Powered-By`/versi Nginx; error tanpa stack trace; `/docs` & `/openapi.json` mati di produksi |
| Mass assignment | Tertutup | Body `/route` menolak field lain (`extra="forbid"`) |
| Supply chain (npm/pip/Actions) | Dikurangi | `npm ci --ignore-scripts` di CI & server; `npm audit` + `pip-audit` di CI; Dependabot; GitHub Actions dipin ke SHA |
| Credential ter-commit | Dicek | Pemindai pola secret di CI; deploy key read-only; tidak ada secret server di GitHub |
| Eskalasi dari proses web | Dikurung | Unit systemd `clau-frontend` dengan sandbox (§ 4) |

Hasil saat audit: `npm audit` 0 kerentanan, `pip-audit` 0 kerentanan, tidak ada credential di repo. `httpx2` di `backend/requirements.txt` dicek: fork resmi `httpx` yang dikelola Pydantic, bukan typosquat.

## 2. Header Keamanan Frontend

Dikirim Next.js untuk semua path (`frontend/next.config.mjs`): `Content-Security-Policy`, `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, `Permissions-Policy` (kamera, mikrofon, lokasi, pembayaran, dll. dimatikan), `Cross-Origin-Opener-Policy`, `Cross-Origin-Resource-Policy`.

**RISK**: CSP memakai `script-src 'unsafe-inline'`, karena Next.js menyisipkan data halaman sebagai script inline yang berbeda per halaman. Script dari domain lain tetap diblokir. **NEXT ACTION** (jatuh tempo: login sudah ada, wajib sebelum login dipakai di VPS 2): pindah ke CSP berbasis nonce (render dinamis + `proxy.ts`).

## 3. Backend (FastAPI)

| Variabel | Default | Produksi (VPS 2) |
|---|---|---|
| `CLAU_ENV` | `development` | `production` (mematikan `/docs` & `/openapi.json`) |
| `CLAU_ALLOWED_HOSTS` | `127.0.0.1,localhost,testserver` | domain API, mis. `api.<domain>` |
| `CLAU_ENABLE_DOCS` | ikut `CLAU_ENV` | jangan diisi `1` di produksi |

Jalankan di produksi di belakang Nginx, hanya listen ke localhost:

```bash
CLAU_ENV=production CLAU_ALLOWED_HOSTS=api.<domain> \
  uvicorn app.main:app --host 127.0.0.1 --port 8000 --no-server-header --proxy-headers --forwarded-allow-ips 127.0.0.1
```

Tidak ada CORS: browser dari domain lain tidak bisa memanggil API. Bila dashboard nanti memanggil API dari domain berbeda, izinkan **hanya** domain dashboard (bukan `*`). Semua dicek di `backend/tests/test_security.py`.

## 4. Server VPS 1 (Nginx + systemd)

File di repo: `scripts/deploy/nginx/clau.conf` dan `scripts/deploy/systemd/` (`clau-frontend`, `clau-deploy`, `clau-config-backup`). Tahap 1 **terpasang di VPS 1 sejak 2026-10-09** (exposure 1.4 OK). Tahap 2 (2026-10-13, `scripts/deploy/vps1-harden.sh`): user khusus, jaringan web dikunci, cek & backup rutin. Cara memasang: [deploy/vps-1-setup.md § 7–8](./deploy/vps-1-setup.md#8-bagian-13--user-khusus-cek--backup-rutin-2026-10-13).

- **Nginx**: hanya GET/HEAD, rate limit 20 req/detik per IP (burst 60), maks 30 koneksi per IP, body 16 KB, timeout header/body 10 detik, file tersembunyi (`.git`, `.env`) selalu 404, header `Upgrade` dari klien tidak diteruskan.
- **systemd**: `ProtectSystem=strict` (semua read-only, termasuk kode rilis), `ProtectHome` (SSH key tidak terbaca), `NoNewPrivileges`, tanpa capability, filter syscall, batas memori 1 GB dan 256 proses. Jaringan hanya localhost + Tailscale (`IPAddressDeny=any`): proses web tidak bisa menghubungi internet.
- **User terpisah (tahap 2)**: `clau-web` menjalankan frontend (tanpa login, tanpa sudo, hanya membaca rilis); `clau-deploy` memiliki `/srv/clau` dan deploy key read-only, sudo hanya `systemctl restart clau-frontend`; user admin `dea` tidak menjalankan aplikasi. Bila aplikasi dibobol, penyerang tidak bisa mengubah kodenya sendiri, membaca deploy key, atau naik ke sudo.
- **Rutin**: `sudo clau-vps1-check` (layanan, header, firewall, SSH, update, disk, Tailscale, file terpasang = repo); backup config mingguan tanpa secret ke `/var/backups/clau/`; update keamanan otomatis dengan reboot 03:30 WITA bila perlu.

### Container (docker-compose.yml, 2026-10-12)

Setara sandbox systemd di atas, untuk kerja lokal dan dasar VPS 2: user non-root (backend uid 10001, frontend `node`), filesystem read-only (hanya `/tmp` dan cache Next.js di tmpfs), `cap_drop: ALL`, `no-new-privileges`, batas memori (512 MB / 1 GB) dan proses, port hanya `127.0.0.1`. Image tidak membawa tool test, compiler, atau `sharp`; `.dockerignore` allowlist sehingga `.env`, `.git`, dan `core/` tidak masuk build context. Diverifikasi job CI `docker` (health, `/docs` 404, Host asing 400, proses bukan root).

### Database (2026-10-12, lokal & dasar VPS 2)

Sudah diterapkan dari § 6: role aplikasi **tanpa hak DDL** (tidak bisa CREATE/ALTER/DROP/TRUNCATE; diuji), akses lewat SQLAlchemy/psycopg dengan parameter (tanpa SQL rakitan string), database tanpa port host (hanya jaringan internal compose), password SCRAM-SHA-256, tiga kredensial terpisah (admin hanya di service `migrate`; backend hanya role aplikasi; diuji `test_env.py`), `audit_log` append-only di level database, dan aturan approval (SIMULASI, review independen, approval per versi, tayang butuh approval) ditolak database sendiri. Backup terenkripsi + uji restore: `scripts/db-backup.sh` / `db-restore.sh --verify` (dites CI). Belum: jadwal otomatis + salinan di luar server (saat VPS 2), dan isolasi data per klien di query endpoint data (Tahap 1 PR 3).

### Login (2026-10-12, Tahap 1 PR 2)

Sudah diterapkan dari § 6: Argon2id, sesi di server (cookie `__Host-` HttpOnly/Secure/SameSite=Lax, token di-hash), CSRF token + cek Origin, kunci akun + throttle per email (tanpa membocorkan email terdaftar), sesi kedaluwarsa (idle 120 menit, maks 12 jam), 2FA TOTP wajib owner (secret terenkripsi, anti-replay), otorisasi peran di server, audit log, tanpa pendaftaran publik. Backend tidak dipanggil browser langsung. 2026-10-13 (0.6.0): audit menyeluruh atas login & database (22 temuan: timing email, race kode 2FA & owner terakhir, brute force ganti password, banjir memori/audit_log, open redirect `?next=`, body besar di `/api`, dll.) ditutup dan dikunci test; QR + kode cadangan 2FA, keluar semua perangkat, tolak password umum, backup terenkripsi + uji restore. Belum: HTTPS + HSTS (wajib sebelum dipakai di server, butuh domain), batas login per IP di Nginx, 2FA untuk `content_lead`, jadwal harian `db-backup.sh` + `purge-sessions` + salin backup ke Backblaze B2 (saat VPS 2).

## 5. Supply Chain & Repo

- `npm ci --ignore-scripts` di CI dan di server: script install dari paket npm tidak pernah dijalankan.
- Job CI `audit`: `npm audit --audit-level=high`, `pip-audit --strict`, dan pemindai pola secret. Gagal = PR tidak boleh di-merge.
- `.github/dependabot.yml`: PR update mingguan (minor/patch) untuk npm, pip, dan GitHub Actions. Owner tetap yang merge. Versi **mayor** tidak dibuka otomatis (keputusan owner 2026-10-09, setelah PR TypeScript 5 → 7 merusak `tsc`): dikerjakan sebagai PR tersendiri setelah diuji.
- GitHub Actions dipin ke commit SHA (tag bisa dipindah oleh pihak lain; SHA tidak). Base image Docker dipin ke digest dengan alasan yang sama; Dependabot (`docker`) memperbaruinya.
- **GitHub Settings (owner, 2026-10-09, dilaporkan owner)**: ruleset branch `main` dibuat (wajib PR, status check `backend`, `frontend`, `audit`, `cross-validate`, blok force push & hapus; approval 0 karena owner tunggal) dan Dependabot alerts + security updates aktif. Alasan: isi `main` tayang otomatis di VPS 1 dalam ±5 menit.
- **Status proteksi `main` (dicek 2026-10-12)**: **RISK**: ruleset **tidak dipaksa** server karena GitHub Free tidak memaksa proteksi di repo private (API: `protected: false`; PR #27 di-merge 8 detik setelah commit bot, sebelum CI jalan). Keputusan owner 2026-10-12: tetap Free, ganti dengan deteksi: workflow `main-guard.yml` (di core, marketing, agents) membuat check merah + email bila commit masuk `main` tanpa PR, di-force push, atau PR di-merge sebelum check wajib hijau. Bot sync menunggu CI hijau sebelum merge. Push langsung tetap **secara teknis bisa**; disiplin owner yang mencegahnya.

## 6. Aturan Wajib Sebelum VPS 2 (Login, Database, AI, WhatsApp)

| Area | Aturan |
|---|---|
| HTTPS | Domain + TLS (Cloudflare/Let's Encrypt) **sebelum** login atau data client apa pun. Lalu HSTS di Nginx: `add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;` |
| SQL injection | Hanya query berparameter / ORM (SQLAlchemy). Dilarang menyusun SQL dengan f-string atau `+`. User database aplikasi tanpa hak DDL. Database hanya listen di localhost/Tailscale |
| Autentikasi | Password di-hash Argon2id; 2FA untuk owner; rate limit + lockout login; sesi kedaluwarsa |
| CSRF | Cookie sesi `HttpOnly; Secure; SameSite=Lax` + token CSRF untuk setiap POST/PUT/PATCH/DELETE; cek header `Origin` |
| Otorisasi | Setiap endpoint cek peran **di server** (owner/content lead/approver). Data dipisah per client (cek `client_id` di setiap query). Approval & review independen dicek di server (rule 08), bukan hanya di UI |
| SSRF | Server hanya memanggil daftar host yang diizinkan (API provider AI, WhatsApp Business, Google). Tolak URL dari input user; blokir IP privat & metadata (`169.254.169.254`, `10/8`, `172.16/12`, `192.168/16`, `127/8`) |
| Prompt injection | Isi dari pihak luar (DM, review, website) diperlakukan sebagai data. AI tidak punya tool publish/kirim (AI-CONSTITUTION §4); aksi Level A hanya per intent & per client |
| Secret | API key hanya di VPS 2 (`.env` permission 600, user service khusus), tidak di repo dan tidak di log. Rotasi bila bocor |
| Webhook | Verifikasi signature (mis. `X-Hub-Signature-256` WhatsApp) dan tolak replay |
| Upload | Batas ukuran & tipe file, simpan di luar web root, nama file acak, scan |
| Log & audit | Audit log approval/perubahan data; jangan simpan data tamu di log |
| Backup | Backup database terenkripsi + uji restore |

## 7. Melaporkan Celah

Temuan celah dilaporkan langsung ke owner (Dea Karisna / d34faiza), **bukan** lewat issue publik. Jangan menguji serangan ke server tanpa izin owner.
