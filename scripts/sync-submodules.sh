#!/usr/bin/env bash
# Sync semua submodule ke commit terbaru branch-nya (lihat SUBMODULE.md).
#
# Langkah:
#   1. pastikan working tree bersih, lalu pull --ff-only branch saat ini
#   2. update tiap submodule top-level ke commit terbaru branch di .gitmodules
#      (submodule bertingkat, mis. agents/core, ikut pin milik repo agents).
#      Pengecualian: bila submodule lain memuat clau-core (agents/core), `core` dipin ke commit
#      yang SAMA dengan pin di dalamnya, bukan ke main core. Jadi core baru masuk marketing bersama
#      agents yang sudah lulus test terhadap core itu (pin core di semua tempat selalu sama).
#   3. cek pin core sama (scripts/check-core-pins.sh --strict), lalu validator repo
#      (scripts/validate.py dan/atau backend pytest)
#   4. commit tersendiri per submodule: "chore(<nama>): bump <nama> to <hash>"
#      (sesuai core/AI-BOUNDARY.md, Multi-Repo & Submodule)
#   5. push (kecuali --no-push) ke --pr-branch, lalu buka PR. Push langsung ke main ditolak
#      (AI-BOUNDARY § Disiplin Push: main wajib lewat PR dengan CI hijau).
#
# Pemakaian:
#   scripts/sync-submodules.sh --pr-branch chore/bump-core   # sync + validasi + commit + push branch; lalu buka PR
#   scripts/sync-submodules.sh --no-push    # commit lokal saja
#   scripts/sync-submodules.sh --dry-run    # tampilkan apa yang akan berubah, tanpa commit
#   scripts/sync-submodules.sh --skip-validate
#   scripts/sync-submodules.sh --pr-branch bot/sync-submodules   # dipakai workflow sync-submodules.yml
#
# Exit code: 0 = sukses / tidak ada perubahan, 1 = gagal (validasi, push, pin beda, atau tree kotor).

set -euo pipefail

PUSH=1
DRY_RUN=0
VALIDATE=1
PR_BRANCH=""
while [[ $# -gt 0 ]]; do
  arg="$1"; shift
  case "$arg" in
    --pr-branch) PR_BRANCH="${1:?--pr-branch butuh nama branch}"; shift ;;
    --no-push) PUSH=0 ;;
    --dry-run) DRY_RUN=1; PUSH=0 ;;
    --skip-validate) VALIDATE=0 ;;
    -h|--help) sed -n '2,25p' "$0"; exit 0 ;;
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
if [[ $PUSH -eq 1 && -z "$PR_BRANCH" && "$BRANCH" == "main" ]]; then
  echo "push langsung ke main tidak diizinkan (AI-BOUNDARY § Disiplin Push)." >&2
  echo "pakai: scripts/sync-submodules.sh --pr-branch chore/bump-submodules  lalu buka PR" >&2
  exit 1
fi
if git remote get-url origin >/dev/null 2>&1; then
  git pull --ff-only --quiet origin "$BRANCH"
fi

git submodule sync --recursive --quiet
git submodule update --init --recursive --quiet

# `core` diproses terakhir agar bisa mengikuti pin core milik submodule lain (mis. agents/core).
mapfile -t PATHS < <(git config -f .gitmodules --get-regexp '^submodule\..*\.path$' | awk '{print $2}' \
  | awk '$0 == "core" { last = $0; next } { print } END { if (last) print last }')

declare -a CHANGED=()
for path in "${PATHS[@]}"; do
  old="$(git -C "$path" rev-parse --short HEAD)"
  follow=""
  if [[ "$path" == "core" ]]; then
    for other in "${PATHS[@]}"; do
      if [[ "$other" != "core" ]] && git -C "$other" rev-parse --verify --quiet HEAD:core >/dev/null; then
        follow="$(git -C "$other" rev-parse HEAD:core)"
        echo "core: ikut pin $other/core ($(cut -c1-7 <<<"$follow"))"
        break
      fi
    done
  fi
  if [[ -n "$follow" ]]; then
    git -C "$path" fetch --quiet origin
    git -C "$path" checkout --quiet --detach "$follow"
  else
    git submodule update --remote --quiet -- "$path"
  fi
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

bash scripts/check-core-pins.sh --strict

if [[ $VALIDATE -eq 1 ]]; then
  if [[ -f scripts/validate.py ]]; then
    python3 scripts/validate.py --require-submodules
  fi
  if [[ -f backend/requirements.txt && -d backend/tests ]]; then
    (cd backend && python3 -m pytest -q)
  fi
fi

if [[ -n "$PR_BRANCH" ]]; then
  git checkout --quiet -B "$PR_BRANCH"
fi

for item in "${CHANGED[@]}"; do
  path="${item%%:*}"
  hash="${item##*:}"
  git add -- "$path"
  git commit --quiet -m "chore($path): bump $path to $hash" -- "$path"
  echo "commit: chore($path): bump $path to $hash"
done

if [[ $PUSH -eq 1 ]]; then
  if [[ -n "$PR_BRANCH" ]]; then
    # Branch milik bot, dibuat ulang tiap sync dari branch dasar terbaru.
    git push --quiet --force origin "$PR_BRANCH"
    echo "push: origin/$PR_BRANCH (buka PR ke $BRANCH)"
  else
    git push --quiet origin "$BRANCH"
    echo "push: origin/$BRANCH (buka PR ke main)"
  fi
fi
