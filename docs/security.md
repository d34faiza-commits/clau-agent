# Keamanan Platform CLAU AI

> Status per 2026-10-09: dashboard VPS 1 (frontend Next.js, HTTP via IP) + backend FastAPI read-only (belum di-deploy). Belum ada database, login, atau pemanggilan model AI. Dokumen ini mencatat ancaman yang sudah ditangani, cara memasang perlindungan di server, dan **aturan wajib** sebelum fitur berisiko (login, data client, AI, WhatsApp) dibangun di VPS 2.

## 1. Ringkasan Audit 2026-10-09

| Serangan | Status sekarang | Alasan / perlindungan |
|---|---|---|
| SQL injection | Tidak berlaku sekarang | Belum ada database. Input `/route` dibatasi pola `^[a-z0-9-]+$` (≤ 64). Aturan untuk VPS 2: § 6 |
| SSRF | Tertutup | Server tidak pernah mengambil URL dari input. Optimizer `/_next/image` dimatikan (`images.unoptimized`) |
| CSRF / XSRF | Tidak berlaku sekarang | Tidak ada cookie, sesi, atau endpoint yang mengubah data. Nginx hanya menerima GET/HEAD. Aturan login: § 6 |
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

**RISK**: CSP memakai `script-src 'unsafe-inline'`, karena Next.js menyisipkan data halaman sebagai script inline yang berbeda per halaman. Script dari domain lain tetap diblokir. **NEXT ACTION** saat ada login: pindah ke CSP berbasis nonce (render dinamis + middleware).

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

File di repo: `scripts/deploy/nginx/clau.conf` dan `scripts/deploy/systemd/clau-frontend.service`. **Terpasang di VPS 1 sejak 2026-10-09** (exposure systemd 1.4 OK). Cara memasang ada di [deploy/vps-1-setup.md § 7](./deploy/vps-1-setup.md#7-bagian-12--pengerasan-keamanan-2026-10-09).

- **Nginx**: hanya GET/HEAD, rate limit 20 req/detik per IP (burst 60), maks 30 koneksi per IP, body 16 KB, timeout header/body 10 detik, file tersembunyi (`.git`, `.env`) selalu 404, header `Upgrade` dari klien tidak diteruskan.
- **systemd**: `ProtectSystem=strict` (sistem read-only, kecuali folder rilis), `ProtectHome` (SSH key & deploy key tidak terbaca), `NoNewPrivileges`, tanpa capability, filter syscall, batas memori 1 GB dan 256 proses.

## 5. Supply Chain & Repo

- `npm ci --ignore-scripts` di CI dan di server: script install dari paket npm tidak pernah dijalankan.
- Job CI `audit`: `npm audit --audit-level=high`, `pip-audit --strict`, dan pemindai pola secret. Gagal = PR tidak boleh di-merge.
- `.github/dependabot.yml`: PR update mingguan (minor/patch) untuk npm, pip, dan GitHub Actions. Owner tetap yang merge. Versi **mayor** tidak dibuka otomatis (keputusan owner 2026-10-09, setelah PR TypeScript 5 → 7 merusak `tsc`): dikerjakan sebagai PR tersendiri setelah diuji.
- GitHub Actions dipin ke commit SHA (tag bisa dipindah oleh pihak lain; SHA tidak).
- **NEXT ACTION (owner, GitHub Settings)**: proteksi branch `main` (wajib PR + CI hijau, termasuk job `audit`), karena isi `main` tayang otomatis di VPS 1 dalam ±5 menit.

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
