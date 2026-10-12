"""Konfigurasi login dari environment (.env.example). Dibaca saat dipanggil, bukan saat import, agar test
dan rotasi kunci tidak butuh restart modul."""

from __future__ import annotations

import os
from dataclasses import dataclass

# __Host-: browser hanya menerima cookie ini dengan Secure, Path=/ dan tanpa Domain (tidak bisa ditimpa subdomain).
SESSION_COOKIE = "__Host-clau_session"
CSRF_HEADER = "x-csrf-token"


@dataclass(frozen=True)
class AuthSettings:
    secret_key: bytes
    session_idle_minutes: int
    session_max_hours: int
    allowed_origins: frozenset[str]
    max_failed_logins: int
    lockout_minutes: int


def _int(name: str, default: int) -> int:
    value = os.environ.get(name) or str(default)
    return int(value)


def auth_settings() -> AuthSettings:
    raw = os.environ.get("CLAU_SECRET_KEY") or ""
    origins = os.environ.get("CLAU_ALLOWED_ORIGINS") or "http://127.0.0.1:3000,http://localhost:3000"
    return AuthSettings(
        # Kosong = login dimatikan (fail closed, 503). Panjang minimum dicek di secret_key_bytes().
        secret_key=raw.encode(),
        session_idle_minutes=_int("CLAU_SESSION_IDLE_MINUTES", 120),
        session_max_hours=_int("CLAU_SESSION_MAX_HOURS", 12),
        allowed_origins=frozenset(o.strip().rstrip("/") for o in origins.split(",") if o.strip()),
        max_failed_logins=5,
        lockout_minutes=15,
    )
