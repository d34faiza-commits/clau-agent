# VPS 1 — Setup Dashboard (Frontend)

> Panduan dan catatan status setup VPS 1 (`clau-vps1`), server untuk frontend Next.js. Keputusan dasar ada di [`../post-vps-checklist.md`](../post-vps-checklist.md). IP server **tidak** ditulis di repo; gunakan `<IP_VPS_1>`.

## 1. Status (2026-10-07)

| Bagian | Status |
|---|---|
| 1–5. OS, hostname, user admin `dea` + SSH key | DATA FINAL — Ubuntu 24.04 LTS, kernel 6.8.0-146, 2 vCPU / 3.8 GB RAM / 79 GB |
| 6. Hardening (UFW, sshd, fail2ban, unattended-upgrades) | DATA FINAL — diverifikasi: UFW active (22/80/443), root & password login ditolak, fail2ban jail `sshd` active |
| 7a–7b. Node 22 + Nginx + swap 2 GB | DATA FINAL — 2026-10-07 |
| 7c. Tailscale | DATA FINAL — 2026-10-07: `clau-vps1` join tailnet milik Dea Karisna. NEXT ACTION: disable key expiry, undang Pak Indra sebagai Admin, ACL setelah VPS 2 join |
| 8. Deploy frontend (akses via IP, HTTP) | DATA FINAL — 2026-10-07: service `clau-frontend` active, Nginx proxy ke 127.0.0.1:3000, halaman registry tampil di `http://<IP_VPS_1>` |
| 9. Domain + Cloudflare + SSL | Ditunda — domain belum ditentukan |
| 10. Backup config (tanpa `.env`) | Ditunda — setelah domain & Tailscale |

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

Nginx (`/etc/nginx/sites-available/clau`), `server_name _` sampai domain ditentukan:

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

## 6. RISK

- Selama belum ada domain + SSL, akses masih **HTTP via IP**. Aman untuk scaffold saat ini (tidak ada login/data), tetapi **jangan** menambahkan login, form, atau data client sebelum Bagian 9 (HTTPS) selesai.
- Service masih berjalan sebagai user `dea`. Pindahkan ke user service khusus (non-login) sebelum produksi dengan data client.
