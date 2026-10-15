#!/usr/bin/env bash
# Backup database VPS 2 setiap 6 jam (clau2-backup.timer 02/08/14/20 WITA, root). Memakai scripts/db-backup.sh
# (AES-256 + HMAC, passphrase CLAU_BACKUP_PASSPHRASE di .env). Simpan 14 hari di server; bila B2 sudah disetel
# (clau-vps2-offsite setup) setiap backup juga disalin ke Backblaze B2. Uji restore ke database sementara
# (db-restore.sh --verify) paling sedikit seminggu sekali. Pemulihan: sudo clau-vps2-restore (selalu manual).
#   sudo clau-vps2-backup            # backup sekarang
#   sudo clau-vps2-backup --verify   # backup sekarang + uji restore
set -euo pipefail

REPO=/srv/clau/clau-ai-agents
ROOT=/srv/clau
OFFSITE_ENV=/etc/clau/offsite.env
VERIFIED="$ROOT/.verify-last"
KEEP_DAYS=14
cd "$REPO"

out=$(scripts/db-backup.sh | tee /dev/stderr | sed -n 's/^backup: \([^ ]*\).*/\1/p')
[ -n "$out" ] && [ -s "$out" ] || { echo "backup gagal" >&2; exit 1; }
find backups -maxdepth 1 -name 'clau-*.dump.enc*' -type f -mtime +"$KEEP_DAYS" -print -delete

status=0
if [ -f "$OFFSITE_ENV" ]; then
  /usr/local/sbin/clau-vps2-offsite push "$out" || { echo "salinan ke B2 GAGAL (backup lokal tetap ada)" >&2; status=1; }
fi
last=$(stat -c %Y "$VERIFIED" 2>/dev/null || echo 0)
if [ "${1:-}" = "--verify" ] || [ $(( $(date +%s) - last )) -gt $(( 6 * 86400 )) ]; then
  scripts/db-restore.sh --verify "$out" && touch "$VERIFIED"
fi
exit "$status"
