#!/usr/bin/env bash
# Pulihkan database VPS 2 dari backup: tombol darurat, SELALU dijalankan manusia (docs/deploy/vps-2-setup.md § 5).
# Dipasang sebagai /usr/local/sbin/clau-vps2-restore oleh vps2-setup.sh.
#
#   sudo clau-vps2-restore           # pilih backup (server + B2), uji, konfirmasi PULIHKAN, pulihkan, cek sehat
#   sudo clau-vps2-restore --list    # hanya tampilkan daftar backup (40 terbaru)
#   sudo clau-vps2-restore --semua   # tampilkan & boleh pilih semua backup (mis. B2 yang lebih dari seminggu)
#   sudo clau-vps2-restore --server-pengganti
#                                    # server baru menggantikan VPS 2 yang hilang: passphrase backup & CLAU_SECRET_KEY
#                                    # lama (password manager) dipakai lagi, supaya backup lama terbuka dan 2FA semua
#                                    # user tetap jalan (data 2FA terenkripsi dengan CLAU_SECRET_KEY)
#
# Pengaman: backup diuji dulu di database sementara; isi sekarang dibandingkan lalu harus dikonfirmasi dengan
# mengetik PULIHKAN; isi sekarang di-backup dulu (…-sebelum-restore); database ditukar hanya setelah restore lengkap;
# backend tidak sehat → isi sebelumnya kembali otomatis (scripts/db-restore.sh --yes). Deploy & backup otomatis
# dijeda selama restore. Tidak ada pemulihan otomatis: mesin tidak memutuskan data mana yang benar.
set -euo pipefail
umask 077  # file sementara (.env.baru, log) berisi secret: jangan pernah terbaca user lain, sekejap pun

REPO="${CLAU_REPO:-/srv/clau/clau-ai-agents}"
ROOT="$(dirname "$REPO")"
OFFSITE="${CLAU_OFFSITE_BIN:-/usr/local/sbin/clau-vps2-offsite}"
OFFSITE_ENV="${CLAU_OFFSITE_ENV:-/etc/clau/offsite.env}"
NAME_RE='^clau-([0-9]{8})T([0-9]{2})([0-9]{2})([0-9]{2})Z(-[a-z0-9-]{1,32})?\.dump\.enc$'

die() { printf '\033[31mGAGAL: %s\033[0m\n' "$*" >&2; exit 1; }
judul() { printf '\n\033[1m%s\033[0m\n' "$*"; }
[ "$(id -u)" -eq 0 ] || [ -n "${CLAU_REPO:-}" ] || die "jalankan dengan sudo: sudo clau-vps2-restore"
cd "$REPO"
[ -f .env ] || die "$REPO/.env tidak ada (jalankan vps2-setup.sh dulu)"
mode="" list_only=0 limit=40
for arg in "$@"; do
  case "$arg" in
    --list) list_only=1 ;;
    --semua) limit=100000 ;;
    --server-pengganti) mode="$arg" ;;
    *) sed -n '2,16p' "$0"; exit 2 ;;
  esac
done

env_value() { grep -m1 "^$1=" .env | cut -d= -f2-; }
pg() { PGPASSWORD="$(env_value POSTGRES_PASSWORD)" docker compose exec -T -e PGPASSWORD db psql -h 127.0.0.1 -U postgres -v ON_ERROR_STOP=1 -qtA "$@"; }
when() {  # nama file → waktu WITA
  [[ "$1" =~ $NAME_RE ]] || { echo "?"; return; }
  TZ=Asia/Makassar date -d "${BASH_REMATCH[1]} ${BASH_REMATCH[2]}:${BASH_REMATCH[3]}:${BASH_REMATCH[4]} UTC" '+%Y-%m-%d %H:%M WITA'
}
hmac_ok() {  # hmac_ok FILE PASSPHRASE
  [ -s "$1.hmac" ] && [ "$(cat "$1.hmac")" = "$(CLAU_HMAC_KEY="$2" python3 -I scripts/backup_hmac.py "$1")" ]
}

# --- 1. Daftar backup: server + B2 --------------------------------------------------------------------------------
declare -A where size
for f in backups/clau-*.dump.enc; do
  [ -f "$f" ] || continue
  n="$(basename "$f")"
  [[ "$n" =~ $NAME_RE ]] || continue
  where[$n]=server; size[$n]=$(stat -c %s "$f")
done
offsite=0
if [ -f "$OFFSITE_ENV" ]; then
  if remote="$("$OFFSITE" list </dev/null)"; then
    offsite=1
    while read -r n s extra; do
      [[ "$n" =~ $NAME_RE && "$s" =~ ^[0-9]+$ && -z "$extra" ]] || continue  # nama dari B2 = data tak tepercaya
      if [ -n "${where[$n]:-}" ]; then where[$n]="server + B2"; else where[$n]=B2; size[$n]=$s; fi
    done <<<"$remote"
  else
    echo "(daftar B2 tidak bisa dibaca; hanya backup di server yang tampil)" >&2
  fi
fi
mapfile -t names < <(printf '%s\n' "${!where[@]}" | sort -r | head -n "$limit")
total=${#where[@]}
[ "${#names[@]}" -gt 0 ] && [ -n "${names[0]}" ] || die "tidak ada backup (server$([ "$offsite" = 1 ] && echo ' maupun B2'))"

judul "Backup tersedia (terbaru di atas)"
for i in "${!names[@]}"; do
  n="${names[$i]}" note=""
  [[ "$n" == *-sebelum-restore.dump.enc ]] && note="  (isi sebelum restore)"
  printf '  %2d. %s  %8s KB  %-12s %s%s\n' $((i + 1)) "$(when "$n")" $(( ${size[$n]:-0} / 1024 )) "${where[$n]}" "$n" "$note"
done
[ "$offsite" = 1 ] || echo "  (B2 belum disetel: hanya backup di server ini)"
[ "$total" -le "${#names[@]}" ] || echo "  (+$(( total - ${#names[@]} )) backup lebih lama: tambahkan --semua)"
[ "$list_only" = 1 ] && exit 0

# --- 2. Pilih (tanpa nilai default: harus diketik) ----------------------------------------------------------------
read -rp $'\nNomor backup yang dipulihkan (Enter = batal): ' pick || pick=""
[[ "$pick" =~ ^[0-9]+$ ]] && [ "$pick" -ge 1 ] && [ "$pick" -le "${#names[@]}" ] || die "dibatalkan; tidak ada yang diubah"
name="${names[$((pick - 1))]}"
file="backups/$name"
if [ ! -f "$file" ]; then
  judul "Mengambil dari B2"
  umask 077; mkdir -p backups
  "$OFFSITE" pull "$name" backups </dev/null
fi

# --- 3. Passphrase: backup dari server lama memakai passphrase lain ----------------------------------------------
new_secret=""
if [ "$mode" = "--server-pengganti" ]; then
  judul "Kunci server lama (dari password manager; tidak tampil saat di-paste)"
  read -rsp "CLAU_BACKUP_PASSPHRASE lama: " old_pass || old_pass=""; echo
  hmac_ok "$file" "$old_pass" || die "passphrase tidak cocok dengan backup ini (atau file rusak); tidak ada yang diubah"
  read -rsp "CLAU_SECRET_KEY lama: " new_secret || new_secret=""; echo
  [[ "$new_secret" =~ ^[A-Za-z0-9+/=_-]{32,256}$ ]] || die "CLAU_SECRET_KEY tidak valid (minimal 32 karakter); tidak ada yang diubah"
  export CLAU_RESTORE_PASSPHRASE="$old_pass"
elif ! hmac_ok "$file" "$(env_value CLAU_BACKUP_PASSPHRASE)"; then
  echo "Backup ini tidak cocok dengan passphrase server ini (backup dari server lain / passphrase lama)."
  echo "Server baru pengganti VPS 2 yang hilang? Batalkan (Enter) lalu: sudo clau-vps2-restore --server-pengganti"
  read -rsp "Passphrase backup dari password manager (tidak tampil): " old_pass || old_pass=""; echo
  hmac_ok "$file" "$old_pass" || die "passphrase salah atau file rusak/diubah; tidak ada yang diubah"
  export CLAU_RESTORE_PASSPHRASE="$old_pass"
fi

# --- 4. Uji di database sementara, bandingkan dengan isi sekarang -------------------------------------------------
judul "Menguji backup di database sementara"
verify="$(scripts/db-restore.sh --verify "$file" 2>&1 </dev/null)" || { echo "$verify" >&2; die "backup tidak lolos uji; tidak ada yang diubah"; }
rev="$(sed -n 's/^restore OK: .*migrasi \([0-9A-Za-z_]*\),.*/\1/p' <<<"$verify")"
backup_sum="$(sed -n 's/^isi backup: //p' <<<"$verify")"
grep -qs "^revision = '$rev'" backend/migrations/versions/*.py \
  || die "backup berasal dari versi aplikasi yang lebih baru (migrasi ${rev:-?}); tunggu deploy versi itu, lalu ulangi"
current_sum="$(pg -d clau < scripts/db-summary.sql 2>/dev/null || echo "(database kosong / tidak terbaca)")"

judul "Perbandingan"
printf '  Sekarang : %s\n' "$current_sum"
printf '  Backup   : %s\n' "$backup_sum"
printf '  Waktu backup: %s (%s, migrasi %s)\n' "$(when "$name")" "$name" "$rev"
[[ "$backup_sum" == "user 0,"* ]] && printf '\033[33m  PERINGATAN: backup ini tidak berisi user (database kosong). Pastikan ini yang dimaksud.\033[0m\n'
cat <<EOF

  Semua perubahan setelah waktu backup HILANG, termasuk user, password, 2FA, dan hak akses yang diubah setelahnya.
  Isi sekarang tetap disimpan dulu sebagai backup "…-sebelum-restore" (bisa dipulihkan lagi dengan perintah ini).
EOF
read -rp $'\nKetik PULIHKAN untuk lanjut (huruf besar): ' answer || answer=""
[ "$answer" = PULIHKAN ] || die "dibatalkan; tidak ada yang diubah"

# --- 5. Jeda deploy & backup otomatis ---------------------------------------------------------------------------
systemd=0 restored=0
cleanup() {  # selalu jalan saat keluar: .env kunci lama tidak pernah tertinggal tanpa restore; timer hidup lagi
  if [ "$restored" != 1 ] && [ -f .env.sebelum-pengganti ]; then
    mv .env.sebelum-pengganti .env && echo "(.env dikembalikan ke kunci server ini)" >&2
  fi
  [ "$systemd" = 1 ] && systemctl start clau2-deploy.timer clau2-backup.timer || true
}
trap cleanup EXIT
if [ -d /run/systemd/system ] && systemctl cat clau2-deploy.timer >/dev/null 2>&1; then
  systemd=1
  systemctl stop clau2-deploy.timer clau2-backup.timer
  while systemctl is-active --quiet clau2-backup.service; do echo "(menunggu backup terjadwal selesai)"; sleep 5; done
fi
exec 9>"$ROOT/.deploy.lock"
flock -w 1200 9 || die "deploy masih berjalan lebih dari 20 menit; ulangi nanti (journalctl -u clau2-deploy -n 80)"
# Mulai sini Ctrl-C / SSH terputus diabaikan: restore yang setengah jalan lebih berbahaya daripada menunggu.
trap '' HUP INT TERM

# --- 6. Server pengganti: kunci lama masuk .env (salinan .env sekarang disimpan; dikembalikan bila restore gagal) ---
set_env() {  # set_env NAMA NILAI tanpa sed: nilai tidak pernah ditafsirkan sebagai pola/ekspresi
  NAME="$1" VALUE="$2" awk 'BEGIN { n = ENVIRON["NAME"]; v = ENVIRON["VALUE"] }
    index($0, n "=") == 1 { print n "=" v; done = 1; next } { print } END { if (!done) print n "=" v }' .env > .env.baru
  chmod 600 .env.baru && mv .env.baru .env
}
if [ -n "$new_secret" ]; then
  cp -p .env .env.sebelum-pengganti
  set_env CLAU_BACKUP_PASSPHRASE "$CLAU_RESTORE_PASSPHRASE"
  set_env CLAU_SECRET_KEY "$new_secret"
  echo "Kunci server lama dipakai di .env (salinan sebelumnya: .env.sebelum-pengganti)."
fi

# --- 7. Pulihkan ------------------------------------------------------------------------------------------------

judul "Memulihkan $name"
log="$(mktemp)"
set +e
# setsid: restore berjalan di sesi proses sendiri, jadi Ctrl-C / SSH terputus tidak sampai ke docker compose (yang
# memasang penangkap sinyal sendiri). tee --output-error=warn: terminal yang hilang tidak mematahkan pipa restore.
setsid -w scripts/db-restore.sh --yes "$file" 2>&1 </dev/null | tee -i --output-error=warn "$log"
rc=${PIPESTATUS[0]}
set -e
safety="$(sed -n 's/^cadangan sebelum restore: //p' "$log")"
rm -f "$log"
[ "$systemd" = 1 ] && logger -t clau-vps2-restore "restore $name oleh ${SUDO_USER:-root}: exit $rc; cadangan $safety"
# Cadangan isi sebelumnya ikut disalin ke B2: server bisa hilang sesudah ini.
if [ -n "$safety" ] && [ "$offsite" = 1 ]; then "$OFFSITE" push "$safety" </dev/null || echo "(cadangan sebelum restore belum tersalin ke B2)" >&2; fi
if [ "$rc" != 0 ] && [ -n "$new_secret" ]; then
  mv .env.sebelum-pengganti .env
  docker compose up -d --wait --wait-timeout 300 backend </dev/null >/dev/null 2>&1 || true
  echo "(.env dikembalikan ke kunci server ini)" >&2
fi
[ "$rc" = 0 ] || die "restore tidak selesai; lihat pesan di atas (isi sebelumnya dikembalikan bila restore sempat berjalan). Cadangan: ${safety:-tidak ada}"
restored=1
[ -z "$new_secret" ] || rm -f .env.sebelum-pengganti  # secret server baru yang sudah tidak dipakai

# Jejak di audit_log (append-only): siapa memulihkan backup apa. Nilai lewat variabel psql, bukan disambung ke SQL.
pg -d clau -v backup="$name" -v safety="$safety" -v by="${SUDO_USER:-root}" -v mode="${mode:-biasa}" <<'SQL' \
  || echo "(restore BERHASIL, tapi jejak audit_log gagal ditulis; catat manual)" >&2
INSERT INTO audit_log (actor_id, action, object_type, object_id, meta)
VALUES (NULL, 'database.restore', 'database', 'clau',
        jsonb_build_object('backup', :'backup', 'cadangan_sebelumnya', :'safety', 'oleh_admin_server', :'by',
                           'mode', :'mode'));
SQL

judul "Selesai"
printf '  Isi sekarang : %s\n' "$(pg -d clau < scripts/db-summary.sql)"
port="$(env_value CLAU_FRONTEND_PORT || true)"
code=$(curl -s -o /dev/null -w '%{http_code}' "http://127.0.0.1:${port:-3000}/login" || true)
printf '  Halaman login: %s\n' "$code"
cat <<EOF
  Cadangan isi sebelumnya: $safety
  Berikutnya: login dan cek /users (user/password setelah waktu backup kembali ke kondisi saat itu),
  lalu jalankan: sudo clau-vps2-check
EOF
