#!/usr/bin/env bash
# Backup config VPS 1 (keputusan VPS #6: config saja, TANPA .env, private key, atau data).
# Dipasang sebagai /usr/local/sbin/clau-backup-config oleh vps1-harden.sh; jalan mingguan lewat
# clau-config-backup.timer (root). Hasil: /var/backups/clau/vps1-config-<UTC>.tar.gz (chmod 600), 8 terakhir.
# Isi utama juga ada di repo (scripts/deploy/); backup ini menangkap keadaan server yang sebenarnya.
set -euo pipefail
umask 077

OUT=/var/backups/clau
KEEP=8
stamp=$(date -u +%Y%m%dT%H%M%SZ)
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT

# File config yang ada saja; yang tidak ada dilewati. Private key dan .env tidak pernah masuk.
paths=(
  /etc/nginx/sites-available/clau
  /etc/systemd/system/clau-frontend.service
  /etc/systemd/system/clau-deploy.service
  /etc/systemd/system/clau-deploy.timer
  /etc/systemd/system/clau-config-backup.service
  /etc/systemd/system/clau-config-backup.timer
  /etc/sudoers.d/clau-deploy
  /etc/ssh/sshd_config.d/00-clau.conf
  /etc/fail2ban/jail.local
  /etc/ufw/user.rules
  /etc/ufw/user6.rules
  /etc/apt/apt.conf.d/20auto-upgrades
  /etc/apt/apt.conf.d/52clau-auto-reboot
  /etc/systemd/journald.conf.d/clau.conf
  /etc/fstab
  /var/lib/clau-deploy/.ssh/config
  /var/lib/clau-deploy/.ssh/known_hosts
)
existing=()
for p in "${paths[@]}"; do [ -e "$p" ] && existing+=("$p"); done

# Keadaan yang tidak berbentuk file: versi paket, rilis aktif, Tailscale, firewall.
{
  echo "host: $(hostname)  dibuat: $stamp"
  echo "rilis aktif: $(cat /srv/clau/current/.sha 2>/dev/null || echo '-')"
  echo "node: $(node -v 2>/dev/null || echo '-')  nginx: $(nginx -v 2>&1 | sed 's/.*\///')"
  echo; echo "== ufw"; ufw status verbose 2>/dev/null || true
  echo; echo "== tailscale"; tailscale status 2>/dev/null | head -20 || true
} > "$work/state.txt"
dpkg-query -W -f='${Package}\t${Version}\n' > "$work/packages.tsv" 2>/dev/null || true

mkdir -p "$OUT"
chmod 700 "$OUT"
file="$OUT/vps1-config-$stamp.tar.gz"
tar -czf "$file" -C / "${existing[@]#/}" -C "$work" state.txt packages.tsv 2>/dev/null
chmod 600 "$file"
echo "[clau-backup] $file ($(du -h "$file" | cut -f1), ${#existing[@]} file config)"

ls -1t "$OUT"/vps1-config-*.tar.gz | tail -n +$((KEEP + 1)) | xargs -r rm -f
