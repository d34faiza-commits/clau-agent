#!/usr/bin/env bash
# Sync semua submodule ke commit terbaru branch-nya (lihat SUBMODULE.md).
#
# Langkah:
#   1. pastikan working tree bersih, lalu pull --ff-only branch saat ini
#   2. update tiap submodule top-level ke commit terbaru branch di .gitmodules
#      (submodule bertingkat, mis. agents/core, ikut pin milik repo agents)
#   3. jalankan validator repo (scripts/validate.py dan/atau backend pytest)
#   4. commit tersendiri per submodule: "chore(<nama>): bump <nama> to <hash>"
#      (sesuai core/AI-BOUNDARY.md, Multi-Repo & Submodule)
#   5. push (kecuali --no-push)
#
# Pemakaian:
#   scripts/sync-submodules.sh              # sync + validasi + commit + push
#   scripts/sync-submodules.sh --no-push    # commit lokal saja
#   scripts/sync-submodules.sh --dry-run    # tampilkan apa yang akan berubah, tanpa commit
#   scripts/sync-submodules.sh --skip-validate
#
# Exit code: 0 = sukses / tidak ada perubahan, 1 = gagal (validasi, push, atau tree kotor).

set -euo pipefail

PUSH=1
DRY_RUN=0
VALIDATE=1
for arg in "$@"; do
  case "$arg" in
    --no-push) PUSH=0 ;;
    --dry-run) DRY_RUN=1; PUSH=0 ;;
    --skip-validate) VALIDATE=0 ;;
    -h|--help) sed -n '2,20p' "$0"; exit 0 ;;
    *) echo "argumen tidak dikenal: $arg" >&2; exit 1 ;;
  esac
done

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

if [[ ! -f .gitmodules ]]; then
  echo "tidak ada .gitmodules di $ROOT; tidak ada yang di-sync"
  exit 0
fi

if [[ -n "$(git status --porcelain --ignore-submodules=none)" ]]; then
  echo "working tree tidak bersih; commit atau stash dulu:" >&2
  git status --short >&2
  exit 1
fi

BRANCH="$(git rev-parse --abbrev-ref HEAD)"
if git remote get-url origin >/dev/null 2>&1; then
  git pull --ff-only --quiet origin "$BRANCH"
fi

git submodule sync --recursive --quiet
git submodule update --init --recursive --quiet

mapfile -t PATHS < <(git config -f .gitmodules --get-regexp '^submodule\..*\.path$' | awk '{print $2}')

declare -a CHANGED=()
for path in "${PATHS[@]}"; do
  old="$(git -C "$path" rev-parse --short HEAD)"
  git submodule update --remote --quiet -- "$path"
  # Submodule bertingkat mengikuti pin milik submodule itu sendiri.
  git -C "$path" submodule update --init --recursive --quiet
  new="$(git -C "$path" rev-parse --short HEAD)"
  if [[ "$old" != "$new" ]]; then
    echo "$path: $old -> $new"
    git -C "$path" log --oneline "$old..$new" | sed 's/^/    /'
    CHANGED+=("$path:$new")
  else
    echo "$path: $old (sudah terbaru)"
  fi
done

if [[ ${#CHANGED[@]} -eq 0 ]]; then
  echo "semua submodule sudah terbaru; tidak ada commit"
  exit 0
fi

if [[ $DRY_RUN -eq 1 ]]; then
  echo "dry-run: kembalikan submodule ke pin semula"
  git submodule update --init --recursive --quiet
  exit 0
fi

if [[ $VALIDATE -eq 1 ]]; then
  if [[ -f scripts/validate.py ]]; then
    python3 scripts/validate.py --require-submodules
  fi
  if [[ -f backend/requirements.txt && -d backend/tests ]]; then
    (cd backend && python3 -m pytest -q)
  fi
fi

for item in "${CHANGED[@]}"; do
  path="${item%%:*}"
  hash="${item##*:}"
  git add -- "$path"
  git commit --quiet -m "chore($path): bump $path to $hash" -- "$path"
  echo "commit: chore($path): bump $path to $hash"
done

if [[ $PUSH -eq 1 ]]; then
  git push --quiet origin "$BRANCH"
  echo "push: origin/$BRANCH"
fi
