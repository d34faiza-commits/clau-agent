#!/usr/bin/env bash
# Pulihkan backup dari scripts/db-backup.sh. Keutuhan (HMAC) dicek dulu; file rusak/diubah ditolak.
#
#   scripts/db-restore.sh --verify backups/clau-….dump.enc   # uji restore ke database sementara, lalu dihapus
#   scripts/db-restore.sh --yes    backups/clau-….dump.enc   # GANTI isi database clau dengan backup ini
#
# --yes menghentikan backend selama restore. Uji --verify tiap bulan (keputusan VPS #6).
set -euo pipefail
cd "$(dirname "$0")/.."

mode="${1:-}"; file="${2:-}"
if [[ "$mode" != "--verify" && "$mode" != "--yes" ]] || [[ ! -f "$file" ]]; then
  sed -n '2,7p' "$0"; exit 2
fi

env_value() { grep -m1 "^$1=" .env | cut -d= -f2-; }
PASS="$(env_value CLAU_BACKUP_PASSPHRASE)"
PGPASS="$(env_value POSTGRES_PASSWORD)"

expected="$(cat "$file.hmac" 2>/dev/null || true)"
actual="$(PASS="$PASS" openssl dgst -sha256 -hmac "$PASS" -r "$file" | cut -d' ' -f1)"
if [[ -z "$expected" || "$expected" != "$actual" ]]; then
  echo "backup ditolak: HMAC tidak cocok (file rusak/diubah, atau passphrase berbeda)" >&2
  exit 1
fi

decrypt() { PASS="$PASS" openssl enc -d -aes-256-cbc -pbkdf2 -iter 600000 -pass env:PASS -in "$file"; }
psql_admin() { docker compose exec -T -e PGPASSWORD="$PGPASS" db psql -h 127.0.0.1 -U postgres -v ON_ERROR_STOP=1 -qtA "$@"; }
restore_into() {
  decrypt | docker compose exec -T -e PGPASSWORD="$PGPASS" db pg_restore -h 127.0.0.1 -U postgres -d "$1" --exit-on-error --no-password "${@:2}"
}

if [[ "$mode" == "--verify" ]]; then
  check="clau_restore_check"
  psql_admin -d postgres -c "DROP DATABASE IF EXISTS $check" -c "CREATE DATABASE $check"
  trap 'psql_admin -d postgres -c "DROP DATABASE IF EXISTS $check" >/dev/null' EXIT
  restore_into "$check"
  tables="$(psql_admin -d "$check" -c "SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public'")"
  version="$(psql_admin -d "$check" -c "SELECT version_num FROM alembic_version")"
  audit="$(psql_admin -d "$check" -c "SELECT count(*) FROM audit_log")"
  echo "restore OK: $tables tabel, migrasi $version, $audit baris audit_log (database uji dihapus)"
else
  docker compose stop backend >/dev/null
  restore_into clau --clean --if-exists
  docker compose start backend >/dev/null
  echo "restore selesai: database clau = $file; backend dijalankan lagi"
fi
