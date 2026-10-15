# VPS 2 — Setup Backend, Database & Login (tanpa domain)

> Panduan dan catatan status VPS 2 (`clau-vps2`): database PostgreSQL, backend, dan frontend dengan login. IP server **tidak** ditulis di repo; gunakan `<IP_VPS_2>`. VPS 1 tetap pratinjau tanpa login ([`vps-1-setup.md`](./vps-1-setup.md)).

## 1. Status (diperbarui 2026-10-15)

| Bagian | Status |
|---|---|
| Server | DATA FINAL — dibuat owner 2026-10-15, Ubuntu 24.04 (kernel 6.8.0-147) |
| Tailscale | DATA FINAL — 2026-10-15: `clau-vps2` tersambung, key expiry dimatikan |
| A–H di bawah | NEXT ACTION — owner menjalankan; kirim hasil `sudo clau-vps2-check` ke agent |
| Domain + HTTPS publik | Ditunda (owner belum beli domain). Sampai itu aplikasi **hanya** bisa dibuka anggota tailnet |
| Backup di luar server (Backblaze B2) | NEXT ACTION setelah setup |

## 2. Keputusan

- **Tanpa domain dulu:** aplikasi dibuka lewat HTTPS Tailscale (`https://clau-vps2.<tailnet>.ts.net`, sertifikat dari Let's Encrypt lewat Tailscale). Hanya perangkat di tailnet yang bisa membukanya; tidak ada port aplikasi di IP publik. Syarat HTTPS sebelum login ([`security.md` § 6](../security.md#6-aturan-wajib-sebelum-vps-2-login-database-ai-whatsapp)) terpenuhi untuk tim internal. **Klien belum bisa login** sampai domain + HTTPS publik ada.
- **Sementara (beda dengan keputusan VPS #1):** frontend login ikut berjalan di VPS 2 karena VPS 1 belum punya HTTPS. Setelah domain ada, kembali ke keputusan #1 ([`post-vps-checklist.md`](../post-vps-checklist.md)): `app.<domain>` di VPS 1 memanggil backend VPS 2 lewat Tailscale; frontend VPS 2 & `tailscale serve` dimatikan.
- **Port publik:** hanya SSH (sampai `--lock-ssh`) dan UDP 41641 (koneksi langsung Tailscale). Database tidak punya port host; backend & frontend hanya `127.0.0.1`.
- **Deploy:** server menarik branch `release/vps1` (= commit `main` yang CI-nya hijau, AI-BOUNDARY 1.3.0), sama dengan VPS 1. Gagal health check → kembali otomatis ke versi sebelumnya, termasuk skema database (`alembic downgrade`). Migrasi baru → backup database dulu.
- **Backup:** database terenkripsi (AES-256 + HMAC) setiap hari 02:00 WITA, simpan 14 hari, uji restore setiap Minggu. Passphrase `CLAU_BACKUP_PASSPHRASE` disimpan owner di password manager.
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

### H. Simpan passphrase backup

```bash
sudo grep CLAU_BACKUP_PASSPHRASE /srv/clau/clau-ai-agents/.env
```

Simpan nilainya di password manager owner (terpisah dari server). Tanpa passphrase ini backup tidak bisa dibuka.

## 4. Perawatan

| Perintah | Fungsi |
|---|---|
| `sudo clau-vps2-check` | Cek kesehatan & keamanan (layanan, aplikasi, akses Tailscale, SSH, secret, backup, deploy, disk/RAM) |
| `sudo clau-vps2-deploy` / `--force` | Deploy manual / ulangi commit yang pernah gagal |
| `journalctl -u clau2-deploy -n 80` | Log deploy otomatis |
| `sudo clau-vps2-backup --verify` | Backup sekarang + uji restore |
| `cd /srv/clau/clau-ai-agents && sudo scripts/db-restore.sh --yes backups/<file>.dump.enc` | Pulihkan database dari backup (backend berhenti sebentar) |
| `sudo bash /srv/clau/clau-ai-agents/scripts/deploy/vps2-setup.sh` | Pasang ulang setelah file di `scripts/deploy/` berubah |

Update keamanan otomatis; reboot otomatis 03:30 WITA bila kernel baru (aplikasi mati ±2 menit, container hidup lagi sendiri).

## 5. Berikutnya

- NEXT ACTION: salinan backup ke Backblaze B2 (bucket privat, key khusus tulis).
- NEXT ACTION: domain + HTTPS publik → klien bisa login; lalu HSTS, CSP nonce, rate limit login per IP di reverse proxy ([`security.md` § 2](../security.md)).
- NEXT ACTION: Tahap 2 (AI menulis draft): API key provider AI hanya di `.env` VPS 2 ([`post-vps-checklist.md`](../post-vps-checklist.md)).
