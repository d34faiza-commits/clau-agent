#!/usr/bin/env bash
# Cek semua salinan clau-core (core/, agents/core/, …) di-pin ke commit yang sama.
# Beda pin = warning (exit 0), karena repo upstream bisa belum di-sync;
# pakai --strict untuk menjadikannya error.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
STRICT=0; [[ "${1:-}" == "--strict" ]] && STRICT=1

mapfile -t PINS < <(git submodule status --recursive | awk '$2 == "core" || $2 ~ /\/core$/ {sub(/^[-+U ]/, "", $1); print $2" "$1}')
if [[ ${#PINS[@]} -le 1 ]]; then
  echo "core pin: ${PINS[0]:-tidak ada submodule core}"
  exit 0
fi
printf 'core pin: %s\n' "${PINS[@]}"
if [[ $(printf '%s\n' "${PINS[@]}" | awk '{print $2}' | sort -u | wc -l) -gt 1 ]]; then
  msg="pin clau-core berbeda antar submodule; jalankan scripts/sync-submodules.sh di repo yang tertinggal"
  if [[ $STRICT -eq 1 ]]; then echo "error: $msg" >&2; exit 1; fi
  echo "::warning::$msg"
fi
