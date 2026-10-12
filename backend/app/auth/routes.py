"""Endpoint login, akun, 2FA, dan manajemen user (khusus owner). docs/security.md § 6.

Tidak ada pendaftaran publik: owner pertama dibuat lewat `python -m app.auth.cli create-owner`, user lain
dibuat owner lewat POST /users dengan password sementara yang wajib diganti saat login pertama.
"""

from __future__ import annotations

import threading
import time
from collections import defaultdict, deque
from datetime import timedelta

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth import crypto
from app.auth.access import is_owner, mfa_required
from app.auth.config import SESSION_COOKIE, AuthSettings
from app.auth.deps import AuthContext, check_origin, current_user_pending_ok, get_db, get_settings, now, require_owner
from app.db.models import LEVELS, LOCALES, ROLES, TIMEZONES, AuditLog, Client, Membership, User, UserSession
from app.errors import ApiError

router = APIRouter()

EMAIL_PATTERN = r"^[^@\s]{1,64}@[^@\s]{1,190}$"


# --- Throttle per email (di memori) --------------------------------------------------------------


class LoginThrottle:
    """Batas gagal login per email, juga untuk email yang tidak terdaftar, supaya respons akun ada dan
    tidak ada terlihat sama (tidak bisa dipakai menebak email). Penguncian akun yang persisten ada di
    database (users.locked_until); batas per IP dipasang di Nginx saat deploy."""

    def __init__(self, limit: int = 5, window_seconds: int = 900) -> None:
        self.limit, self.window = limit, window_seconds
        self._fails: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def _prune(self, key: str, t: float) -> deque[float]:
        q = self._fails[key]
        while q and t - q[0] > self.window:
            q.popleft()
        return q

    def blocked(self, key: str) -> bool:
        with self._lock:
            return len(self._prune(key, time.monotonic())) >= self.limit

    def fail(self, key: str) -> None:
        with self._lock:
            self._prune(key, time.monotonic()).append(time.monotonic())

    def reset(self, key: str) -> None:
        with self._lock:
            self._fails.pop(key, None)


throttle = LoginThrottle()


# --- Helper ---------------------------------------------------------------------------------------


def audit(db: Session, actor_id: int | None, action: str, object_type: str, object_id: object, **meta: object) -> None:
    db.add(AuditLog(actor_id=actor_id, action=action, object_type=object_type, object_id=str(object_id), meta=meta))


def memberships_of(db: Session, user_id: int) -> list[Membership]:
    return list(db.scalars(select(Membership).where(Membership.user_id == user_id).order_by(Membership.scope)))


def user_json(user: User, memberships: list[Membership]) -> dict:
    return {
        "id": user.id,
        "display_name": user.display_name,
        "email": user.email,
        "locale": user.locale,
        "timezone": user.timezone,
        "salutation": user.salutation,
        "memberships": [{"scope": m.scope, "role": m.role, "max_level": m.max_level} for m in memberships],
        "mfa_enabled": user.totp_enabled,
        "disabled": user.disabled_at is not None,
    }


def me_json(ctx: AuthContext, settings: AuthSettings) -> dict:
    return {
        "user": user_json(ctx.user, ctx.memberships),
        "mfa_required": mfa_required(ctx.memberships),
        "must_change_password": ctx.user.must_change_password,
        "next": ctx.pending or "ready",
        "csrf_token": crypto.csrf_token(settings.secret_key, ctx.token),
    }


def start_session(db: Session, response: Response, settings: AuthSettings, user: User, mfa_ok: bool) -> AuthContext:
    """Selalu token baru (cegah session fixation). Cookie: HttpOnly, Secure, SameSite=Lax, __Host-."""
    token = crypto.new_session_token()
    t = now()
    session = UserSession(token_hash=crypto.token_hash(token), user_id=user.id, mfa_ok=mfa_ok, created_at=t, last_seen_at=t,
                          expires_at=t + timedelta(hours=settings.session_max_hours))
    db.add(session)
    response.set_cookie(SESSION_COOKIE, token, max_age=settings.session_max_hours * 3600, path="/", secure=True, httponly=True, samesite="lax")
    return AuthContext(user=user, session=session, token=token, memberships=memberships_of(db, user.id))


def revoke_sessions(db: Session, user_id: int, keep: str | None = None) -> None:
    stmt = update(UserSession).where(UserSession.user_id == user_id, UserSession.revoked_at.is_(None))
    if keep:
        stmt = stmt.where(UserSession.token_hash != keep)
    db.execute(stmt.values(revoked_at=now()))


def find_user(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(func.lower(User.email) == email.strip().lower()))


# --- Login & sesi ---------------------------------------------------------------------------------


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: str = Field(max_length=255, pattern=EMAIL_PATTERN)
    password: str = Field(min_length=1, max_length=crypto.MAX_PASSWORD)
    totp_code: str | None = Field(default=None, max_length=10)


INVALID = ApiError(401, "invalid_credentials", "Email atau password salah.")
TOO_MANY = ApiError(429, "too_many_attempts", "Terlalu banyak percobaan gagal. Coba lagi dalam 15 menit.")


@router.post("/auth/login")
def login(body: LoginRequest, request: Request, response: Response, db: Session = Depends(get_db), settings: AuthSettings = Depends(get_settings)) -> dict:
    check_origin(request, settings)
    key = body.email.strip().lower()
    if throttle.blocked(key):
        raise TOO_MANY
    user = find_user(db, key)
    t = now()
    if user is not None and user.locked_until is not None and user.locked_until > t:
        crypto.verify_password(None, body.password)  # waktu respons tetap sama
        raise TOO_MANY

    def failed(reason: str) -> None:
        throttle.fail(key)
        if user is not None:
            count = db.scalar(update(User).where(User.id == user.id).values(failed_logins=User.failed_logins + 1).returning(User.failed_logins))
            if count >= settings.max_failed_logins:
                db.execute(update(User).where(User.id == user.id).values(locked_until=t + timedelta(minutes=settings.lockout_minutes), failed_logins=0))
        audit(db, None, "login_failed", "user", user.id if user else "unknown", reason=reason)
        db.commit()

    if user is None or user.disabled_at is not None or not crypto.verify_password(user.password_hash, body.password):
        failed("password")
        raise INVALID

    if user.totp_enabled:
        if not body.totp_code:
            raise ApiError(401, "mfa_required", "Masukkan kode 6 digit dari aplikasi authenticator.")
        secret = crypto.decrypt_totp_secret(settings.secret_key, user.id, user.totp_secret_enc)
        counter = crypto.verify_totp(secret, body.totp_code, user.totp_last_counter)
        if counter is None:
            failed("totp")
            raise ApiError(401, "invalid_mfa_code", "Kode 2FA salah atau sudah dipakai.")
        user.totp_last_counter = counter

    throttle.reset(key)
    user.failed_logins, user.locked_until, user.last_login_at = 0, None, t
    if crypto.needs_rehash(user.password_hash):
        user.password_hash = crypto.hash_password(body.password)
    memberships = memberships_of(db, user.id)
    ctx = start_session(db, response, settings, user, mfa_ok=user.totp_enabled or not mfa_required(memberships))
    audit(db, user.id, "login", "user", user.id, mfa=user.totp_enabled)
    db.commit()
    return me_json(ctx, settings)


@router.get("/auth/me")
def me(ctx: AuthContext = Depends(current_user_pending_ok), settings: AuthSettings = Depends(get_settings)) -> dict:
    return me_json(ctx, settings)


@router.post("/auth/logout", status_code=204)
def logout(response: Response, ctx: AuthContext = Depends(current_user_pending_ok), db: Session = Depends(get_db)) -> Response:
    ctx.session.revoked_at = now()
    audit(db, ctx.user.id, "logout", "user", ctx.user.id)
    db.commit()
    response.delete_cookie(SESSION_COOKIE, path="/", secure=True, httponly=True, samesite="lax")
    response.status_code = 204
    return response


class PasswordChange(BaseModel):
    model_config = ConfigDict(extra="forbid")
    current_password: str = Field(min_length=1, max_length=crypto.MAX_PASSWORD)
    new_password: str = Field(min_length=1, max_length=crypto.MAX_PASSWORD)


@router.post("/auth/password")
def change_password(body: PasswordChange, response: Response, ctx: AuthContext = Depends(current_user_pending_ok),
                    db: Session = Depends(get_db), settings: AuthSettings = Depends(get_settings)) -> dict:
    user = ctx.user
    if not crypto.verify_password(user.password_hash, body.current_password):
        raise ApiError(400, "invalid_current_password", "Password saat ini salah.")
    if problem := crypto.password_problem(body.new_password, user.email):
        raise ApiError(422, "weak_password", problem)
    if crypto.verify_password(user.password_hash, body.new_password):
        raise ApiError(422, "weak_password", "Password baru harus berbeda dari password lama.")
    user.password_hash, user.must_change_password = crypto.hash_password(body.new_password), False
    # Semua sesi lama (termasuk yang mungkin dicuri) diputus; sesi ini diganti token baru.
    revoke_sessions(db, user.id)
    new = start_session(db, response, settings, user, mfa_ok=ctx.session.mfa_ok)
    audit(db, user.id, "password_changed", "user", user.id)
    db.commit()
    return me_json(new, settings)


# --- 2FA (TOTP) -----------------------------------------------------------------------------------


@router.post("/auth/mfa/setup")
def mfa_setup(ctx: AuthContext = Depends(current_user_pending_ok), db: Session = Depends(get_db), settings: AuthSettings = Depends(get_settings)) -> dict:
    if ctx.user.must_change_password:
        raise ApiError(403, "password_change_required", "Ganti password sementara dulu.")
    if ctx.user.totp_enabled:
        raise ApiError(409, "mfa_already_enabled", "2FA sudah aktif. Reset hanya lewat admin server.")
    secret = crypto.new_totp_secret()
    ctx.user.totp_secret_enc = crypto.encrypt_totp_secret(settings.secret_key, ctx.user.id, secret)
    db.commit()
    return {"secret": secret, "otpauth_uri": crypto.totp_uri(secret, ctx.user.email)}


class MfaConfirm(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: str = Field(min_length=6, max_length=10)


@router.post("/auth/mfa/confirm")
def mfa_confirm(body: MfaConfirm, response: Response, ctx: AuthContext = Depends(current_user_pending_ok),
                db: Session = Depends(get_db), settings: AuthSettings = Depends(get_settings)) -> dict:
    user = ctx.user
    if user.totp_enabled:
        raise ApiError(409, "mfa_already_enabled", "2FA sudah aktif.")
    if user.totp_secret_enc is None:
        raise ApiError(409, "mfa_setup_missing", "Mulai pengaturan 2FA dulu.")
    secret = crypto.decrypt_totp_secret(settings.secret_key, user.id, user.totp_secret_enc)
    counter = crypto.verify_totp(secret, body.code, user.totp_last_counter)
    if counter is None:
        raise ApiError(400, "invalid_mfa_code", "Kode salah. Pastikan jam HP otomatis, lalu coba kode berikutnya.")
    user.totp_enabled, user.totp_last_counter = True, counter
    revoke_sessions(db, user.id)
    new = start_session(db, response, settings, user, mfa_ok=True)
    audit(db, user.id, "mfa_enabled", "user", user.id)
    db.commit()
    return me_json(new, settings)


# --- Manajemen user (owner) -----------------------------------------------------------------------


class MembershipIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    scope: str = Field(max_length=12, pattern=r"^(agency|[A-Z0-9]{2,12})$")
    role: str = Field(pattern="^(" + "|".join(ROLES) + ")$")
    max_level: str = Field(pattern="^(" + "|".join(LEVELS) + ")$")


class UserCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    display_name: str = Field(min_length=1, max_length=120)
    email: str = Field(max_length=255, pattern=EMAIL_PATTERN)
    temporary_password: str = Field(min_length=1, max_length=crypto.MAX_PASSWORD)
    locale: str = Field(default="id", pattern="^(" + "|".join(LOCALES) + ")$")
    timezone: str = Field(default="Asia/Makassar", pattern="^(" + "|".join(TIMEZONES).replace("/", "\\/") + ")$")
    memberships: list[MembershipIn] = Field(min_length=1, max_length=50)


def save_memberships(db: Session, user_id: int, items: list[MembershipIn]) -> None:
    if len({m.scope for m in items}) != len(items):
        raise ApiError(422, "invalid_membership", "Satu scope hanya boleh satu peran.")
    clients = {m.scope for m in items if m.scope != "agency"}
    if clients and len(db.scalars(select(Client.client_code).where(Client.client_code.in_(clients))).all()) != len(clients):
        raise ApiError(422, "invalid_membership", "Klien tidak dikenal.")
    db.query(Membership).filter(Membership.user_id == user_id).delete()
    db.add_all(Membership(user_id=user_id, scope=m.scope, role=m.role, max_level=m.max_level) for m in items)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise ApiError(422, "invalid_membership", "Peran tidak cocok dengan scope atau klien tidak dikenal.") from exc


def ensure_active_owner(db: Session) -> None:
    owners = db.scalar(
        select(func.count()).select_from(Membership).join(User, User.id == Membership.user_id)
        .where(Membership.scope == "agency", Membership.role == "owner", User.disabled_at.is_(None))
    )
    if not owners:
        db.rollback()
        raise ApiError(409, "last_owner", "Harus tetap ada minimal satu owner aktif.")


@router.get("/users")
def list_users(ctx: AuthContext = Depends(require_owner), db: Session = Depends(get_db)) -> dict:
    users = db.scalars(select(User).order_by(User.id)).all()
    return {"users": [user_json(u, memberships_of(db, u.id)) for u in users]}


@router.post("/users", status_code=201)
def create_user(body: UserCreate, ctx: AuthContext = Depends(require_owner), db: Session = Depends(get_db)) -> dict:
    if problem := crypto.password_problem(body.temporary_password, body.email):
        raise ApiError(422, "weak_password", problem)
    if find_user(db, body.email):
        raise ApiError(409, "email_taken", "Email sudah dipakai akun lain.")
    user = User(display_name=body.display_name.strip(), email=body.email.strip(), locale=body.locale, timezone=body.timezone,
                password_hash=crypto.hash_password(body.temporary_password), must_change_password=True)
    db.add(user)
    db.flush()
    save_memberships(db, user.id, body.memberships)
    audit(db, ctx.user.id, "user_created", "user", user.id, memberships=[m.model_dump() for m in body.memberships])
    db.commit()
    return user_json(user, memberships_of(db, user.id))


def target_user(db: Session, user_id: int) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise ApiError(404, "not_found", "User tidak ada.")
    return user


@router.put("/users/{user_id}/memberships")
def set_memberships(user_id: int, body: list[MembershipIn], ctx: AuthContext = Depends(require_owner), db: Session = Depends(get_db)) -> dict:
    user = target_user(db, user_id)
    if not body:
        raise ApiError(422, "invalid_membership", "Minimal satu peran.")
    save_memberships(db, user.id, body)
    ensure_active_owner(db)
    if user.id != ctx.user.id:
        revoke_sessions(db, user.id)  # hak berubah: user login ulang dengan hak baru
    audit(db, ctx.user.id, "membership_changed", "user", user.id, memberships=[m.model_dump() for m in body])
    db.commit()
    return user_json(user, memberships_of(db, user.id))


@router.post("/users/{user_id}/disable")
def disable_user(user_id: int, ctx: AuthContext = Depends(require_owner), db: Session = Depends(get_db)) -> dict:
    user = target_user(db, user_id)
    if user.id == ctx.user.id:
        raise ApiError(409, "cannot_disable_self", "Owner tidak bisa menonaktifkan akunnya sendiri.")
    user.disabled_at = now()
    db.flush()
    ensure_active_owner(db)
    revoke_sessions(db, user.id)
    audit(db, ctx.user.id, "user_disabled", "user", user.id)
    db.commit()
    return user_json(user, memberships_of(db, user.id))


@router.post("/users/{user_id}/enable")
def enable_user(user_id: int, ctx: AuthContext = Depends(require_owner), db: Session = Depends(get_db)) -> dict:
    user = target_user(db, user_id)
    user.disabled_at, user.failed_logins, user.locked_until = None, 0, None
    audit(db, ctx.user.id, "user_enabled", "user", user.id)
    db.commit()
    return user_json(user, memberships_of(db, user.id))


def owner_exists(db: Session) -> bool:
    return bool(db.scalar(select(func.count()).select_from(Membership).where(Membership.scope == "agency", Membership.role == "owner")))


__all__ = ["router", "throttle", "is_owner", "owner_exists"]
