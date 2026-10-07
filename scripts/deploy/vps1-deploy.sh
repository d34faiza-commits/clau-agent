#!/usr/bin/env bash
# Pull-based deploy of the frontend on VPS 1 (docs/deploy/vps-1-setup.md §9).
# Run by clau-deploy.timer as user dea. Nothing on GitHub can reach into the server:
# the server pulls main with a read-only deploy key, builds a new release next to the
# running one, switches the `current` symlink, and rolls back if the health check fails.
set -euo pipefail

ROOT="${CLAU_ROOT:-/srv/clau}"
REPO="$ROOT/clau-ai-agents"
RELEASES="$ROOT/releases"
CURRENT="$ROOT/current"
BRANCH="${CLAU_BRANCH:-main}"
KEEP=3
HEALTH_URL="${CLAU_HEALTH_URL:-http://127.0.0.1:3000}"
RESTART="${CLAU_RESTART:-sudo -n /usr/bin/systemctl restart clau-frontend}"
# Only these paths change what the frontend serves.
WATCH=(frontend agents/registry.json)

log() { echo "[clau-deploy] $*"; }

exec 9>"$ROOT/.deploy.lock"
flock -n 9 || { log "another deploy is running"; exit 0; }

git -C "$REPO" pull --quiet --ff-only origin "$BRANCH"
new=$(git -C "$REPO" rev-parse HEAD)
old=""
[ -f "$CURRENT/.sha" ] && old=$(cat "$CURRENT/.sha")

if [ "$new" = "$old" ]; then
  exit 0
fi
# A commit that already failed is not retried every 5 minutes; push a fix or use --force.
if [ "${1:-}" != "--force" ] && [ "$(cat "$ROOT/.failed-sha" 2>/dev/null)" = "$new" ]; then
  exit 1
fi
if [ -n "$old" ] && [ "${1:-}" != "--force" ] && git -C "$REPO" diff --quiet "$old" "$new" -- "${WATCH[@]}"; then
  log "${new:0:12}: no frontend changes since ${old:0:12}, skip build"
  echo "$new" > "$CURRENT/.sha"
  exit 0
fi

dir="$RELEASES/${new:0:12}"
log "building ${new:0:12} in $dir"
mkdir -p "$RELEASES"
rm -rf "$dir"
mkdir -p "$dir"
git -C "$REPO" archive "$new" | tar -x -C "$dir"
if ! (cd "$dir/frontend" && npm ci --no-audit --no-fund && npm run build); then
  log "build FAILED for ${new:0:12}; still serving ${old:0:12}"
  rm -rf "$dir"
  echo "$new" > "$ROOT/.failed-sha"
  exit 1
fi
echo "$new" > "$dir/.sha"

prev=$(readlink -f "$CURRENT" 2>/dev/null || true)
ln -sfn "$dir" "$CURRENT.new" && mv -T "$CURRENT.new" "$CURRENT"
$RESTART 9>&-

healthy() {
  for _ in $(seq 1 30); do
    curl -fsS -o /dev/null "$HEALTH_URL" && return 0
    sleep 1
  done
  return 1
}

if ! healthy; then
  log "health check FAILED for ${new:0:12}"
  if [ -n "$prev" ] && [ -d "$prev" ]; then
    ln -sfn "$prev" "$CURRENT.new" && mv -T "$CURRENT.new" "$CURRENT"
    $RESTART 9>&-
    log "rolled back to $(basename "$prev")"
  fi
  echo "$new" > "$ROOT/.failed-sha"
  exit 1
fi
rm -f "$ROOT/.failed-sha"
log "live: ${new:0:12}"

# Keep the newest $KEEP releases (the live one is always kept).
live=$(readlink -f "$CURRENT")
ls -1dt "$RELEASES"/*/ 2>/dev/null | sed 's#/$##' | tail -n +$((KEEP + 1)) | while read -r d; do
  [ "$d" = "$live" ] || rm -rf "$d"
done
