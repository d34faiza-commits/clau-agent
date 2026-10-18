#!/usr/bin/env bash
# Pengerasan VPS 1 tahap 2 (docs/deploy/vps-1-setup.md § 8) untuk VPS 1 yang dipasang manual (§ 3–6).
# VPS baru/pengganti: pakai vps1-setup.sh (§ 0), yang memasang semuanya termasuk isi script ini.
# Jalankan sekali, lalu setiap kali file di
# scripts/deploy/ berubah (aman diulang):
#   sudo bash /srv/clau/clau-ai-agents/scripts/deploy/vps1-harden.sh
#
# Yang dilakukan:
#   1. User khusus tanpa login: clau-web (menjalankan frontend, hanya membaca) dan clau-deploy (pemilik
#      /srv/clau + deploy key read-only, hanya boleh `systemctl restart clau-frontend`). User admin (dea)
#      tidak lagi menjalankan aplikasi.
#   2. Deploy key dipindah (disalin) ke /var/lib/clau-deploy/.ssh; key lama di ~dea dihapus setelah berhasil.
#   3. Pasang unit systemd dari repo, alat cek (clau-vps1-check) & backup config mingguan (clau-backup-config).
#   4. Update keamanan yang butuh reboot dipasang otomatis 03:30 WITA; log journald dibatasi 300 MB.
# Bila langkah 1–3 gagal, semuanya dikembalikan ke keadaan sebelum script jalan (frontend tetap hidup).
set -euo pipefail

ROOT=/srv/clau
REPO="$ROOT/clau-ai-agents"
DEPLOY_HOME=/var/lib/clau-deploy
ADMIN="${SUDO_USER:-dea}"   # user admin yang menjalankan sudo (pemilik deploy key lama)
ADMIN_HOME=$(getent passwd "$ADMIN" | cut -d: -f6)
SRC="$REPO/scripts/deploy"
stamp=$(date -u +%Y%m%dT%H%M%SZ)
BACKUP="/var/backups/clau/pre-harden-$stamp"

log()  { printf '\n\033[1m== %s\033[0m\n' "$*"; }
die()  { printf '\033[31mGAGAL: %s\033[0m\n' "$*" >&2; exit 1; }

[ "$(id -u)" -eq 0 ] || die "jalankan dengan sudo"
[ -d "$REPO/.git" ] || die "$REPO tidak ada"
[ -L "$ROOT/current" ] || die "$ROOT/current belum ada (selesaikan Bagian 9 dulu)"
healthy() { for _ in $(seq 1 30); do curl -fs -o /dev/null http://127.0.0.1:3000 && return 0; sleep 1; done; return 1; }
healthy || die "frontend belum sehat sebelum mulai; perbaiki dulu (journalctl -u clau-frontend -n 30)"

log "1/7 Simpan keadaan sekarang ke $BACKUP"
mkdir -p "$BACKUP" && chmod 700 "$BACKUP"
for f in /etc/systemd/system/clau-frontend.service /etc/systemd/system/clau-deploy.service \
         /etc/systemd/system/clau-deploy.timer /etc/sudoers.d/clau-deploy; do
  [ -e "$f" ] && cp -a "$f" "$BACKUP/"
done
old_owner=$(stat -c %U:%G "$ROOT")

armed=0
rollback() {
  local status=$?
  [ "$armed" = 1 ] && [ "$status" != 0 ] || return 0
  set +e
  printf '\n\033[31m== Ada yang gagal: mengembalikan keadaan sebelumnya\033[0m\n'
  for f in clau-frontend.service clau-deploy.service clau-deploy.timer; do
    [ -e "$BACKUP/$f" ] && cp -a "$BACKUP/$f" /etc/systemd/system/
  done
  [ -e "$BACKUP/clau-deploy" ] && cp -a "$BACKUP/clau-deploy" /etc/sudoers.d/
  chown -R "$old_owner" "$ROOT"
  systemctl daemon-reload
  systemctl restart clau-frontend
  healthy && echo "Frontend kembali normal sebagai $old_owner. Kirim output di atas ke agent." \
          || echo "Frontend BELUM sehat: journalctl -u clau-frontend -n 30 --no-pager"
}
# Gagal di langkah mana pun (perintah error atau `die`) selama armed=1 → kembalikan semuanya.
trap rollback EXIT
armed=1

log "2/7 User clau-deploy & clau-web (tanpa login, tanpa password)"
getent group clau-web >/dev/null || groupadd --system clau-web
id clau-web >/dev/null 2>&1 || useradd --system --gid clau-web --no-create-home --home-dir /nonexistent --shell /usr/sbin/nologin clau-web
id clau-deploy >/dev/null 2>&1 || useradd --system --user-group --create-home --home-dir "$DEPLOY_HOME" --shell /usr/sbin/nologin clau-deploy
chmod 700 "$DEPLOY_HOME"
id clau-web; id clau-deploy

log "3/7 Deploy key read-only untuk clau-deploy"
install -d -m 700 -o clau-deploy -g clau-deploy "$DEPLOY_HOME/.ssh"
key="$DEPLOY_HOME/.ssh/clau_agents_deploy"
if [ ! -f "$key" ]; then
  [ -f "$ADMIN_HOME/.ssh/clau_agents_deploy" ] || die "deploy key tidak ditemukan di $ADMIN_HOME/.ssh/clau_agents_deploy"
  install -m 600 -o clau-deploy -g clau-deploy "$ADMIN_HOME/.ssh/clau_agents_deploy" "$key"
  install -m 644 -o clau-deploy -g clau-deploy "$ADMIN_HOME/.ssh/clau_agents_deploy.pub" "$key.pub"
fi
printf 'Host github-agents\n  HostName github.com\n  User git\n  IdentityFile %s\n  IdentitiesOnly yes\n  StrictHostKeyChecking yes\n' "$key" > "$DEPLOY_HOME/.ssh/config"
# Host key GitHub dari known_hosts admin (sudah diverifikasi saat `ssh -T github-agents`), cadangan: key resmi
# GitHub (https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/githubs-ssh-key-fingerprints).
known=$(ssh-keygen -F github.com -f "$ADMIN_HOME/.ssh/known_hosts" 2>/dev/null | grep -v '^#' || true)
[ -n "$known" ] || known="github.com ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIOMqqnkVzrm0SdG6UOoqKLsabgH5C9okWi0dh2l9GKJl"
printf '%s\n' "$known" > "$DEPLOY_HOME/.ssh/known_hosts"
chown clau-deploy:clau-deploy "$DEPLOY_HOME/.ssh/config" "$DEPLOY_HOME/.ssh/known_hosts"
chmod 600 "$DEPLOY_HOME/.ssh/config" "$DEPLOY_HOME/.ssh/known_hosts"

log "4/7 /srv/clau milik clau-deploy, hanya bisa dibaca clau-web"
chown -R clau-deploy:clau-web "$ROOT"
chmod -R u+rwX,g+rX,g-w,o-rwx "$ROOT"
find "$ROOT" -type d -exec chmod g+s {} +
as_deploy() { runuser -u clau-deploy -- env HOME="$DEPLOY_HOME" "$@"; }
as_deploy git -C "$REPO" fetch --quiet origin main
echo "clau-deploy bisa membaca GitHub dengan deploy key"
as_deploy git -C "$REPO" ls-remote --exit-code origin refs/heads/release/vps1 >/dev/null \
  || die "branch release/vps1 belum ada: tunggu job CI 'release-vps1' di main hijau (±5 menit setelah merge), lalu ulangi"

log "5/7 sudo terbatas, unit systemd, alat cek & backup"
tmp=$(mktemp)
echo 'clau-deploy ALL=(root) NOPASSWD: /usr/bin/systemctl restart clau-frontend' > "$tmp"
visudo -cf "$tmp" >/dev/null
install -m 440 -o root -g root "$tmp" /etc/sudoers.d/clau-deploy
rm -f "$tmp"
for u in clau-frontend.service clau-deploy.service clau-deploy.timer clau-config-backup.service clau-config-backup.timer; do
  install -m 644 -o root -g root "$SRC/systemd/$u" "/etc/systemd/system/$u"
done
# Salinan milik root: script yang dijalankan root tidak boleh bisa diubah user clau-deploy.
install -m 755 -o root -g root "$SRC/vps1-check.sh" /usr/local/sbin/clau-vps1-check
install -m 755 -o root -g root "$SRC/vps1-backup-config.sh" /usr/local/sbin/clau-backup-config
systemctl daemon-reload
systemctl restart clau-frontend
healthy || die "frontend tidak sehat setelah pindah ke clau-web"
pid=$(systemctl show -p MainPID --value clau-frontend)
[ "$(ps -o user= -p "$pid" | tr -d ' ')" = clau-web ] || die "frontend tidak jalan sebagai clau-web"
echo "frontend sehat sebagai clau-web"
systemctl start clau-deploy.service || die "deploy sebagai clau-deploy gagal (journalctl -u clau-deploy -n 50)"
echo "deploy berjalan sebagai clau-deploy"
systemctl enable --now clau-deploy.timer clau-config-backup.timer >/dev/null
armed=0

log "6/7 Update keamanan otomatis + reboot 03:30 WITA bila perlu, batas log"
# Jam lokal server yang sama dengan 03:30 WITA (server biasanya UTC → 19:30).
reboot_at=$(date -d 'TZ="Asia/Makassar" 03:30' +%H:%M)
cat > /etc/apt/apt.conf.d/52clau-auto-reboot <<EOF
// Dipasang vps1-harden.sh: kernel/libc baru aktif tanpa menunggu reboot manual (pratinjau mati ±1 menit).
Unattended-Upgrade::Automatic-Reboot "true";
Unattended-Upgrade::Automatic-Reboot-Time "$reboot_at";
EOF
mkdir -p /etc/systemd/journald.conf.d
printf '[Journal]\nSystemMaxUse=300M\n' > /etc/systemd/journald.conf.d/clau.conf
systemctl restart systemd-journald

log "7/7 Backup config pertama & bersihkan key lama"
/usr/local/sbin/clau-backup-config
if [ -f "$ADMIN_HOME/.ssh/clau_agents_deploy" ] && cmp -s "$ADMIN_HOME/.ssh/clau_agents_deploy" "$key"; then
  rm -f "$ADMIN_HOME/.ssh/clau_agents_deploy" "$ADMIN_HOME/.ssh/clau_agents_deploy.pub"
  echo "deploy key di $ADMIN_HOME/.ssh dihapus (sekarang hanya milik clau-deploy)"
fi

printf '\n\033[32mSelesai.\033[0m Keadaan lama tersimpan di %s. Hasil cek:\n' "$BACKUP"
/usr/local/sbin/clau-vps1-check || true
