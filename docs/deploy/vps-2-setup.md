# VPS 2 — Setup Backend, Database & Login (tanpa domain)

> Panduan dan catatan status VPS 2 (`clau-vps2`): database PostgreSQL, backend, dan frontend dengan login. IP server **tidak** ditulis di repo; gunakan `<IP_VPS_2>`. VPS 1 tetap pratinjau tanpa login ([`vps-1-setup.md`](./vps-1-setup.md)).

## 1. Status (diperbarui 2026-10-15)

| Bagian | Status |
|---|---|
| Server | DATA FINAL — dibuat owner 2026-10-15, Ubuntu 24.04 (kernel 6.8.0-147) |
| Tailscale | DATA FINAL — 2026-10-15: `clau-vps2` tersambung, key expiry dimatikan |
| A–E di bawah | DATA FINAL — 2026-10-15: dijalankan owner. `clau-vps2-check`: db/backend/frontend sehat, backend 0.8.0, login 200, halaman kerja 307, `/docs` 404, container bukan root, HTTPS Tailscale `https://clau-vps2.<tailnet>.ts.net` → frontend, Funnel mati, UFW aktif, SSH tanpa root/password, backup pertama + HMAC, rilis = `release/vps1` (`8b4d0c0`), disk 17%, RAM tersedia 3,1 GB. Satu GAGAL "port publik" = alarm palsu alat cek (alamat Tailscale/loopback ber-akhiran `%tailscale0`/`%lo`), diperbaiki setelahnya |
| F–H di bawah | DATA FINAL — 2026-10-15: SSH publik ditutup (UFW hanya `tailscale0` + 41641/udp, `/etc/clau/ssh-locked`; `--lock-ssh` diperbaiki di #53), akun owner dibuat + login lewat HTTPS Tailscale + 2FA aktif, kode cadangan dibuat ulang setelah sempat terlihat di screenshot, `CLAU_BACKUP_PASSPHRASE` disimpan owner di password manager. `clau-vps2-check`: 0 gagal, 1 perlu dicek (backup luar server) |
| Domain + HTTPS publik | Ditunda (owner belum beli domain). Sampai itu aplikasi **hanya** bisa dibuka anggota tailnet |
| Backup tiap 6 jam + salinan Backblaze B2 + `clau-vps2-restore` | Kode siap (dites dengan database sungguhan + B2 tiruan). NEXT ACTION: jalankan ulang langkah E di server, simpan juga `CLAU_SECRET_KEY` (langkah H baru), lalu langkah I (akun B2). FIELD VERIFICATION: kirim/ambil ke B2 asli + uji Object Lock di server owner |

## 2. Keputusan

- **Tanpa domain dulu:** aplikasi dibuka lewat HTTPS Tailscale (`https://clau-vps2.<tailnet>.ts.net`, sertifikat dari Let's Encrypt lewat Tailscale). Hanya perangkat di tailnet yang bisa membukanya; tidak ada port aplikasi di IP publik. Syarat HTTPS sebelum login ([`security.md` § 6](../security.md#6-aturan-wajib-sebelum-vps-2-login-database-ai-whatsapp)) terpenuhi untuk tim internal. **Klien belum bisa login** sampai domain + HTTPS publik ada.
- **Sementara (beda dengan keputusan VPS #1):** frontend login ikut berjalan di VPS 2 karena VPS 1 belum punya HTTPS. Setelah domain ada, kembali ke keputusan #1 ([`post-vps-checklist.md`](../post-vps-checklist.md)): `app.<domain>` di VPS 1 memanggil backend VPS 2 lewat Tailscale; frontend VPS 2 & `tailscale serve` dimatikan.
- **Port publik:** hanya SSH (sampai `--lock-ssh`) dan UDP 41641 (koneksi langsung Tailscale). Database tidak punya port host; backend & frontend hanya `127.0.0.1`.
- **Deploy:** server menarik branch `release/vps1` (= commit `main` yang CI-nya hijau, AI-BOUNDARY 1.3.0), sama dengan VPS 1. Gagal health check → kembali otomatis ke versi sebelumnya, termasuk skema database (`alembic downgrade`). Migrasi baru → backup database dulu.
- **Backup:** database terenkripsi (AES-256 + HMAC) **setiap 6 jam** (02/08/14/20 WITA), simpan 14 hari di server, uji restore ke database sementara paling sedikit seminggu sekali. Setiap backup juga disalin ke **Backblaze B2** (bucket privat + Object Lock: tidak bisa dihapus dari server, juga oleh penyusup). Data yang bisa hilang saat musibah: paling banyak ±6 jam. `CLAU_BACKUP_PASSPHRASE`, `CLAU_SECRET_KEY`, dan key B2 disimpan owner di password manager.
- **Pemulihan selalu manual:** server yang mati hidup lagi sendiri (data tetap di disk), tapi mengganti isi database dengan backup hanya lewat `sudo clau-vps2-restore` yang dijalankan manusia. Mesin tidak memutuskan data mana yang benar (keputusan owner 2026-10-15).
- Semua yang menyentuh Docker berjalan sebagai root (Docker = setara root). Secret (`.env`, deploy key) chmod 600 milik root.

## 3. Langkah (copy-paste satu baris per perintah)

> Paste **satu perintah per baris**. Saat `sudo` meminta password, ketik password user `dea`.

### A. User admin `dea` + SSH key (lewati bila `ssh dea@<IP_VPS_2>` sudah bisa)

Dari laptop, masuk sebagai root:

```bash
ssh root@<IP_VPS_2>
```

Di server (sebagai root):

```bash
adduser dea
usermod -aG sudo dea
mkdir -p /home/dea/.ssh
cp /root/.ssh/authorized_keys /home/dea/.ssh/
chown -R dea:dea /home/dea/.ssh
chmod 700 /home/dea/.ssh
chmod 600 /home/dea/.ssh/authorized_keys
exit
```

Lalu dari laptop: `ssh dea@<IP_VPS_2>` harus bisa masuk tanpa password server.

### B. Deploy key (read-only) untuk repo `clau-ai-agents`

```bash
sudo mkdir -p /etc/clau
sudo ssh-keygen -t ed25519 -N "" -C clau-vps2-deploy -f /etc/clau/deploy_key
sudo cat /etc/clau/deploy_key.pub
```

Salin baris `ssh-ed25519 ...` yang muncul. Di GitHub: repo **clau-ai-agents** → **Settings** → **Deploy keys** → **Add deploy key** → Title `clau-vps2` → paste → **jangan** centang *Allow write access* → **Add key**.

### C. Ambil repo

```bash
echo "github.com ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIOMqqnkVzrm0SdG6UOoqKLsabgH5C9okWi0dh2l9GKJl" | sudo tee /etc/clau/known_hosts
sudo mkdir -p /srv/clau
sudo GIT_SSH_COMMAND="ssh -i /etc/clau/deploy_key -o IdentitiesOnly=yes -o UserKnownHostsFile=/etc/clau/known_hosts" git clone git@github.com:d34faiza-commits/clau-ai-agents.git /srv/clau/clau-ai-agents
```

Host key di baris pertama = key resmi GitHub ([fingerprint GitHub](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/githubs-ssh-key-fingerprints)).

### D. Aktifkan HTTPS di Tailscale (sekali, di browser)

[login.tailscale.com/admin/dns](https://login.tailscale.com/admin/dns): pastikan **MagicDNS** aktif, lalu di bagian **HTTPS Certificates** klik **Enable HTTPS**. Nama tailnet (`xxxx.ts.net`) akan tercantum di sertifikat publik (Certificate Transparency); isinya hanya nama mesin, bukan data.

### E. Jalankan setup (±10–15 menit, aman diulang)

```bash
sudo bash /srv/clau/clau-ai-agents/scripts/deploy/vps2-setup.sh
```

Di akhir muncul hasil `clau-vps2-check`. Yang diharapkan: **0 gagal**; *PERLU DICEK* untuk SSH publik dan backup luar server masih wajar di tahap ini. Kirim screenshot ke agent.

### F. Kunci SSH hanya lewat Tailscale

Dari laptop yang tersambung Tailscale, keluar lalu masuk lewat alamat Tailscale (`100.x.x.x`, lihat admin Tailscale → Machines):

```bash
ssh dea@<IP_TAILSCALE_VPS_2>
```

Bila berhasil, di server:

```bash
sudo bash /srv/clau/clau-ai-agents/scripts/deploy/vps2-setup.sh --lock-ssh
```

Bila Tailscale suatu saat mati: masuk lewat konsol web provider (Lish), lalu `sudo ufw allow OpenSSH`.

### G. Akun owner pertama

```bash
cd /srv/clau/clau-ai-agents
sudo docker compose run --rm backend python -m app.auth.cli create-owner --email <email-owner> --name "Dea Karisna"
```

Password diketik di prompt tersembunyi. Lalu di laptop/HP yang tersambung Tailscale buka `https://clau-vps2.<tailnet>.ts.net` (alamat lengkap tercetak di akhir langkah E), login, aktifkan 2FA (wajib owner), simpan kode cadangan.

### H. Simpan kunci pemulihan (passphrase backup + secret key)

```bash
sudo grep -E '^(CLAU_BACKUP_PASSPHRASE|CLAU_SECRET_KEY)=' /srv/clau/clau-ai-agents/.env
```

Simpan **dua** nilai (bagian setelah `=`) di password manager owner, terpisah dari server:

- `CLAU_BACKUP_PASSPHRASE`: tanpa ini backup tidak bisa dibuka.
- `CLAU_SECRET_KEY`: data 2FA semua user terenkripsi dengan key ini. Server pengganti tanpa key lama = semua user harus atur ulang 2FA.

Jangan kirim hasil perintah ini, kode cadangan 2FA, atau screenshot-nya ke chat/agent; bila sempat terlihat, buat kode cadangan baru di halaman Account.

### I. Salinan backup di luar server: Backblaze B2 (sekali, ±15 menit)

Tujuan: kalau VPS 2 rusak/terhapus/akun Linode bermasalah, backup tetap ada. File sudah terenkripsi sebelum dikirim; Backblaze tidak bisa membaca isinya. Tampilan web Backblaze bisa sedikit berbeda (ASSUMPTION); kirim screenshot ke agent bila ragu.

1. Daftar di [backblaze.com](https://www.backblaze.com/sign-up/cloud-storage) (B2 Cloud Storage) dan **aktifkan 2FA** akun Backblaze (My Settings → Security).
2. **Buckets → Create a Bucket**:
   - Bucket Unique Name: `clau-backup-` + kata acak (mis. `clau-backup-sawah27`; nama harus unik di seluruh Backblaze)
   - Files in Bucket: **Private**
   - Default Encryption: **Enable**
   - Object Lock: **Enable**
3. Di bucket itu → **Object Lock** → Default Retention Policy: mode **Compliance**, **30 days**. Backup tidak bisa dihapus oleh siapa pun selama 30 hari: tidak oleh orang yang menguasai VPS 2, tidak juga oleh akun Backblaze sendiri (mode Governance bisa dilewati key dengan izin khusus, jadi tidak dipakai). Biayanya tetap kecil karena file backup kecil.
4. Di bucket itu → **Lifecycle Settings** → *Use custom lifecycle rules*: File Path `vps2/`, *Days till hide* **60**, *Days till delete* **1**. Backup lebih dari 60 hari dibersihkan otomatis.
5. **Application Keys → Add a New Application Key**: Name `clau-vps2`, *Allow access to Bucket(s)*: **hanya bucket tadi**, Type of Access: **Read and Write**, lainnya kosong → **Create New Key**. Salin **keyID** dan **applicationKey** ke password manager (key hanya tampil sekali). **Jangan kirim ke chat.**
6. Di server (sesi Tailscale):

```bash
sudo clau-vps2-offsite setup
```

Isi keyID, applicationKey (tidak tampil saat di-paste), dan nama bucket. Yang diharapkan: `OK kirim ke B2 berhasil` dan `OK Object Lock aktif`. Lalu:

```bash
sudo clau-vps2-backup --verify
sudo clau-vps2-check
```

Harus muncul `salinan B2 terakhir 0 jam lalu`. Biaya: ±10 GB pertama gratis; untuk ukuran database CLAU sekarang praktis Rp0 (ASSUMPTION, cek harga di Backblaze).

## 4. Perawatan

| Perintah | Fungsi |
|---|---|
| `sudo clau-vps2-check` | Cek kesehatan & keamanan (layanan, aplikasi, akses Tailscale, SSH, secret, backup, deploy, disk/RAM) |
| `sudo clau-vps2-deploy` / `--force` | Deploy manual / ulangi commit yang pernah gagal |
| `journalctl -u clau2-deploy -n 80` | Log deploy otomatis |
| `sudo clau-vps2-backup --verify` | Backup sekarang (+ salinan B2) + uji restore |
| `sudo clau-vps2-restore --list` | Daftar backup di server dan B2 |
| `sudo clau-vps2-restore` | **Pulihkan database** (§ 5): pilih backup, uji, konfirmasi `PULIHKAN` |
| `sudo clau-vps2-offsite setup` | Isi/ganti key Backblaze B2 (langkah I) |
| `sudo bash /srv/clau/clau-ai-agents/scripts/deploy/vps2-setup.sh` | Pasang ulang setelah file di `scripts/deploy/` berubah |

Update keamanan otomatis; reboot otomatis 03:30 WITA bila kernel baru (aplikasi mati ±2 menit, container hidup lagi sendiri).

## 5. Pemulihan database (selalu manual)

**Kapan dipakai:** data rusak/terhapus karena kesalahan, atau server pengganti setelah VPS 2 hilang. **Bukan** untuk VPS yang sekadar mati/restart: aplikasi hidup lagi sendiri dengan data utuh.

```bash
sudo clau-vps2-restore
```

Yang terjadi, berurutan:

1. Daftar backup di server dan di B2 (waktu WITA, ukuran, lokasi). Ketik nomornya; Enter saja = batal.
2. Backup dari B2 diambil otomatis. Backup yang memakai passphrase lain: diminta passphrase dari password manager (tidak tampil).
3. Backup **diuji dulu** di database sementara (file utuh, bisa dibuka). Backup dari versi aplikasi yang lebih baru ditolak.
4. Perbandingan isi sekarang vs isi backup (jumlah user, klien, request, draft, fact sheet, audit, aktivitas terakhir), plus peringatan bila backup kosong.
5. Ketik `PULIHKAN` (huruf besar). Selain itu = batal, tidak ada yang diubah.
6. Deploy & backup otomatis dijeda, backend berhenti (aplikasi tidak bisa dipakai ±1–3 menit, jadi tidak ada data baru yang terlewat). Isi sekarang **di-backup dulu** (`…-sebelum-restore`, ikut disalin ke B2). Backup dipulihkan ke database baru; database aktif baru ditukar setelah lengkap, skema dinaikkan ke versi kode sekarang, lalu backend dicek sehat. Restore gagal atau backend tidak sehat = database sebelumnya kembali otomatis. Ctrl-C atau SSH terputus selama langkah ini diabaikan supaya tidak berhenti setengah jalan; tetap jangan matikan server.
7. Jejak `database.restore` tercatat di audit log (backup apa, oleh admin server siapa).

Salah pilih backup? Jalankan lagi `sudo clau-vps2-restore` dan pilih baris `(isi sebelum restore)`. Daftar menampilkan 40 backup terbaru (±10 hari); yang lebih lama (B2 menyimpan 60 hari): `sudo clau-vps2-restore --semua`.

Bila muncul "ada sisa restore yang terputus" (server mati di tengah restore): jangan dihapus, kirim pesannya ke agent. Database sisa itu bisa jadi satu-satunya salinan isi sebelumnya.

Sesudahnya: login, cek `/users` (user/password/2FA kembali ke kondisi waktu backup), lalu `sudo clau-vps2-check`.

### VPS 2 hilang total (server baru)

Yang dibutuhkan dari password manager: `CLAU_BACKUP_PASSPHRASE` dan `CLAU_SECRET_KEY` (langkah H), key B2 (langkah I).

1. Buat VPS baru (Ubuntu 24.04), sambungkan Tailscale, lalu langkah A–E seperti biasa.
2. Langkah I nomor 6 saja (`sudo clau-vps2-offsite setup`, key B2 yang sama).
3. Pulihkan sebagai server pengganti:

```bash
sudo clau-vps2-restore --server-pengganti
```

Pilih backup terbaru yang berlokasi **B2** (backup "server" di mesin baru masih kosong), isi passphrase dan secret key lama saat diminta (tidak tampil), lalu ketik `PULIHKAN`. Server baru memakai kunci lama, jadi backup lama tetap terbuka dan 2FA semua user tetap jalan; kunci di password manager tetap sama.
4. Langkah F (kunci SSH), lalu login dengan akun lama (ikut pulih dari backup).
5. Hapus mesin lama di admin Tailscale bila masih tercantum; nama baru bisa jadi `clau-vps2-1` (alamat HTTPS ikut berubah, jalankan ulang langkah E supaya origin login ikut).

Uji coba sekali setelah langkah I selesai (NEXT ACTION, ±30 menit, VPS uji sementara): langkah 1–3 di VPS kecil sementara, cek data tampil, lalu hapus VPS uji itu.

## 6. Berikutnya

- NEXT ACTION: domain + HTTPS publik → klien bisa login; lalu HSTS, CSP nonce, rate limit login per IP di reverse proxy ([`security.md` § 2](../security.md)).
- NEXT ACTION: Tahap 2 (AI menulis draft): API key provider AI hanya di `.env` VPS 2 ([`post-vps-checklist.md`](../post-vps-checklist.md)).
