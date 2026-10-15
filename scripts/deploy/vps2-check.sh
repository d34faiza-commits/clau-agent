#!/usr/bin/env bash
# Cek kesehatan & keamanan VPS 2 dalam satu perintah (docs/deploy/vps-2-setup.md).
# Dipasang sebagai /usr/local/sbin/clau-vps2-check oleh vps2-setup.sh. Jalankan: sudo clau-vps2-check
# Hasil: daftar OK / PERLU DICEK / GAGAL yang bisa di-screenshot. Exit 1 bila ada GAGAL.
# Hanya membaca; tidak mengubah apa pun. Tidak pernah menampilkan isi secret.
set -uo pipefail

ROOT=/srv/clau
REPO="$ROOT/clau-ai-agents"
ETC=/etc/clau
fail=0 warn=0
ok()   { printf '  \033[32mOK\033[0m          %s\n' "$*"; }
cek()  { printf '  \033[33mPERLU DICEK\033[0m %s\n' "$*"; warn=$((warn + 1)); }
gagal(){ printf '  \033[31mGAGAL\033[0m       %s\n' "$*"; fail=$((fail + 1)); }
judul(){ printf '\n%s\n' "$*"; }
# Alamat:port dari `ss -Htln` yang bisa dijangkau dari IP publik. Akhiran zona (%tailscale0, %lo) dibuang dulu;
# loopback, Tailscale (100.x, fd7a:115c:a1e0::), SSH, dan UDP Tailscale bukan port aplikasi publik.
public_listeners() {
  awk '{print $4}' | sed -E 's/%[^]:]*//' \
    | grep -vE '^(127\.[0-9.]+|\[::1\]|100\.[0-9.]+|\[fd7a:115c:a1e0:[0-9a-f:]*\]):' | grep -vE ':(22|41641)$' || true
}

[ "$(id -u)" -eq 0 ] || { echo "Jalankan dengan sudo: sudo clau-vps2-check"; exit 2; }

judul "Layanan"
for u in docker fail2ban ssh tailscaled; do
  systemctl is-active --quiet "$u" && ok "$u aktif" || gagal "$u tidak aktif (journalctl -u $u -n 30)"
done
for t in clau2-deploy.timer clau2-backup.timer apt-daily-upgrade.timer; do
  systemctl is-active --quiet "$t" && ok "$t terjadwal" || gagal "$t tidak aktif"
done

judul "Aplikasi (docker compose)"
for s in db backend frontend; do
  state=$(cd "$REPO" && docker compose ps --format '{{.Service}} {{.Health}}' 2>/dev/null | awk -v s="$s" '$1 == s {print $2}')
  [ "$state" = healthy ] && ok "$s sehat" || gagal "$s: '${state:-tidak jalan}' (cd $REPO && sudo docker compose logs --tail 50 $s)"
done
migrate=$(cd "$REPO" && docker compose ps -a --format '{{.Service}} {{.ExitCode}}' 2>/dev/null | awk '$1 == "migrate" {print $2}')
[ "$migrate" = 0 ] && ok "migrasi database selesai" || gagal "migrasi: exit '${migrate:--}' (sudo docker compose logs migrate)"
health=$(curl -fs http://127.0.0.1:8000/health 2>/dev/null)
grep -q '"status":"ok"' <<<"$health" && ok "backend /health: $(grep -o '"version":"[^"]*"' <<<"$health")" || gagal "backend /health tidak menjawab"
code=$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:3000/login)
[ "$code" = 200 ] && ok "halaman login: 200" || gagal "halaman login: $code"
code=$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:3000/requests)
[ "$code" = 307 ] && ok "halaman kerja wajib login (307)" || gagal "/requests tanpa login: $code (seharusnya 307)"
code=$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/docs)
[ "$code" = 404 ] && ok "dokumentasi API tertutup (404)" || gagal "/docs: $code (seharusnya 404, CLAU_ENV=production)"
for c in $(cd "$REPO" && docker compose ps -q backend frontend 2>/dev/null); do
  uid=$(docker exec "$c" id -u 2>/dev/null)
  [ -n "$uid" ] && [ "$uid" != 0 ] && ok "container $(docker inspect -f '{{.Name}}' "$c" | tr -d /) bukan root" || gagal "container $c jalan sebagai root"
done

judul "Akses (hanya lewat Tailscale)"
dns=$(tailscale status --json 2>/dev/null | python3 -c 'import json,sys; print(json.load(sys.stdin)["Self"]["DNSName"].rstrip("."))' 2>/dev/null)
serve=$(tailscale serve status 2>/dev/null)
grep -q "https://$dns" <<<"$serve" && grep -q '127.0.0.1:3000' <<<"$serve" && ok "HTTPS Tailscale: https://$dns → frontend" || gagal "tailscale serve belum aktif (jalankan ulang vps2-setup.sh)"
tailscale funnel status 2>/dev/null | grep -qi 'funnel on' && gagal "Tailscale Funnel aktif: aplikasi terbuka ke internet (tailscale funnel reset)" || ok "Funnel mati (tidak terbuka ke internet)"
origins=$(grep -m1 '^CLAU_ALLOWED_ORIGINS=' "$REPO/.env" 2>/dev/null | cut -d= -f2-)
[ "$origins" = "https://$dns" ] && ok "origin login = https://$dns" || gagal "CLAU_ALLOWED_ORIGINS='$origins', seharusnya https://$dns"
if listening=$(ss -Htln 2>/dev/null); then
  public=$(public_listeners <<<"$listening")
  [ -z "$public" ] && ok "tidak ada port aplikasi yang mendengar di IP publik" || gagal "port terbuka di IP publik: $(tr '\n' ' ' <<<"$public")"
else
  gagal "tidak bisa membaca port yang terbuka (ss)"
fi
ufw_status=$(ufw status 2>/dev/null)
grep -q '^Status: active' <<<"$ufw_status" && ok "UFW aktif" || gagal "UFW tidak aktif"
if [ -f "$ETC/ssh-locked" ]; then
  grep -qE '^(22/tcp|OpenSSH) .*ALLOW' <<<"$ufw_status" && gagal "SSH publik terbuka lagi padahal sudah dikunci" || ok "SSH hanya lewat Tailscale"
else
  cek "SSH masih terbuka di IP publik: setelah ssh lewat Tailscale berhasil, jalankan vps2-setup.sh --lock-ssh"
fi
sshd=$(sshd -T 2>/dev/null)
grep -q '^permitrootlogin no' <<<"$sshd" && ok "login root SSH mati" || gagal "login root SSH masih boleh"
grep -q '^passwordauthentication no' <<<"$sshd" && ok "login password SSH mati" || gagal "login password SSH masih boleh"
tailscale status --json 2>/dev/null | python3 -c 'import json,sys; s=json.load(sys.stdin)["Self"]; sys.exit(0 if s.get("KeyExpiry") in (None,"","0001-01-01T00:00:00Z") else 1)' 2>/dev/null \
  && ok "key expiry Tailscale mati" || cek "key expiry Tailscale masih aktif (matikan di admin Tailscale → Machines → clau-vps2)"

judul "Secret & backup"
perm=$(stat -c '%a %U' "$REPO/.env" 2>/dev/null)
[ "$perm" = "600 root" ] && ok ".env chmod 600 milik root" || gagal ".env: '${perm:-tidak ada}' (seharusnya 600 root)"
perm=$(stat -c '%a %U' "$ETC/deploy_key" 2>/dev/null)
[ "$perm" = "600 root" ] && ok "deploy key chmod 600 milik root" || gagal "deploy key: '${perm:-tidak ada}'"
latest=$(ls -1t "$REPO"/backups/clau-*.dump.enc 2>/dev/null | head -1)
if [ -z "$latest" ]; then gagal "belum ada backup database (sudo clau-vps2-backup)"
else
  age=$(( ($(date +%s) - $(stat -c %Y "$latest")) / 3600 ))
  [ "$age" -le 26 ] && ok "backup terakhir $age jam lalu ($(ls -1 "$REPO"/backups/clau-*.dump.enc | wc -l) file)" || gagal "backup terakhir $age jam lalu (lebih dari sehari)"
  [ -s "$latest.hmac" ] && ok "backup punya HMAC (cek keutuhan)" || gagal "backup tanpa .hmac"
fi
cek "salinan backup di luar server (Backblaze B2) belum ada: NEXT ACTION; simpan CLAU_BACKUP_PASSPHRASE di password manager"

judul "Deploy"
live=$(cat "$ROOT/.live-sha" 2>/dev/null)
release=$(GIT_SSH_COMMAND="ssh -i $ETC/deploy_key -o IdentitiesOnly=yes -o StrictHostKeyChecking=yes -o UserKnownHostsFile=$ETC/known_hosts" \
  git -C "$REPO" ls-remote origin refs/heads/release/vps1 2>/dev/null | cut -f1)
if [ -z "$release" ]; then gagal "tidak bisa membaca release/vps1 dengan deploy key"
elif [ "$live" = "$release" ]; then ok "rilis aktif = release/vps1 terbaru (${live:0:7})"
else cek "rilis aktif ${live:0:7}, release/vps1 ${release:0:7} (normal bila < 10 menit lalu)"; fi
[ -f "$ROOT/.failed-sha" ] && cek "commit $(cut -c1-7 "$ROOT/.failed-sha") gagal di-deploy (journalctl -u clau2-deploy -n 80)"

judul "Sumber daya"
disk=$(df --output=pcent / | tail -1 | tr -dc 0-9)
[ "$disk" -lt 80 ] && ok "disk terpakai $disk%" || gagal "disk terpakai $disk%"
avail=$(awk '/MemAvailable/ {print int($2/1024)}' /proc/meminfo)
[ "$avail" -ge 500 ] && ok "RAM tersedia ${avail} MB" || cek "RAM tersedia hanya ${avail} MB"
pending=$(apt-get -s upgrade 2>/dev/null | grep -c '^Inst .*security' || true)
[ "$pending" = 0 ] && ok "tidak ada update keamanan tertunda" || cek "$pending update keamanan tertunda (otomatis malam ini)"
[ -f /var/run/reboot-required ] && cek "perlu reboot (otomatis 03:30 WITA)" || ok "tidak perlu reboot"

printf '\nHasil: %d gagal, %d perlu dicek.\n' "$fail" "$warn"
[ "$fail" -eq 0 ]
