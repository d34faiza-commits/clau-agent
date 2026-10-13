#!/usr/bin/env bash
# Cek kesehatan & keamanan VPS 1 dalam satu perintah (docs/deploy/vps-1-setup.md § 8).
# Dipasang sebagai /usr/local/sbin/clau-vps1-check oleh vps1-harden.sh. Jalankan: sudo clau-vps1-check
# Hasil: daftar OK / PERLU DICEK / GAGAL yang bisa di-screenshot. Exit 1 bila ada GAGAL.
# Hanya membaca; tidak mengubah apa pun.
set -uo pipefail

REPO=/srv/clau/clau-ai-agents
fail=0 warn=0
ok()   { printf '  \033[32mOK\033[0m          %s\n' "$*"; }
cek()  { printf '  \033[33mPERLU DICEK\033[0m %s\n' "$*"; warn=$((warn + 1)); }
gagal(){ printf '  \033[31mGAGAL\033[0m       %s\n' "$*"; fail=$((fail + 1)); }
judul(){ printf '\n%s\n' "$*"; }

[ "$(id -u)" -eq 0 ] || { echo "Jalankan dengan sudo: sudo clau-vps1-check"; exit 2; }

judul "Layanan"
for u in clau-frontend nginx fail2ban ssh tailscaled; do
  systemctl is-active --quiet "$u" && ok "$u aktif" || gagal "$u tidak aktif (journalctl -u $u -n 30)"
done
for t in clau-deploy.timer clau-config-backup.timer apt-daily-upgrade.timer; do
  systemctl is-active --quiet "$t" && ok "$t terjadwal" || gagal "$t tidak aktif"
done

judul "Aplikasi"
pid=$(systemctl show -p MainPID --value clau-frontend 2>/dev/null)
web_user=$( [ -n "$pid" ] && [ "$pid" != 0 ] && ps -o user= -p "$pid" | tr -d ' ')
[ "$web_user" = clau-web ] && ok "frontend jalan sebagai clau-web" || gagal "frontend jalan sebagai '${web_user:--}', seharusnya clau-web (jalankan vps1-harden.sh)"
code=$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1/)
[ "$code" = 200 ] && ok "halaman utama lewat Nginx: 200" || gagal "halaman utama lewat Nginx: $code"
code=$(curl -s -o /dev/null -w '%{http_code}' -X POST http://127.0.0.1/)
[ "$code" = 405 ] && ok "POST ditolak Nginx (405)" || gagal "POST ke Nginx: $code (seharusnya 405)"
code=$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1/.env)
[ "$code" = 404 ] && ok "/.env tidak bisa dibuka (404)" || gagal "/.env: $code (seharusnya 404)"
headers=$(curl -sI http://127.0.0.1/)
grep -qi '^content-security-policy:' <<<"$headers" && ok "header keamanan (CSP) terkirim" || gagal "header CSP tidak ada"
grep -qi '^x-powered-by:' <<<"$headers" && gagal "header X-Powered-By masih terkirim" || ok "versi server tidak dibocorkan"

judul "Deploy"
live=$(cat /srv/clau/current/.sha 2>/dev/null || echo "")
remote=$(runuser -u clau-deploy -- env HOME=/var/lib/clau-deploy git -C "$REPO" ls-remote origin refs/heads/main 2>/dev/null | cut -c1-40)
if [ -z "$remote" ]; then gagal "tidak bisa membaca GitHub dengan deploy key (user clau-deploy)"
elif [ "$live" = "$remote" ]; then ok "rilis aktif = main terbaru (${live:0:7})"
else cek "rilis aktif ${live:0:7}, main ${remote:0:7} (normal bila push < 5 menit lalu)"; fi
if [ -f /srv/clau/.failed-sha ]; then gagal "deploy terakhir gagal untuk $(cut -c1-7 /srv/clau/.failed-sha) (journalctl -u clau-deploy -n 50)"; else ok "tidak ada deploy gagal"; fi
owner=$(stat -c %U:%G /srv/clau/current/ 2>/dev/null)
[ "$owner" = clau-deploy:clau-web ] && ok "file rilis milik clau-deploy, hanya dibaca clau-web" || gagal "pemilik file rilis: ${owner:--}"
for f in "nginx/clau.conf:/etc/nginx/sites-available/clau" \
         "systemd/clau-frontend.service:/etc/systemd/system/clau-frontend.service" \
         "systemd/clau-deploy.service:/etc/systemd/system/clau-deploy.service" \
         "systemd/clau-deploy.timer:/etc/systemd/system/clau-deploy.timer" \
         "systemd/clau-config-backup.service:/etc/systemd/system/clau-config-backup.service" \
         "systemd/clau-config-backup.timer:/etc/systemd/system/clau-config-backup.timer" \
         "vps1-check.sh:/usr/local/sbin/clau-vps1-check" \
         "vps1-backup-config.sh:/usr/local/sbin/clau-backup-config"; do
  src="$REPO/scripts/deploy/${f%%:*}" dst="${f#*:}"
  if cmp -s "$src" "$dst"; then ok "$(basename "$dst") sama dengan repo"
  else cek "$(basename "$dst") beda dengan repo (versi baru? jalankan ulang vps1-harden.sh)"; fi
done

judul "Keamanan server"
ufw status 2>/dev/null | grep -q '^Status: active' && ok "firewall UFW aktif" || gagal "firewall UFW tidak aktif"
extra=$(ufw status 2>/dev/null | awk 'NR>4 && $2 ~ /ALLOW/ {print $1}' | grep -vE '^(22|80|443|OpenSSH|Nginx.*)(/tcp)?( \(v6\))?$' | sort -u | tr '\n' ' ')
[ -z "$extra" ] && ok "port terbuka hanya 22, 80, 443" || gagal "port lain terbuka: $extra"
sshd_cfg=$(sshd -T 2>/dev/null)
grep -q '^permitrootlogin no' <<<"$sshd_cfg" && ok "login root SSH mati" || gagal "login root SSH masih boleh"
grep -q '^passwordauthentication no' <<<"$sshd_cfg" && ok "login SSH pakai password mati" || gagal "login SSH pakai password masih boleh"
fail2ban-client status sshd >/dev/null 2>&1 && ok "fail2ban menjaga SSH" || gagal "jail fail2ban sshd tidak aktif"
grep -q '^clau-deploy ALL=(root) NOPASSWD: /usr/bin/systemctl restart clau-frontend$' /etc/sudoers.d/clau-deploy 2>/dev/null \
  && ok "sudo clau-deploy hanya untuk restart frontend" || gagal "aturan /etc/sudoers.d/clau-deploy tidak sesuai"
score=$(systemd-analyze security clau-frontend 2>/dev/null | grep 'Overall exposure level' | grep -oE '[0-9]+\.[0-9]+' | head -1)
if [ -n "$score" ] && awk "BEGIN{exit !($score <= 2.0)}"; then ok "sandbox frontend: exposure $score"; else cek "sandbox frontend: exposure ${score:--} (target <= 2.0)"; fi

judul "Pembaruan & sumber daya"
sec=$(apt-get -s upgrade 2>/dev/null | grep -c '^Inst .*security' || true)
[ "$sec" = 0 ] && ok "tidak ada update keamanan tertunda" || cek "$sec update keamanan tertunda (dipasang otomatis tiap hari)"
[ -f /var/run/reboot-required ] && cek "perlu reboot untuk kernel baru (otomatis 03:30 WITA)" || ok "tidak perlu reboot"
disk=$(df --output=pcent / | tail -1 | tr -dc 0-9)
[ "$disk" -lt 80 ] && ok "disk terpakai ${disk}%" || gagal "disk terpakai ${disk}% (>= 80%)"
mem=$(awk '/MemAvailable/ {print int($2/1024)}' /proc/meminfo)
[ "$mem" -ge 300 ] && ok "RAM tersedia ${mem} MB" || cek "RAM tersedia hanya ${mem} MB"
swapon --show=NAME --noheadings | grep -q . && ok "swap aktif" || cek "swap tidak aktif"
last=$(ls -1t /var/backups/clau/vps1-config-*.tar.gz 2>/dev/null | head -1)
if [ -n "$last" ] && [ -z "$(find "$last" -mtime +8)" ]; then ok "backup config terakhir: $(basename "$last")"; else gagal "backup config > 8 hari / belum ada (sudo systemctl start clau-config-backup)"; fi

judul "Tailscale"
if command -v tailscale >/dev/null && tailscale status --json >/tmp/.ts.json 2>/dev/null; then
  python3 - /tmp/.ts.json <<'PY'
import json, sys
s = json.load(open(sys.argv[1]))["Self"]
ok = lambda m: print(f"  \033[32mOK\033[0m          {m}")
cek = lambda m: print(f"  \033[33mPERLU DICEK\033[0m {m}")
ok(f"terhubung sebagai {s.get('HostName')}") if s.get("Online") else cek("tidak online")
exp = s.get("KeyExpiry")
cek(f"key expiry aktif ({exp[:10]}): matikan di admin console") if exp else ok("key expiry dimatikan")
PY
  rm -f /tmp/.ts.json
else
  gagal "tailscale tidak terpasang / tidak login"
fi

printf '\nRingkasan: %d gagal, %d perlu dicek.\n' "$fail" "$warn"
[ "$fail" -eq 0 ]
