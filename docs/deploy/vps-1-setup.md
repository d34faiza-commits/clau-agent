# VPS 1 — Setup Dashboard (Frontend)

> Panduan dan catatan status setup VPS 1 (`clau-vps1`), server untuk frontend Next.js. Keputusan dasar ada di [`../post-vps-checklist.md`](../post-vps-checklist.md). IP server **tidak** ditulis di repo; gunakan `<IP_VPS_1>`.

## 1. Status (diperbarui 2026-10-09)

| Bagian | Status |
|---|---|
| 1–5. OS, hostname, user admin `dea` + SSH key | DATA FINAL — Ubuntu 24.04 LTS, kernel 6.8.0-146, 2 vCPU / 3.8 GB RAM / 79 GB |
| 6. Hardening (UFW, sshd, fail2ban, unattended-upgrades) | DATA FINAL — diverifikasi: UFW active (22/80/443), root & password login ditolak, fail2ban jail `sshd` active |
| 7a–7b. Node 22 + Nginx + swap 2 GB | DATA FINAL — 2026-10-07 |
| 7c. Tailscale | DATA FINAL — 2026-10-09: dipasang ulang (cek 2026-10-08 menemukan `tailscale` tidak terpasang dan `tailscaled` inactive), join ulang sebagai `clau-vps1`, `tailscaled` active. Entri lama offline diganti nama `clau-vps1-aja`. Users: Dea Karisna (Owner), Pak Indra (Admin, sejak 2026-10-07). NEXT ACTION: hapus entri `clau-vps1-aja`, disable key expiry `clau-vps1`, ACL setelah VPS 2 join |
| 8. Deploy frontend (akses via IP, HTTP) | DATA FINAL — 2026-10-07: service `clau-frontend` active, Nginx proxy ke 127.0.0.1:3000, halaman registry tampil di `http://<IP_VPS_1>` |
| 9. Auto-deploy dari repo (pull-based) | DATA FINAL — 2026-10-07: `clau-deploy.timer` aktif (5 menit), service frontend memakai `/srv/clau/current` |
| Cek kesehatan 2026-10-08 | DATA FINAL — `clau-frontend`, nginx, fail2ban, `clau-deploy.timer` active; `/team` HTTP 200; rilis live = `main` (`8948618`), commit tanpa perubahan frontend dilewati build; UFW 22/80/443; disk 11%, RAM tersedia 3,3 GB; 0 update keamanan tertunda |
| 10. Domain + Cloudflare + SSL | Ditunda — domain belum ditentukan |
| 11. Backup config (tanpa `.env`) | Ditunda — setelah domain & Tailscale |
| 12. Pengerasan keamanan aplikasi (header, Nginx, sandbox systemd) | DATA FINAL — 2026-10-09: rilis `8acf7a4` live (CSP & `X-Frame-Options: DENY` ada, `X-Powered-By` hilang); Nginx `scripts/deploy/nginx/clau.conf` terpasang (`nginx -t` OK; `/` 200, POST 405, `/.env` 404); `clau-frontend.service` sandbox terpasang, `active`, `systemd-analyze security` = **1.4 OK**. Backup: `/etc/nginx/sites-available/clau.bak`, `/etc/systemd/system/clau-frontend.service.bak`. Proteksi `main` + Dependabot alerts: aktif (owner, 2026-10-09) |

## 2. Aturan

- Login hanya `ssh dea@<IP_VPS_1>` dengan SSH key. Root login dan password login **mati**.
- Paste **satu perintah per baris** saat ada `sudo` (baris berikutnya bisa terbaca sebagai password).
- Tetap di Ubuntu 24.04 LTS. **Jangan** `do-release-upgrade` tanpa rencana terpisah.
- VPS 1 **tidak** menyimpan API key AI atau database (keputusan #1, #6). Semua itu di VPS 2.
- Port publik hanya 22, 80, 443. App Next.js listen di `127.0.0.1:3000` dan hanya diakses lewat Nginx.

## 3. Bagian 1–6 — Akses & Hardening (sudah selesai)

```bash
# sebagai root (sekali, lalu root login dimatikan)
hostnamectl set-hostname clau-vps1
adduser dea && usermod -aG sudo dea
mkdir -p /home/dea/.ssh && cp /root/.ssh/authorized_keys /home/dea/.ssh/
chown -R dea:dea /home/dea/.ssh && chmod 700 /home/dea/.ssh && chmod 600 /home/dea/.ssh/authorized_keys

# sebagai dea
sudo apt update && sudo apt -y full-upgrade
sudo apt -y install ufw fail2ban unattended-upgrades
sudo dpkg-reconfigure -plow unattended-upgrades

sudo ufw default deny incoming && sudo ufw default allow outgoing
sudo ufw allow OpenSSH && sudo ufw allow 80/tcp && sudo ufw allow 443/tcp
sudo ufw enable

# 00- supaya menang dari 50-cloud-init.conf (sshd memakai nilai pertama yang ditemukan)
printf "PermitRootLogin no\nPasswordAuthentication no\nKbdInteractiveAuthentication no\n" | sudo tee /etc/ssh/sshd_config.d/00-clau.conf
sudo mkdir -p /run/sshd          # Ubuntu 24.04 (socket activation): wajib sebelum sshd -t
sudo sshd -t && sudo systemctl restart ssh

printf "[sshd]\nenabled = true\nbackend = systemd\nmaxretry = 5\nfindtime = 10m\nbantime = 1h\n" | sudo tee /etc/fail2ban/jail.local
sudo systemctl enable --now fail2ban
sudo reboot                      # memuat kernel baru
```

Verifikasi:

```bash
sudo ufw status verbose                       # active; 22, 80, 443 ALLOW IN
sudo sshd -T | grep -E "permitrootlogin|passwordauthentication|kbdinteractive"   # semua no
sudo fail2ban-client status sshd              # jail aktif
ssh root@<IP_VPS_1>                           # dari laptop: Permission denied (publickey)
```

## 4. Bagian 7 — Runtime

```bash
curl -fsSL https://deb.nodesource.com/setup_22.x -o /tmp/nodesource_setup.sh
sudo bash /tmp/nodesource_setup.sh
sudo apt -y install nodejs nginx
node -v                                       # v22.x
sudo systemctl is-active nginx                # active
```

Swap 2 GB (default 495 MB terlalu kecil untuk `next build` di RAM 3.8 GB):

```bash
sudo swapon --show                            # catat nama file swap lama bila ada
sudo fallocate -l 2G /swapfile2 && sudo chmod 600 /swapfile2
sudo mkswap /swapfile2 && sudo swapon /swapfile2
echo '/swapfile2 none swap sw 0 0' | sudo tee -a /etc/fstab
```

Tailscale (7c), tailnet milik Dea Karisna: `curl -fsSL https://tailscale.com/install.sh | sh`, lalu `sudo tailscale up --hostname=clau-vps1` dan login lewat link yang muncul. Di admin console: Disable key expiry untuk `clau-vps1`, undang Pak Indra sebagai Admin.

## 5. Bagian 8 — Deploy Frontend

Repo private → pakai **deploy key read-only** khusus repo ini (bukan key pribadi, bukan PAT). Frontend hanya membaca `agents/registry.json`, jadi submodule `core/` tidak perlu di-clone di VPS 1.

```bash
ssh-keygen -t ed25519 -f ~/.ssh/clau_agents_deploy -N "" -C "clau-vps1 deploy (read-only)"
cat ~/.ssh/clau_agents_deploy.pub
# GitHub → clau-ai-agents → Settings → Deploy keys → Add deploy key
#   Title: clau-vps1 ; Allow write access: JANGAN dicentang

printf "Host github-agents\n  HostName github.com\n  User git\n  IdentityFile ~/.ssh/clau_agents_deploy\n  IdentitiesOnly yes\n" >> ~/.ssh/config
chmod 600 ~/.ssh/config
ssh -T github-agents                          # "successfully authenticated"

sudo mkdir -p /srv/clau && sudo chown dea:dea /srv/clau
git clone git@github-agents:d34faiza-commits/clau-ai-agents.git /srv/clau/clau-ai-agents
cd /srv/clau/clau-ai-agents/frontend
npm ci && npm run build
```

Service systemd (`/etc/systemd/system/clau-frontend.service`):

```ini
[Unit]
Description=CLAU AI frontend (Next.js)
After=network.target

[Service]
User=dea
WorkingDirectory=/srv/clau/clau-ai-agents/frontend
Environment=NODE_ENV=production
ExecStart=/usr/bin/node node_modules/next/dist/bin/next start -H 127.0.0.1 -p 3000
Restart=on-failure
NoNewPrivileges=true
ProtectSystem=full
PrivateTmp=true

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload && sudo systemctl enable --now clau-frontend
curl -sI http://127.0.0.1:3000 | head -1      # HTTP/1.1 200 OK
```

Nginx (`/etc/nginx/sites-available/clau`), `server_name _` sampai domain ditentukan. Versi yang dikeraskan (rate limit, GET/HEAD saja, batas body & timeout) ada di `scripts/deploy/nginx/clau.conf` — pasang lewat [§ 7](#7-bagian-12--pengerasan-keamanan-2026-10-09):

```nginx
server {
    listen 80 default_server;
    listen [::]:80 default_server;
    server_name _;
    server_tokens off;

    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

```bash
sudo rm /etc/nginx/sites-enabled/default
sudo ln -s /etc/nginx/sites-available/clau /etc/nginx/sites-enabled/clau
sudo nginx -t && sudo systemctl reload nginx
# browser: http://<IP_VPS_1> → halaman registry agent
```

Update versi baru:

```bash
cd /srv/clau/clau-ai-agents && git pull
cd frontend && npm ci && npm run build && sudo systemctl restart clau-frontend
```

## 6. Bagian 9 — Auto-Deploy dari Repo

Setiap 5 menit VPS 1 mengecek branch `main`. Bila ada perubahan di `frontend/`, `agents/registry.json`, `agents/personas/`, atau `agents/evals/cases/` (jumlah kasus uji tampil di UI), server build rilis baru **di samping** rilis yang sedang jalan, lalu pindah ke rilis baru. Commit yang hanya mengubah dokumen tidak memicu build.

| Sifat | Keterangan |
|---|---|
| Pull-based | GitHub tidak punya akses ke server (tidak ada SSH key/secret server di GitHub). Server menarik kode dengan deploy key read-only |
| Build gagal | Rilis lama tetap jalan; commit itu tidak dicoba ulang tiap 5 menit sampai ada commit baru atau `--force` |
| Health check gagal | Otomatis rollback ke rilis sebelumnya |
| Riwayat | 3 rilis terakhir disimpan di `/srv/clau/releases/`; `/srv/clau/current` menunjuk rilis aktif |

Pasang (sekali):

```bash
cd /srv/clau/clau-ai-agents && git pull --ff-only

# izinkan dea me-restart service frontend saja, tanpa password
echo 'dea ALL=(root) NOPASSWD: /usr/bin/systemctl restart clau-frontend' | sudo tee /etc/sudoers.d/clau-deploy
sudo chmod 440 /etc/sudoers.d/clau-deploy && sudo visudo -c

# rilis pertama (membuat /srv/clau/current)
scripts/deploy/vps1-deploy.sh --force

# service frontend pindah ke rilis aktif
sudo sed -i 's#^WorkingDirectory=.*#WorkingDirectory=/srv/clau/current/frontend#' /etc/systemd/system/clau-frontend.service
sudo systemctl daemon-reload && sudo systemctl restart clau-frontend

# timer
sudo cp scripts/deploy/systemd/clau-deploy.service scripts/deploy/systemd/clau-deploy.timer /etc/systemd/system/
sudo systemctl daemon-reload && sudo systemctl enable --now clau-deploy.timer
```

Operasional:

```bash
systemctl list-timers clau-deploy.timer          # jadwal cek berikutnya
journalctl -u clau-deploy -n 30 --no-pager       # log deploy
/srv/clau/clau-ai-agents/scripts/deploy/vps1-deploy.sh --force   # deploy manual sekarang
ls -l /srv/clau/current                          # rilis aktif
```

Rollback manual ke rilis sebelumnya:

```bash
ls -1t /srv/clau/releases/                       # pilih folder rilis
ln -sfn /srv/clau/releases/<folder> /srv/clau/current && sudo systemctl restart clau-frontend
```

## 7. Bagian 12 — Pengerasan Keamanan (2026-10-09)

Ringkasan ancaman dan alasan tiap pengaturan: [`../security.md`](../security.md). Header keamanan (CSP, anti-clickjacking, dll.) sudah ikut auto-deploy. Dua langkah di bawah dipasang **sekali, manual**, satu perintah per baris.

**a. Nginx** (rate limit, GET/HEAD saja, body 16 KB, timeout pendek):

```bash
cd /srv/clau/clau-ai-agents && git pull --ff-only
sudo cp /etc/nginx/sites-available/clau /etc/nginx/sites-available/clau.bak
sudo cp scripts/deploy/nginx/clau.conf /etc/nginx/sites-available/clau
sudo nginx -t
sudo systemctl reload nginx
curl -sI http://127.0.0.1/ | head -1                      # HTTP/1.1 200 OK
curl -s -o /dev/null -w "%{http_code}\n" -X POST http://127.0.0.1/   # 405
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1/.env       # 404
```

Bila `nginx -t` gagal: `sudo cp /etc/nginx/sites-available/clau.bak /etc/nginx/sites-available/clau` lalu `sudo systemctl reload nginx`.

**b. Sandbox systemd untuk frontend** (sistem read-only, `/home` tidak terbaca, tanpa hak tambahan):

```bash
sudo cp /etc/systemd/system/clau-frontend.service /etc/systemd/system/clau-frontend.service.bak
sudo cp scripts/deploy/systemd/clau-frontend.service /etc/systemd/system/clau-frontend.service
sudo systemctl daemon-reload
sudo systemctl restart clau-frontend
systemctl is-active clau-frontend                          # active
curl -sI http://127.0.0.1:3000 | head -1                   # HTTP/1.1 200 OK
systemd-analyze security clau-frontend | tail -1           # skor exposure (makin kecil makin aman)
```

Bila tidak `active` atau curl gagal: `journalctl -u clau-frontend -n 30 --no-pager` (kirim ke agent), lalu kembalikan dengan `sudo cp /etc/systemd/system/clau-frontend.service.bak /etc/systemd/system/clau-frontend.service`, `sudo systemctl daemon-reload`, `sudo systemctl restart clau-frontend`.

**c. GitHub** (owner): Settings → Branches → proteksi `main` (wajib PR, CI hijau termasuk job `audit`). Settings → Code security → aktifkan Dependabot alerts & security updates.

## 8. RISK

- Selama belum ada domain + SSL, akses masih **HTTP via IP**. Aman untuk scaffold saat ini (tidak ada login/data), tetapi **jangan** menambahkan login, form, atau data client sebelum Bagian 9 (HTTPS) selesai.
- Service masih berjalan sebagai user `dea`. Pindahkan ke user service khusus (non-login) sebelum produksi dengan data client.
- Push ke `main` tampil di VPS 1 dalam ±5 menit. `main` harus lewat CI hijau (build frontend sudah dicek di CI) dan sebaiknya diproteksi (PR + review) agar perubahan tidak langsung live tanpa dicek.
