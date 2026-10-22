"""Dependency FastAPI: koneksi database, sesi login, CSRF & Origin, dan peran."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from fastapi import Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import crypto
from app.auth.access import is_owner, mfa_required
from app.auth.config import CSRF_HEADER, AuthSettings, auth_settings
from app.db.models import Membership, User, UserSession
from app.errors import ApiError

SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}
TOUCH_EVERY = timedelta(minutes=1)


def now() -> datetime:
    return datetime.now(timezone.utc)


def get_db() -> Iterator[Session]:
    from app.db.session import session_factory

    try:
        factory = session_factory()
    except RuntimeError as exc:
        raise ApiError(503, "database_unavailable", "Database belum dikonfigurasi.") from exc
    with factory() as session:
        yield session


def get_settings() -> AuthSettings:
    settings = auth_settings()
    try:
        crypto.check_secret_key(settings.secret_key)
    except crypto.SecretKeyMissing as exc:
        # Fail closed: tanpa kunci server, login (CSRF, 2FA) tidak bisa aman.
        raise ApiError(503, "auth_unavailable", "Login belum dikonfigurasi di server.") from exc
    return settings


def check_origin(request: Request, settings: AuthSettings) -> None:
    """Request yang mengubah data dari browser harus berasal dari origin aplikasi sendiri."""
    if request.method in SAFE_METHODS:
        return
    if request.headers.get("sec-fetch-site") == "cross-site":
        raise ApiError(403, "origin_not_allowed", "Request lintas situs ditolak.")
    origin = request.headers.get("origin")
    if origin and origin.rstrip("/") not in settings.allowed_origins:
        raise ApiError(403, "origin_not_allowed", "Origin request tidak diizinkan.")


@dataclass
class AuthContext:
    user: User
    session: UserSession
    token: str
    memberships: list[Membership]

    @property
    def pending(self) -> str | None:
        """Langkah wajib yang belum selesai; selama ada, hanya endpoint akun yang boleh dipakai."""
        if self.user.must_change_password:
            return "password_change"
        # mfa_ok dihitung saat login; cek ulang di sini agar sesi yang dibuat sebelum 2FA diwajibkan untuk
        # perannya (mis. content_lead sebelum 0.9.1) tidak bisa dipakai tanpa mengaktifkan 2FA.
        if not self.session.mfa_ok or (mfa_required(self.memberships) and not self.user.totp_enabled):
            return "mfa_setup"
        return None


def load_auth(request: Request, db: Session, settings: AuthSettings) -> AuthContext | None:
    token = request.cookies.get(settings.cookie_name)
    if not token or len(token) > 128:
        return None
    row = db.get(UserSession, crypto.token_hash(token))
    t = now()
    if row is None or row.revoked_at is not None:
        return None
    if t >= row.expires_at or t - row.last_seen_at > timedelta(minutes=settings.session_idle_minutes):
        row.revoked_at = t
        db.commit()
        return None
    user = db.get(User, row.user_id)
    if user is None or user.disabled_at is not None:
        return None
    if t - row.last_seen_at > TOUCH_EVERY:
        row.last_seen_at = t
        db.commit()
    memberships = list(db.scalars(select(Membership).where(Membership.user_id == user.id)))
    return AuthContext(user=user, session=row, token=token, memberships=memberships)


def _authenticated(request: Request, db: Session, settings: AuthSettings, allow_pending: bool) -> AuthContext:
    check_origin(request, settings)
    ctx = load_auth(request, db, settings)
    if ctx is None:
        raise ApiError(401, "unauthenticated", "Silakan login.")
    if request.method not in SAFE_METHODS and not crypto.csrf_valid(settings.secret_key, ctx.token, request.headers.get(CSRF_HEADER)):
        raise ApiError(403, "csrf_failed", "Token CSRF tidak valid; muat ulang halaman.")
    if ctx.pending and not allow_pending:
        code = {"password_change": "password_change_required", "mfa_setup": "mfa_setup_required"}[ctx.pending]
        raise ApiError(403, code, "Selesaikan pengaturan akun dulu (ganti password / aktifkan 2FA).")
    return ctx


def current_user(request: Request, db: Session = Depends(get_db), settings: AuthSettings = Depends(get_settings)) -> AuthContext:
    return _authenticated(request, db, settings, allow_pending=False)


def current_user_pending_ok(request: Request, db: Session = Depends(get_db), settings: AuthSettings = Depends(get_settings)) -> AuthContext:
    """Untuk endpoint akun (me, logout, ganti password, aktifkan 2FA) yang harus bisa dipakai sebelum siap."""
    return _authenticated(request, db, settings, allow_pending=True)


def require_owner(ctx: AuthContext = Depends(current_user)) -> AuthContext:
    if not is_owner(ctx.memberships):
        raise ApiError(403, "forbidden", "Hanya owner yang boleh melakukan ini.")
    return ctx
