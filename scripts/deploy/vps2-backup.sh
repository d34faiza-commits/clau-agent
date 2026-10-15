#!/usr/bin/env bash
# Backup database harian VPS 2 (clau2-backup.timer, root). Memakai scripts/db-backup.sh (AES-256 + HMAC,
# passphrase CLAU_BACKUP_PASSPHRASE di .env). Simpan 14 hari terakhir. Setiap Minggu: uji restore ke database
# sementara (db-restore.sh --verify). Salinan di luar server (Backblaze B2) menyusul (NEXT ACTION panduan).
#   sudo clau-vps2-backup
set -euo pipefail

REPO=/srv/clau/clau-ai-agents
KEEP_DAYS=14
cd "$REPO"

out=$(scripts/db-backup.sh | tee /dev/stderr | sed -n 's/^backup: \([^ ]*\).*/\1/p')
[ -n "$out" ] && [ -s "$out" ] || { echo "backup gagal" >&2; exit 1; }
find backups -maxdepth 1 -name 'clau-*.dump.enc*' -type f -mtime +"$KEEP_DAYS" -print -delete
if [ "$(date +%u)" = 7 ] || [ "${1:-}" = "--verify" ]; then
  scripts/db-restore.sh --verify "$out"
fi
