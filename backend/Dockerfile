# syntax=docker/dockerfile:1
# Image backend FastAPI (read-only API). Build context = root repo, karena API membaca agents/registry.json:
#   docker build -f backend/Dockerfile -t clau-backend .
# Base image dipin ke digest (sama seperti Actions dipin ke SHA); Dependabot memperbaruinya.
FROM python:3.14-slim-bookworm@sha256:48b13b003dda20b16f9442b8475aa05fe21bf6579a8c881db92ffb4d8fd20f83

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    CLAU_ENV=production

WORKDIR /app
# Hanya dependency runtime (tanpa pytest/httpx2). Pin harus sama dengan requirements.txt (dites).
COPY backend/requirements-runtime.txt backend/requirements-runtime.txt
RUN pip install --no-cache-dir -r backend/requirements-runtime.txt

COPY agents/registry.json agents/registry.json
COPY backend/app backend/app
# Migrasi ikut di image: service compose `migrate` menjalankannya dengan role migrasi.
COPY backend/alembic.ini backend/alembic.ini
COPY backend/migrations backend/migrations

# User tanpa hak root dan tanpa shell login; file aplikasi milik root (tidak bisa diubah proses).
RUN useradd --system --uid 10001 --no-create-home --shell /usr/sbin/nologin clau
USER 10001
WORKDIR /app/backend

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3)"]
# --no-server-header: jangan umumkan teknologi server (docs/security.md § 3).
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-server-header"]
