#!/usr/bin/env bash
# Backup database terenkripsi (docs/security.md § 6, keputusan VPS #6).
#   pg_dump (format custom) → AES-256-CBC, kunci dari CLAU_BACKUP_PASSPHRASE lewat PBKDF2 600.000 iterasi
#   → backups/clau-<waktu UTC>.dump.enc + .hmac (HMAC-SHA256, cek keutuhan sebelum restore).
# Tanpa passphrase backup tidak bisa dibuka: simpan passphrase di password manager owner, terpisah dari
# file backup. Salin file ke luar server (Backblaze B2) dan uji restore bulanan: scripts/db-restore.sh --verify.
#
#   scripts/db-backup.sh                  # stack docker compose harus jalan
#   scripts/db-backup.sh sebelum-restore  # label di nama file (huruf kecil, angka, tanda -)
set -euo pipefail
cd "$(dirname "$0")/.."

label="${1:-}"
[[ -z "$label" || "$label" =~ ^[a-z0-9-]{1,32}$ ]] || { echo "label tidak valid: $label" >&2; exit 2; }

env_value() { grep -m1 "^$1=" .env | cut -d= -f2-; }
PASS="$(env_value CLAU_BACKUP_PASSPHRASE)"
PGPASS="$(env_value POSTGRES_PASSWORD)"
if [[ ${#PASS} -lt 32 ]]; then
  echo "CLAU_BACKUP_PASSPHRASE kosong/terlalu pendek di .env (jalankan scripts/init-env.sh)" >&2
  exit 1
fi

umask 077
mkdir -p backups
out="backups/clau-$(date -u +%Y%m%dT%H%M%SZ)${label:+-$label}.dump.enc"
trap 'rm -f "$out" "$out.hmac"' ERR  # dump gagal di tengah: jangan tinggalkan file setengah jadi
docker compose exec -T -e PGPASSWORD="$PGPASS" db pg_dump -h 127.0.0.1 -U postgres -d clau -Fc --no-password \
  | PASS="$PASS" openssl enc -aes-256-cbc -pbkdf2 -iter 600000 -salt -pass env:PASS -out "$out"
CLAU_HMAC_KEY="$PASS" python3 -I scripts/backup_hmac.py "$out" > "$out.hmac"
echo "backup: $out ($(wc -c < "$out") byte, terenkripsi)"
