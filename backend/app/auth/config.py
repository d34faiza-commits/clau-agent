"""Konfigurasi login dari environment (.env.example). Dibaca setiap request, bukan saat import, agar test
bisa mengubahnya. Mengganti CLAU_SECRET_KEY membatalkan semua sesi, 2FA, dan kode cadangan (reset-mfa)."""

from __future__ import annotations

import os
from dataclasses import dataclass

# __Host-: browser hanya menerima cookie ini dengan Secure, Path=/ dan tanpa Domain (tidak bisa ditimpa subdomain).
SESSION_COOKIE = "__Host-clau_session"
# Hanya CLAU_ENV=development: tanpa Secure, untuk browser yang menolak cookie Secure di http://localhost (Safari).
DEV_SESSION_COOKIE = "clau_session_dev"
CSRF_HEADER = "x-csrf-token"


@dataclass(frozen=True)
class AuthSettings:
    secret_key: bytes
    session_idle_minutes: int
    session_max_hours: int
    allowed_origins: frozenset[str]
    max_failed_logins: int
    lockout_minutes: int
    cookie_secure: bool

    @property
    def cookie_name(self) -> str:
        return SESSION_COOKIE if self.cookie_secure else DEV_SESSION_COOKIE


def _int(name: str, default: int) -> int:
    value = os.environ.get(name) or str(default)
    return int(value)


def auth_settings() -> AuthSettings:
    raw = os.environ.get("CLAU_SECRET_KEY") or ""
    origins = os.environ.get("CLAU_ALLOWED_ORIGINS") or "http://127.0.0.1:3000,http://localhost:3000"
    return AuthSettings(
        # Kosong = login dimatikan (fail closed, 503). Panjang minimum dicek di crypto.check_secret_key().
        secret_key=raw.encode(),
        session_idle_minutes=_int("CLAU_SESSION_IDLE_MINUTES", 120),
        session_max_hours=_int("CLAU_SESSION_MAX_HOURS", 12),
        allowed_origins=frozenset(o.strip().rstrip("/") for o in origins.split(",") if o.strip()),
        max_failed_logins=5,
        lockout_minutes=15,
        cookie_secure=(os.environ.get("CLAU_ENV") or "production") != "development",
    )
