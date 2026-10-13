#!/usr/bin/env bash
# Buat .env dari .env.example dengan secret acak: password database (heksadesimal 48 karakter),
# CLAU_SECRET_KEY dan CLAU_BACKUP_PASSPHRASE (96 karakter). .env dibuat chmod 600 dan tidak di-commit.
#
# Bila .env sudah ada, nilai yang ada TIDAK diubah (password database harus tetap sama dengan volume
# yang sudah dibuat); hanya secret yang belum ada (mis. setelah upgrade) yang ditambahkan.
#
#   scripts/init-env.sh
set -euo pipefail
cd "$(dirname "$0")/.."

gen() { od -An -N24 -tx1 /dev/urandom | tr -d ' \n'; }
umask 077

declare -A SECRETS=(
  [POSTGRES_PASSWORD]=48 [CLAU_DB_MIGRATOR_PASSWORD]=48 [CLAU_DB_APP_PASSWORD]=48
  [CLAU_SECRET_KEY]=96 [CLAU_BACKUP_PASSPHRASE]=96
)
value() { if [[ $1 -eq 96 ]]; then echo "$(gen)$(gen)"; else gen; fi; }

if [[ ! -e .env ]]; then
  cp .env.example .env
  created=1
else
  created=0
fi
chmod 600 .env

added=()
for name in "${!SECRETS[@]}"; do
  if grep -q "^${name}=." .env; then
    continue  # sudah berisi: jangan pernah diganti
  elif grep -q "^${name}=\$" .env; then
    sed -i "s/^${name}=\$/${name}=$(value "${SECRETS[$name]}")/" .env
  else
    printf '%s=%s\n' "$name" "$(value "${SECRETS[$name]}")" >> .env
  fi
  added+=("$name")
done

if [[ $created -eq 1 ]]; then
  echo ".env dibuat (chmod 600) dengan secret acak"
elif [[ ${#added[@]} -gt 0 ]]; then
  echo ".env sudah ada; ditambahkan secret yang belum ada: ${added[*]} (nilai lain tidak diubah)"
else
  echo ".env sudah lengkap; tidak diubah"
fi
