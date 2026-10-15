#!/usr/bin/env bash
# Setup VPS 2 (backend + database + frontend login), tanpa domain: hanya bisa dibuka lewat Tailscale dengan
# HTTPS (sertifikat *.ts.net). Panduan: docs/deploy/vps-2-setup.md. Jalankan sebagai admin (bukan root):
#   sudo bash /srv/clau/clau-ai-agents/scripts/deploy/vps2-setup.sh
# Aman diulang (setiap kali file di scripts/deploy/ berubah). Setelah SSH lewat Tailscale terbukti jalan:
#   sudo bash /srv/clau/clau-ai-agents/scripts/deploy/vps2-setup.sh --lock-ssh
#
# Yang dilakukan:
#   1. Pengerasan dasar: update, UFW (masuk hanya lewat Tailscale + SSH), SSH tanpa root/password, fail2ban,
#      update keamanan otomatis (+ reboot 03:30 WITA), batas log, swap.
#   2. Docker Engine + Compose dari repo resmi Docker (log dibatasi, live-restore).
#   3. .env dengan secret acak (chmod 600, root), origin = alamat HTTPS Tailscale server ini.
#   4. Stack docker compose dari commit release/vps1 (main yang CI-nya hijau), port hanya 127.0.0.1.
#   5. `tailscale serve`: https://<nama-server>.<tailnet>.ts.net → frontend (hanya anggota tailnet).
#   6. Timer: deploy otomatis 5 menit sekali, backup database terenkripsi tiap 6 jam (+ uji restore mingguan,
#      salinan ke Backblaze B2 setelah `sudo clau-vps2-offsite setup`).
#   7. Alat: sudo clau-vps2-check (cek), sudo clau-vps2-restore (pemulihan, selalu manual).
set -euo pipefail

ROOT=/srv/clau
REPO="$ROOT/clau-ai-agents"
SRC="$REPO/scripts/deploy"
ETC=/etc/clau
KEY="$ETC/deploy_key"
ADMIN="${SUDO_USER:-}"
LOCK_SSH=0
[ "${1:-}" = "--lock-ssh" ] && LOCK_SSH=1

log() { printf '\n\033[1m== %s\033[0m\n' "$*"; }
die() { printf '\033[31mGAGAL: %s\033[0m\n' "$*" >&2; exit 1; }

[ "$(id -u)" -eq 0 ] || die "jalankan dengan sudo"
[ -n "$ADMIN" ] && [ "$ADMIN" != root ] || die "jalankan dari user admin (mis. dea) dengan sudo, bukan login root"
. /etc/os-release
[ "$ID" = ubuntu ] && [ "$VERSION_ID" = "24.04" ] || die "butuh Ubuntu 24.04 (ini $PRETTY_NAME)"
[ -d "$REPO/.git" ] || die "$REPO belum ada (selesaikan Bagian C panduan)"
[ -f "$KEY" ] || die "deploy key $KEY belum ada (Bagian B panduan)"
command -v tailscale >/dev/null && tailscale status >/dev/null 2>&1 || die "Tailscale belum tersambung (tailscale up)"
admin_home=$(getent passwd "$ADMIN" | cut -d: -f6)
[ -s "$admin_home/.ssh/authorized_keys" ] || die "$ADMIN belum punya SSH key ($admin_home/.ssh/authorized_keys); SSH tanpa password akan mengunci akses"

if [ "$LOCK_SSH" = 1 ]; then
  log "SSH publik ditutup: hanya lewat Tailscale"
  # sudo biasanya membuang SSH_CONNECTION; cadangan: alamat asal sesi dari `who -m`.
  remote="${SSH_CONNECTION:-}"
  remote="${remote%% *}"
  [ -n "$remote" ] || remote=$(who -m 2>/dev/null | sed -n 's/.*(\([^)]*\)).*/\1/p')
  case "$remote" in
    100.*|fd7a:115c:a1e0:*) ;;
    "") echo "(alamat asal sesi tidak terbaca; pastikan kamu login lewat Tailscale)" ;;
    *) die "kamu sedang login lewat IP publik ($remote); login dulu lewat Tailscale (ssh $ADMIN@$(tailscale ip -4 | head -1)), lalu ulangi" ;;
  esac
  ufw delete allow OpenSSH >/dev/null 2>&1 || true
  ufw delete allow 22/tcp >/dev/null 2>&1 || true
  touch "$ETC/ssh-locked"  # setup berikutnya tidak membuka SSH publik lagi
  ufw status verbose
  echo "Bila Tailscale mati: masuk lewat konsol web provider (Lish/LISH), lalu: sudo ufw allow OpenSSH"
  exit 0
fi

log "1/8 Update sistem & paket dasar"
export DEBIAN_FRONTEND=noninteractive
apt-get update -q
apt-get -y -q full-upgrade
apt-get -y -q install ufw fail2ban unattended-upgrades ca-certificates curl git openssl python3 rclone >/dev/null
hostnamectl set-hostname clau-vps2 2>/dev/null || echo "(nama host tidak diubah; tidak masalah)"

log "2/8 Firewall, SSH, fail2ban"
ufw default deny incoming >/dev/null
ufw default allow outgoing >/dev/null
ufw allow in on tailscale0 >/dev/null
# SSH publik tetap dibuka sampai --lock-ssh (setelah SSH lewat Tailscale terbukti jalan).
[ -f "$ETC/ssh-locked" ] || ufw allow OpenSSH >/dev/null
# Tailscale butuh UDP 41641 untuk koneksi langsung (tanpa relay); bukan layanan, aman dibuka.
ufw allow 41641/udp >/dev/null
ufw --force enable >/dev/null
# 00- supaya menang dari 50-cloud-init.conf (sshd memakai nilai pertama yang ditemukan).
printf 'PermitRootLogin no\nPasswordAuthentication no\nKbdInteractiveAuthentication no\n' > /etc/ssh/sshd_config.d/00-clau.conf
mkdir -p /run/sshd
sshd -t
systemctl restart ssh
printf '[sshd]\nenabled = true\nbackend = systemd\nmaxretry = 5\nfindtime = 10m\nbantime = 1h\n' > /etc/fail2ban/jail.local
systemctl enable --now fail2ban >/dev/null
systemctl restart fail2ban

log "3/8 Update keamanan otomatis, batas log, swap"
printf 'APT::Periodic::Update-Package-Lists "1";\nAPT::Periodic::Unattended-Upgrade "1";\n' > /etc/apt/apt.conf.d/20auto-upgrades
reboot_at=$(date -d 'TZ="Asia/Makassar" 03:30' +%H:%M)
cat > /etc/apt/apt.conf.d/52clau-auto-reboot <<EOF
// Dipasang vps2-setup.sh: kernel/libc baru aktif tanpa menunggu reboot manual (layanan mati ±2 menit).
Unattended-Upgrade::Automatic-Reboot "true";
Unattended-Upgrade::Automatic-Reboot-Time "$reboot_at";
EOF
mkdir -p /etc/systemd/journald.conf.d
printf '[Journal]\nSystemMaxUse=300M\n' > /etc/systemd/journald.conf.d/clau.conf
systemctl restart systemd-journald
if ! swapon --show | grep -q .; then
  if fallocate -l 2G /swapfile && chmod 600 /swapfile && mkswap /swapfile >/dev/null && swapon /swapfile; then
    grep -q '^/swapfile ' /etc/fstab || echo '/swapfile none swap sw 0 0' >> /etc/fstab
  else
    swapoff /swapfile 2>/dev/null || true; rm -f /swapfile
    echo "(swap tidak bisa dibuat; lanjut tanpa swap)"
  fi
fi
swapon --show || true

log "4/8 Docker Engine + Compose (repo resmi Docker)"
if ! command -v docker >/dev/null; then
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
  chmod a+r /etc/apt/keyrings/docker.asc
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $VERSION_CODENAME stable" \
    > /etc/apt/sources.list.d/docker.list
  apt-get update -q
  apt-get -y -q install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin >/dev/null
fi
mkdir -p /etc/docker
cat > /etc/docker/daemon.json <<'EOF'
{
  "log-driver": "json-file",
  "log-opts": { "max-size": "10m", "max-file": "3" },
  "live-restore": true,
  "no-new-privileges": true
}
EOF
systemctl enable docker >/dev/null
systemctl restart docker
docker compose version

log "5/8 Repo di commit release/vps1 (hanya main yang CI-nya hijau)"
chown -R root:root "$ROOT" "$ETC"
chmod 700 "$ETC" && chmod 600 "$KEY"
chmod 755 "$ROOT"
# Host key resmi GitHub (https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/githubs-ssh-key-fingerprints).
[ -s "$ETC/known_hosts" ] || echo "github.com ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIOMqqnkVzrm0SdG6UOoqKLsabgH5C9okWi0dh2l9GKJl" > "$ETC/known_hosts"
export GIT_SSH_COMMAND="ssh -i $KEY -o IdentitiesOnly=yes -o StrictHostKeyChecking=yes -o UserKnownHostsFile=$ETC/known_hosts"
git config --global --add safe.directory "$REPO" 2>/dev/null || true
git -C "$REPO" fetch --quiet origin release/vps1 || die "tidak bisa membaca release/vps1 (deploy key sudah ditambahkan di GitHub?)"
git -C "$REPO" checkout --quiet --detach FETCH_HEAD
echo "commit: $(git -C "$REPO" rev-parse --short HEAD)"

log "6/8 .env (secret acak, chmod 600) + origin HTTPS Tailscale"
dns=$(tailscale status --json | python3 -c 'import json,sys; print(json.load(sys.stdin)["Self"]["DNSName"].rstrip("."))')
[ -n "$dns" ] || die "nama DNS Tailscale tidak ditemukan; aktifkan MagicDNS di admin Tailscale (DNS)"
(cd "$REPO" && bash scripts/init-env.sh)
set_env() {  # set_env NAMA NILAI: ganti baris (aktif atau komentar) atau tambahkan
  if grep -q "^#\? \?$1=" "$REPO/.env"; then sed -i "s|^#\? \?$1=.*|$1=$2|" "$REPO/.env"; else echo "$1=$2" >> "$REPO/.env"; fi
}
set_env CLAU_ENV production
set_env CLAU_ALLOWED_ORIGINS "https://$dns"
set_env CLAU_AUTH_ENABLED 1
set_env CLAU_PUBLIC_ORIGIN "https://$dns"
chown root:root "$REPO/.env" && chmod 600 "$REPO/.env"
echo "alamat: https://$dns"

log "7/8 Jalankan stack (build ±5–10 menit pertama kali)"
(cd "$REPO" && docker compose up -d --build --wait --wait-timeout 600)
git -C "$REPO" rev-parse HEAD > "$ROOT/.live-sha"
curl -fsS http://127.0.0.1:8000/health && echo
# Hanya anggota tailnet: HTTPS 443 di alamat ts.net → frontend. Bukan Funnel (tidak terbuka ke internet).
if ! tailscale serve --bg --https=443 http://127.0.0.1:3000; then
  die "tailscale serve gagal: aktifkan 'HTTPS Certificates' di admin Tailscale (DNS), lalu ulangi script ini"
fi
tailscale serve status

log "8/8 Deploy otomatis, backup tiap 6 jam, alat cek & pemulihan"
for u in clau2-deploy.service clau2-deploy.timer clau2-backup.service clau2-backup.timer; do
  install -m 644 -o root -g root "$SRC/systemd/$u" "/etc/systemd/system/$u"
done
# Salinan milik root di luar repo: yang dijalankan timer tidak berubah sebelum script ini diulang.
install -m 755 -o root -g root "$SRC/vps2-deploy.sh" /usr/local/sbin/clau-vps2-deploy
install -m 755 -o root -g root "$SRC/vps2-backup.sh" /usr/local/sbin/clau-vps2-backup
install -m 755 -o root -g root "$SRC/vps2-check.sh" /usr/local/sbin/clau-vps2-check
install -m 755 -o root -g root "$SRC/vps2-offsite.sh" /usr/local/sbin/clau-vps2-offsite
install -m 755 -o root -g root "$SRC/vps2-restore.sh" /usr/local/sbin/clau-vps2-restore
systemctl daemon-reload
systemctl enable --now clau2-deploy.timer clau2-backup.timer >/dev/null
/usr/local/sbin/clau-vps2-backup || echo "(backup pertama/salinan B2 belum berhasil: lihat pesan di atas, lalu sudo clau-vps2-check)"

printf '\n\033[32mSelesai.\033[0m Buka https://%s dari laptop/HP yang tersambung Tailscale.\n' "$dns"
printf 'Owner pertama (sekali): cd %s && sudo docker compose run --rm backend python -m app.auth.cli create-owner --email <email> --name "<nama>"\n' "$REPO"
/usr/local/sbin/clau-vps2-check || true
