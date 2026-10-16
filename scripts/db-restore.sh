#!/usr/bin/env bash
# Pulihkan backup dari scripts/db-backup.sh. Keutuhan (HMAC) dicek dulu; file rusak/diubah ditolak.
#
#   scripts/db-restore.sh --verify backups/clau-….dump.enc   # uji restore ke database sementara, lalu dihapus
#   scripts/db-restore.sh --yes    backups/clau-….dump.enc   # GANTI isi database clau dengan backup ini
#
# --yes membuat backup isi database sekarang dulu (backups/clau-…-sebelum-restore.dump.enc), lalu menghentikan
# backend selama restore. Di VPS 2 pakai `sudo clau-vps2-restore` (pilih backup, uji, konfirmasi, cek sehat).
# Backup dari server lama (passphrase lain): isi CLAU_RESTORE_PASSPHRASE di environment, bukan di argumen.
# Uji --verify tiap bulan (keputusan VPS #6).
set -euo pipefail
cd "$(dirname "$0")/.."

mode="${1:-}"; file="${2:-}"
if [[ "$mode" != "--verify" && "$mode" != "--yes" ]] || [[ ! -f "$file" ]]; then
  sed -n '2,10p' "$0"; exit 2
fi

env_value() { grep -m1 "^$1=" .env | cut -d= -f2-; }
PASS="${CLAU_RESTORE_PASSPHRASE:-$(env_value CLAU_BACKUP_PASSPHRASE)}"
PGPASS="$(env_value POSTGRES_PASSWORD)"

expected="$(cat "$file.hmac" 2>/dev/null || true)"
actual="$(CLAU_HMAC_KEY="$PASS" python3 -I scripts/backup_hmac.py "$file")"
if [[ -z "$expected" || "$expected" != "$actual" ]]; then
  echo "backup ditolak: HMAC tidak cocok (file rusak/diubah, atau passphrase berbeda)" >&2
  exit 1
fi

decrypt() { PASS="$PASS" openssl enc -d -aes-256-cbc -pbkdf2 -iter 600000 -pass env:PASS -in "$file"; }
psql_admin() { PGPASSWORD="$PGPASS" docker compose exec -T -e PGPASSWORD db psql -h 127.0.0.1 -U postgres -v ON_ERROR_STOP=1 -qtA "$@"; }
restore_into() {
  decrypt | PGPASSWORD="$PGPASS" docker compose exec -T -e PGPASSWORD db pg_restore -h 127.0.0.1 -U postgres -d "$1" --exit-on-error --no-password "${@:2}"
}

if [[ "$mode" == "--verify" ]]; then
  check="clau_restore_check_$$"  # unik per proses: uji terjadwal & uji manual bisa berjalan bersamaan
  psql_admin -d postgres -c "DROP DATABASE IF EXISTS $check" -c "CREATE DATABASE $check"
  trap 'psql_admin -d postgres -c "DROP DATABASE IF EXISTS $check" >/dev/null' EXIT
  restore_into "$check"
  tables="$(psql_admin -d "$check" -c "SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public'")"
  version="$(psql_admin -d "$check" -c "SELECT version_num FROM alembic_version")"
  audit="$(psql_admin -d "$check" -c "SELECT count(*) FROM audit_log")"
  summary="$(psql_admin -d "$check" < scripts/db-summary.sql)"
  echo "restore OK: $tables tabel, migrasi $version, $audit baris audit_log (database uji dihapus)"
  echo "isi backup: $summary"
else
  new=clau_restore_new old=clau_sebelum_restore failed=clau_restore_gagal
  WRITERS="backend worker"  # service yang menulis ke database (frontend tidak)
  # Sisa restore yang terputus (mis. server mati di tengah) tidak pernah dihapus diam-diam: bisa jadi satu-satunya
  # salinan isi sebelumnya.
  leftover="$(psql_admin -d postgres -c "SELECT string_agg(datname, ' ') FROM pg_database WHERE datname IN ('$old', '$failed')")"
  if [[ -n "$leftover" ]]; then
    echo "ada sisa restore yang terputus: database $leftover. Restore dibatalkan; periksa dulu (docs/deploy/vps-2-setup.md § 5)." >&2
    exit 1
  fi

  # Dari sini sampai selesai: Ctrl-C / SSH terputus diabaikan (terputus saat menukar database = `clau` hilang), dan
  # setiap langkah dicek sendiri (set +e) supaya kegagalan tidak menghentikan script di tengah jalan.
  trap '' HUP INT TERM PIPE
  set +e
  # Backend dan worker AI berhenti DULU: tidak ada tulisan baru antara cadangan dan restore yang bisa hilang.
  docker compose stop $WRITERS >/dev/null 2>&1
  safety="$(scripts/db-backup.sh sebelum-restore | sed -n 's/^backup: \([^ ]*\).*/\1/p')"
  if [[ -z "$safety" || ! -s "$safety" ]]; then
    docker compose start $WRITERS >/dev/null 2>&1
    echo "backup isi sekarang GAGAL: restore dibatalkan, database tidak diubah" >&2
    exit 1
  fi
  echo "cadangan sebelum restore: $safety"

  # Backup dipulihkan ke database baru di samping `clau`; `clau` baru ditukar setelah restore lengkap. Gagal di
  # tengah = `clau` tidak tersentuh. Database baru (bukan --clean) juga menghindari tabel versi lebih baru yang
  # tertinggal dan menghalangi restore backup lama.
  if ! psql_admin -d postgres -c "DROP DATABASE IF EXISTS $new" -c "CREATE DATABASE $new OWNER clau_migrator ENCODING 'UTF8' TEMPLATE template0" \
     || ! restore_into "$new"; then
    psql_admin -d postgres -c "DROP DATABASE IF EXISTS $new" >/dev/null 2>&1
    docker compose start $WRITERS >/dev/null 2>&1
    echo "restore GAGAL: database clau tidak diubah" >&2
    exit 1
  fi
  swap() {  # swap DARI KE: ganti nama database tanpa koneksi aktif
    psql_admin -d postgres -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname IN ('$1', '$2') AND pid <> pg_backend_pid()" >/dev/null \
      && psql_admin -d postgres -c "ALTER DATABASE $1 RENAME TO $2"
  }
  if ! swap clau "$old"; then
    psql_admin -d postgres -c "DROP DATABASE IF EXISTS $new" >/dev/null 2>&1
    docker compose start $WRITERS >/dev/null 2>&1
    echo "restore GAGAL (database clau tidak bisa ditukar): database clau tidak diubah" >&2
    exit 1
  fi
  if swap "$new" clau && docker compose up -d --wait --wait-timeout 300 $WRITERS >/dev/null 2>&1; then
    # `up` menjalankan service migrate dulu (hak akses role + alembic upgrade head: backup dari versi lebih lama
    # dinaikkan ke skema kode sekarang), lalu backend sampai sehat.
    psql_admin -d postgres -c "DROP DATABASE $old" >/dev/null 2>&1 \
      || echo "(database $old belum terhapus; hapus manual setelah dicek)" >&2
    echo "restore selesai: database clau = $file; backend sehat"
    exit 0
  fi
  echo "backend tidak sehat setelah restore: database dikembalikan ke isi sebelumnya" >&2
  docker compose stop $WRITERS >/dev/null 2>&1
  if psql_admin -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname = 'clau'" | grep -q 1; then
    swap clau "$failed" || echo "(gagal memindahkan database hasil restore ke $failed)" >&2
  fi
  if swap "$old" clau; then
    psql_admin -d postgres -c "DROP DATABASE IF EXISTS $failed" >/dev/null 2>&1
    psql_admin -d postgres -c "DROP DATABASE IF EXISTS $new" >/dev/null 2>&1
  else
    echo "PERLU TINDAKAN: database $old belum bisa dikembalikan menjadi clau. Cadangan file: $safety" >&2
  fi
  docker compose up -d --wait --wait-timeout 300 $WRITERS >/dev/null 2>&1 \
    || echo "backend masih belum sehat: docker compose logs --tail 50 migrate backend; cadangan: $safety" >&2
  exit 1
fi
