#!/usr/bin/env bash
# Buat .env dari .env.example dengan password database acak (heksadesimal 48 karakter).
# Tidak pernah menimpa .env yang sudah ada. .env dibuat chmod 600 dan tidak di-commit (.gitignore).
#
#   scripts/init-env.sh
set -euo pipefail
cd "$(dirname "$0")/.."

if [[ -e .env ]]; then
  echo ".env sudah ada; tidak diubah (hapus dulu bila memang ingin membuat ulang)"
  exit 0
fi

gen() { od -An -N24 -tx1 /dev/urandom | tr -d ' \n'; }

umask 077
sed -e "s/^POSTGRES_PASSWORD=\$/POSTGRES_PASSWORD=$(gen)/" \
    -e "s/^CLAU_DB_MIGRATOR_PASSWORD=\$/CLAU_DB_MIGRATOR_PASSWORD=$(gen)/" \
    -e "s/^CLAU_DB_APP_PASSWORD=\$/CLAU_DB_APP_PASSWORD=$(gen)/" \
    .env.example > .env
echo ".env dibuat (chmod 600) dengan password database acak"
