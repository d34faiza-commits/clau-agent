#!/usr/bin/env bash
# Deploy otomatis VPS 2 (docs/deploy/vps-2-setup.md). Dijalankan clau2-deploy.timer (root: Docker butuh root).
# Server menarik commit release/vps1 (hanya commit main yang CI-nya hijau, AI-BOUNDARY 1.3.0) dengan deploy key
# read-only; GitHub tidak bisa masuk ke server. Alur:
#   1. Commit baru? Bila migrasi database berubah: backup terenkripsi DULU (migrasi tidak bisa dibatalkan otomatis).
#   2. Image yang sedang jalan disimpan sebagai :prev, lalu build + `docker compose up --wait`.
#   3. Health check gagal → skema database diturunkan ke revisi sebelumnya (alembic downgrade, dites di CI) bila
#      migrasi sempat jalan, lalu kembali ke image & commit sebelumnya; commit gagal tidak dicoba ulang tiap 5 menit.
#   sudo clau-vps2-deploy            # manual
#   sudo clau-vps2-deploy --force    # ulangi commit yang pernah gagal
set -euo pipefail

ROOT=/srv/clau
REPO="$ROOT/clau-ai-agents"
ETC=/etc/clau
BRANCH="${CLAU_BRANCH:-release/vps1}"
LIVE="$ROOT/.live-sha"
FAILED="$ROOT/.failed-sha"
IMAGES=(clau-backend clau-frontend)
export GIT_SSH_COMMAND="ssh -i $ETC/deploy_key -o IdentitiesOnly=yes -o StrictHostKeyChecking=yes -o UserKnownHostsFile=$ETC/known_hosts"

log() { echo "[clau2-deploy] $*"; }

exec 9>"$ROOT/.deploy.lock"
flock -n 9 || { log "deploy lain sedang berjalan"; exit 0; }
cd "$REPO"

# fetch, bukan pull: yang di-build persis commit yang ditunjuk branch deploy.
git fetch --quiet origin "$BRANCH"
new=$(git rev-parse FETCH_HEAD)
old=$(cat "$LIVE" 2>/dev/null || true)
[ "$new" = "$old" ] && exit 0
if [ "${1:-}" != "--force" ] && [ "$(cat "$FAILED" 2>/dev/null)" = "$new" ]; then
  exit 1
fi

healthy() {
  for _ in $(seq 1 60); do
    if curl -fs -o /dev/null http://127.0.0.1:8000/health && curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:3000/login | grep -q '^200$'; then
      return 0
    fi
    sleep 2
  done
  return 1
}

env_value() { grep -m1 "^$1=" .env | cut -d= -f2-; }
db_rev() {
  PGPASSWORD="$(env_value POSTGRES_PASSWORD)" docker compose exec -T -e PGPASSWORD db \
    psql -h 127.0.0.1 -U postgres -d clau -tAc "SELECT version_num FROM alembic_version" 2>/dev/null || true
}
prev_rev=$(db_rev)

if [ -n "$old" ] && ! git diff --quiet "$old" "$new" -- backend/migrations; then
  log "migrasi berubah (${old:0:12} → ${new:0:12}): backup database dulu"
  /usr/local/sbin/clau-vps2-backup || { log "backup GAGAL: deploy dibatalkan"; echo "$new" > "$FAILED"; exit 1; }
fi

for img in "${IMAGES[@]}"; do
  docker image inspect "$img:local" >/dev/null 2>&1 && docker tag "$img:local" "$img:prev"
done

log "build ${new:0:12}"
git checkout --quiet --detach "$new"
if docker compose build && docker compose up -d --wait --wait-timeout 600 && healthy; then
  echo "$new" > "$LIVE"
  rm -f "$FAILED"
  docker image prune -f >/dev/null
  log "live: ${new:0:12}"
  exit 0
fi

log "deploy ${new:0:12} GAGAL; kembali ke ${old:0:12}"
echo "$new" > "$FAILED"
if [ -n "$old" ]; then
  # Image baru masih bertag :local dan mengenal revisi lama maupun baru: turunkan skema dengannya.
  now_rev=$(db_rev)
  if [ -n "$prev_rev" ] && [ -n "$now_rev" ] && [ "$now_rev" != "$prev_rev" ]; then
    log "skema database $now_rev → kembali ke $prev_rev"
    if ! docker compose run --rm --no-deps migrate alembic downgrade "$prev_rev"; then
      log "downgrade GAGAL: pulihkan manual dari backup terakhir (sudo clau-vps2-check, docs/deploy/vps-2-setup.md)"
      exit 1
    fi
  fi
  git checkout --quiet --detach "$old"
  for img in "${IMAGES[@]}"; do
    docker image inspect "$img:prev" >/dev/null 2>&1 && docker tag "$img:prev" "$img:local"
  done
  docker compose up -d --no-build --wait --wait-timeout 300 && healthy && log "kembali live: ${old:0:12}" \
    || log "rollback BELUM sehat: docker compose ps; docker compose logs --tail 50"
fi
exit 1
