# syntax=docker/dockerfile:1
# Image frontend Next.js. Build context = root repo, karena halaman membaca agents/ saat build:
#   docker build -f frontend/Dockerfile -t clau-frontend .
# Base image dipin ke digest; Dependabot memperbaruinya. Node 22 = sama dengan CI.
ARG NODE_IMAGE=node:22-bookworm-slim@sha256:c3de60bf2f9dd0ac6370e6117950ff62d6e339527e7472301c9c78a017978392

# 1. Build. --ignore-scripts: sama dengan CI dan VPS 1 (docs/security.md § 5).
FROM ${NODE_IMAGE} AS build
ENV NODE_ENV=production NEXT_TELEMETRY_DISABLED=1 CLAU_STANDALONE=1
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --ignore-scripts --no-audit --no-fund
WORKDIR /app
COPY agents/registry.json agents/registry.json
COPY agents/personas agents/personas
COPY agents/evals/cases agents/evals/cases
COPY frontend frontend
WORKDIR /app/frontend
RUN npm run build

# 2. Runtime: output standalone (server.js + dependency yang benar-benar dipakai), tanpa npm install.
FROM ${NODE_IMAGE}
ENV NODE_ENV=production NEXT_TELEMETRY_DISABLED=1 HOSTNAME=0.0.0.0 PORT=3000
WORKDIR /app
COPY --from=build /app/frontend/.next/standalone ./
COPY --from=build /app/frontend/.next/static frontend/.next/static
COPY frontend/public frontend/public
# Halaman agent membaca persona & eval dari ../agents (lib/persona.ts).
COPY agents/registry.json agents/registry.json
COPY agents/personas agents/personas
COPY agents/evals/cases agents/evals/cases
WORKDIR /app/frontend
# Next.js menulis cache ISR ke .next/cache: hanya folder itu yang milik user aplikasi.
RUN mkdir -p .next/cache && chown node:node .next/cache
USER node

EXPOSE 3000
# /login: halaman publik (200 tanpa redirect). Halaman lain mengarahkan ke CLAU_PUBLIC_ORIGIN (mis. alamat
# HTTPS Tailscale) yang tidak bisa dijangkau dari dalam container, jadi redirect tidak diikuti.
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD ["node", "-e", "fetch('http://127.0.0.1:3000/login', { redirect: 'manual' }).then(r => process.exit(r.status === 200 ? 0 : 1)).catch(() => process.exit(1))"]
CMD ["node", "server.js"]
