"""Login, sesi, CSRF, 2FA, dan hak akses (docs/security.md § 6), diuji ke PostgreSQL sungguhan."""

from __future__ import annotations

import time
from datetime import timedelta

import pytest

pyotp = pytest.importorskip("pyotp")
psycopg = pytest.importorskip("psycopg")

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine, func, select, update  # noqa: E402
from sqlalchemy.orm import Session, sessionmaker  # noqa: E402

from app.auth import crypto  # noqa: E402
from app.auth.config import SESSION_COOKIE  # noqa: E402
from app.auth.deps import get_db, now  # noqa: E402
from app.auth.routes import throttle  # noqa: E402
from app.db.models import AuditLog, Client, Membership, User, UserSession  # noqa: E402
from app.main import app  # noqa: E402
from tests.conftest import TempDatabase, admin_url_or_skip, sqlalchemy_url  # noqa: E402

SECRET = "k" * 48
PASSWORD = "kopi-sawah-ubud-2026"
ORIGIN = "http://127.0.0.1:3000"


@pytest.fixture(scope="module")
def engine():
    db = TempDatabase(admin_url_or_skip())
    try:
        db.alembic("upgrade", "head")
        eng = create_engine(sqlalchemy_url(db.app_conninfo))
        with Session(eng) as s, s.begin():
            s.add(Client(client_code="CTH", vertical="accommodation", business_type="villa", approver_role="owner"))
        yield eng
        eng.dispose()
    finally:
        db.drop()


@pytest.fixture()
def factory(engine, monkeypatch):
    monkeypatch.setenv("CLAU_SECRET_KEY", SECRET)
    throttle._fails.clear()
    make = sessionmaker(bind=engine, expire_on_commit=False)

    def override():
        with make() as s:
            yield s

    app.dependency_overrides[get_db] = override
    yield make
    app.dependency_overrides.clear()


def client() -> TestClient:
    return TestClient(app, base_url="https://testserver", headers={"origin": ORIGIN})


counter = iter(range(10_000))


def make_user(factory, role="content_staff", scope="agency", level="L2", password=PASSWORD, mfa_secret=None, must_change=False) -> User:
    n = next(counter)
    with factory() as s, s.begin():
        user = User(display_name=f"User {n}", email=f"user{n}@contoh.test", password_hash=crypto.hash_password(password), must_change_password=must_change)
        s.add(user)
        s.flush()
        s.add(Membership(user_id=user.id, scope=scope, role=role, max_level=level))
        if mfa_secret:
            user.totp_secret_enc = crypto.encrypt_totp_secret(SECRET.encode(), user.id, mfa_secret)
            user.totp_enabled = True
    return user


def login(c: TestClient, user: User, password=PASSWORD, **extra):
    return c.post("/auth/login", json={"email": user.email, "password": password, **extra})


def csrf(c: TestClient) -> dict:
    return {"x-csrf-token": c.get("/auth/me").json()["csrf_token"]}


def ready_owner(factory) -> tuple[TestClient, User, str]:
    secret = pyotp.random_base32()
    owner = make_user(factory, role="owner", level="L3", mfa_secret=secret)
    c = client()
    assert login(c, owner, totp_code=pyotp.TOTP(secret).now()).status_code == 200
    return c, owner, secret


# --- Login & cookie -------------------------------------------------------------------------------


def test_login_sets_hardened_cookie_and_me_works(factory):
    user = make_user(factory)
    c = client()
    r = login(c, user)
    assert r.status_code == 200 and r.json()["next"] == "ready"
    cookie = r.headers["set-cookie"]
    assert cookie.startswith(f"{SESSION_COOKIE}=")
    for flag in ("HttpOnly", "Secure", "SameSite=lax", "Path=/"):
        assert flag.lower() in cookie.lower()
    assert "domain" not in cookie.lower()
    me = c.get("/auth/me").json()
    assert me["user"]["email"] == user.email and me["csrf_token"] and "password_hash" not in str(me)


def test_session_token_is_stored_hashed(factory):
    user = make_user(factory)
    c = client()
    login(c, user)
    token = c.cookies[SESSION_COOKIE]
    with factory() as s:
        hashes = s.scalars(select(UserSession.token_hash).where(UserSession.user_id == user.id)).all()
    assert hashes == [crypto.token_hash(token)] and token not in hashes


def test_wrong_password_and_unknown_email_look_the_same(factory):
    user = make_user(factory)
    wrong = login(client(), user, password="salah-sekali-123")
    unknown = client().post("/auth/login", json={"email": "tidak-ada@contoh.test", "password": "apa-saja-123456"})
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json() == unknown.json() == {"error": {"code": "invalid_credentials", "message": "Email atau password salah."}}


def test_account_locks_after_five_failures(factory):
    user = make_user(factory)
    for _ in range(5):
        assert login(client(), user, password="salah-sekali-123").status_code == 401
    throttle._fails.clear()  # buktikan kunci di database, bukan hanya di memori
    assert login(client(), user).status_code == 429
    with factory() as s:
        assert s.get(User, user.id).locked_until > now()
        fails = s.scalar(select(func.count()).select_from(AuditLog).where(AuditLog.action == "login_failed", AuditLog.object_id == str(user.id)))
    assert fails == 5


def test_unknown_email_is_throttled_too(factory):
    body = {"email": "penyerang@contoh.test", "password": "tebakan-panjang-1"}
    codes = [client().post("/auth/login", json=body).status_code for _ in range(6)]
    assert codes == [401] * 5 + [429]


def test_disabled_user_cannot_login(factory):
    user = make_user(factory)
    with factory() as s, s.begin():
        s.get(User, user.id).disabled_at = now()
    assert login(client(), user).status_code == 401


# --- CSRF, Origin, logout, kedaluwarsa -------------------------------------------------------------


def test_mutations_need_csrf_token(factory):
    user = make_user(factory)
    c = client()
    login(c, user)
    assert c.post("/auth/logout").json()["error"]["code"] == "csrf_failed"
    assert c.post("/auth/logout", headers={"x-csrf-token": "palsu"}).status_code == 403
    assert c.post("/auth/logout", headers=csrf(c)).status_code == 204
    assert c.get("/auth/me").status_code == 401


@pytest.mark.parametrize("headers", [{"origin": "https://evil.example"}, {"sec-fetch-site": "cross-site"}])
def test_cross_site_requests_rejected(factory, headers):
    user = make_user(factory)
    c = TestClient(app, base_url="https://testserver")
    r = c.post("/auth/login", json={"email": user.email, "password": PASSWORD}, headers=headers)
    assert r.status_code == 403 and r.json()["error"]["code"] == "origin_not_allowed"


def test_idle_session_expires(factory):
    user = make_user(factory)
    c = client()
    login(c, user)
    with factory() as s, s.begin():
        s.execute(update(UserSession).where(UserSession.user_id == user.id).values(last_seen_at=now() - timedelta(hours=3)))
    assert c.get("/auth/me").status_code == 401


def test_no_session_is_unauthenticated(factory):
    assert client().get("/auth/me").json()["error"]["code"] == "unauthenticated"


# --- 2FA -------------------------------------------------------------------------------------------


def test_owner_must_enable_mfa_before_anything_else(factory):
    owner = make_user(factory, role="owner", level="L3")
    c = client()
    assert login(c, owner).json()["next"] == "mfa_setup"
    assert c.get("/users").json()["error"]["code"] == "mfa_setup_required"
    old_token = c.cookies[SESSION_COOKIE]
    setup = c.post("/auth/mfa/setup", headers=csrf(c)).json()
    assert setup["otpauth_uri"].startswith("otpauth://totp/CLAU%20AI:")
    assert c.post("/auth/mfa/confirm", json={"code": "000000"}, headers=csrf(c)).status_code == 400
    r = c.post("/auth/mfa/confirm", json={"code": pyotp.TOTP(setup["secret"]).now()}, headers=csrf(c))
    assert r.status_code == 200 and r.json()["next"] == "ready"
    assert c.cookies[SESSION_COOKIE] != old_token, "token sesi wajib diganti setelah 2FA aktif"
    assert c.get("/users").status_code == 200
    stale = client()
    stale.cookies.set(SESSION_COOKIE, old_token)
    assert stale.get("/auth/me").status_code == 401


def test_totp_login_rejects_missing_wrong_and_replayed_codes(factory):
    secret = pyotp.random_base32()
    owner = make_user(factory, role="owner", level="L3", mfa_secret=secret)
    assert login(client(), owner).json()["error"]["code"] == "mfa_required"
    assert login(client(), owner, totp_code="123456").json()["error"]["code"] == "invalid_mfa_code"
    code = pyotp.TOTP(secret).now()
    assert login(client(), owner, totp_code=code).status_code == 200
    assert login(client(), owner, totp_code=code).json()["error"]["code"] == "invalid_mfa_code"


def test_totp_secret_is_encrypted_and_bound_to_user(factory):
    secret = pyotp.random_base32()
    user = make_user(factory, mfa_secret=secret)
    with factory() as s:
        blob = s.get(User, user.id).totp_secret_enc
    assert secret.encode() not in blob
    assert crypto.decrypt_totp_secret(SECRET.encode(), user.id, blob) == secret
    with pytest.raises(Exception):
        crypto.decrypt_totp_secret(SECRET.encode(), user.id + 1, blob)


def test_verify_totp_window_and_replay():
    secret = pyotp.random_base32()
    t = time.time()
    totp = pyotp.TOTP(secret)
    counter = crypto.verify_totp(secret, totp.at(t), None, now=t)
    assert counter is not None
    assert crypto.verify_totp(secret, totp.at(t - 30), None, now=t) == counter - 1
    assert crypto.verify_totp(secret, totp.at(t - 90), None, now=t) is None
    assert crypto.verify_totp(secret, totp.at(t), counter, now=t) is None
    assert crypto.verify_totp(secret, "12a456", None, now=t) is None


# --- Password -------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("password", "ok"),
    [("pendek", False), ("aaaaaaaaaaaaaaaa", False), ("budi.santoso-2026", False), ("kopi-sawah-ubud-2026", True), ("x" * 129, False)],
)
def test_password_policy(password, ok):
    assert (crypto.password_problem(password, "budi.santoso@contoh.test") is None) is ok


def test_temporary_password_must_be_changed(factory):
    c, owner, _ = ready_owner(factory)
    body = {"display_name": "Staf Baru", "email": "staf.baru@contoh.test", "temporary_password": "sementara-panjang-1",
            "memberships": [{"scope": "agency", "role": "content_staff", "max_level": "L1"}]}
    assert c.post("/users", json=body, headers=csrf(c)).status_code == 201
    staff = client()
    r = staff.post("/auth/login", json={"email": body["email"], "password": body["temporary_password"]})
    assert r.json()["next"] == "password_change"
    assert staff.post("/auth/mfa/setup", headers=csrf(staff)).json()["error"]["code"] == "password_change_required"
    weak = staff.post("/auth/password", json={"current_password": body["temporary_password"], "new_password": "pendek"}, headers=csrf(staff))
    assert weak.status_code == 422
    other = client()
    other.post("/auth/login", json={"email": body["email"], "password": body["temporary_password"]})
    r = staff.post("/auth/password", json={"current_password": body["temporary_password"], "new_password": "kebun-teh-bedugul-9"}, headers=csrf(staff))
    assert r.status_code == 200 and r.json()["next"] == "ready"
    assert staff.get("/auth/me").status_code == 200
    assert other.get("/auth/me").status_code == 401, "ganti password wajib memutus sesi lain"


# --- Hak akses & manajemen user -------------------------------------------------------------------


def test_non_owner_cannot_manage_users(factory):
    user = make_user(factory, role="content_lead")
    c = client()
    login(c, user)
    assert c.get("/users").json()["error"]["code"] == "forbidden"
    assert c.post("/users", json={}, headers=csrf(c)).status_code in (403, 422)


@pytest.mark.parametrize(
    "memberships",
    [
        [{"scope": "agency", "role": "client_approver", "max_level": "L2"}],
        [{"scope": "CTH", "role": "owner", "max_level": "L3"}],
        [{"scope": "XYZ", "role": "client_approver", "max_level": "L2"}],
        [{"scope": "CTH", "role": "viewer", "max_level": "L1"}, {"scope": "CTH", "role": "client_approver", "max_level": "L2"}],
    ],
)
def test_invalid_memberships_rejected(factory, memberships):
    c, _, _ = ready_owner(factory)
    body = {"display_name": "X", "email": f"x{next(counter)}@contoh.test", "temporary_password": "sementara-panjang-1", "memberships": memberships}
    r = c.post("/users", json=body, headers=csrf(c))
    assert r.status_code == 422 and r.json()["error"]["code"] == "invalid_membership"


def test_owner_cannot_remove_last_owner_or_disable_self(factory):
    with factory() as s, s.begin():
        # Hanya owner dari test ini yang aktif, supaya aturan "minimal satu owner" teruji.
        s.execute(update(User).where(User.id.in_(select(Membership.user_id).where(Membership.role == "owner"))).values(disabled_at=now()))
    c, owner, _ = ready_owner(factory)
    demote = c.put(f"/users/{owner.id}/memberships", json=[{"scope": "agency", "role": "content_lead", "max_level": "L3"}], headers=csrf(c))
    assert demote.status_code == 409 and demote.json()["error"]["code"] == "last_owner"
    assert c.post(f"/users/{owner.id}/disable", headers=csrf(c)).json()["error"]["code"] == "cannot_disable_self"


def test_disabling_user_ends_their_sessions(factory):
    c, _, _ = ready_owner(factory)
    user = make_user(factory)
    victim = client()
    login(victim, user)
    assert c.post(f"/users/{user.id}/disable", headers=csrf(c)).status_code == 200
    assert victim.get("/auth/me").status_code == 401
    assert c.post(f"/users/{user.id}/enable", headers=csrf(c)).json()["disabled"] is False


def test_changed_memberships_end_target_sessions_and_are_audited(factory):
    c, owner, _ = ready_owner(factory)
    user = make_user(factory)
    other = client()
    login(other, user)
    r = c.put(f"/users/{user.id}/memberships", json=[{"scope": "CTH", "role": "client_approver", "max_level": "L2"}], headers=csrf(c))
    assert r.status_code == 200 and r.json()["memberships"] == [{"scope": "CTH", "role": "client_approver", "max_level": "L2"}]
    assert other.get("/auth/me").status_code == 401
    with factory() as s:
        actions = s.scalars(select(AuditLog.action).where(AuditLog.actor_id == owner.id)).all()
    assert "membership_changed" in actions


def test_access_rules_for_client_scope():
    from app.auth.access import can_access_client, can_approve, visible_client_codes

    approver = [Membership(scope="CTH", role="client_approver", max_level="L2")]
    staff = [Membership(scope="agency", role="content_staff", max_level="L1")]
    assert visible_client_codes(approver) == {"CTH"} and visible_client_codes(staff) is None
    assert can_access_client(approver, "CTH") and not can_access_client(approver, "LAIN")
    assert can_approve(approver, "CTH", "L2") and not can_approve(approver, "CTH", "L3")
    assert not can_approve(approver, "LAIN", "L1")
    assert can_approve(staff, "LAIN", "L1") and not can_approve(staff, "LAIN", "L2")


# --- Fail closed & CLI ----------------------------------------------------------------------------


def test_missing_secret_key_disables_login(factory, monkeypatch):
    monkeypatch.setenv("CLAU_SECRET_KEY", "pendek")
    r = client().post("/auth/login", json={"email": "a@contoh.test", "password": "apa-saja-123456"})
    assert r.status_code == 503 and r.json()["error"]["code"] == "auth_unavailable"


def test_missing_database_is_503(monkeypatch):
    from app.db.session import get_engine

    monkeypatch.setenv("CLAU_SECRET_KEY", SECRET)
    monkeypatch.delenv("CLAU_DATABASE_URL", raising=False)
    get_engine.cache_clear()
    app.dependency_overrides.clear()
    r = client().post("/auth/login", json={"email": "a@contoh.test", "password": "apa-saja-123456"})
    assert r.status_code == 503 and r.json()["error"]["code"] == "database_unavailable"


def test_cli_creates_single_owner():
    from app.auth.cli import create_owner

    db = TempDatabase(admin_url_or_skip())
    try:
        db.alembic("upgrade", "head")
        eng = create_engine(sqlalchemy_url(db.app_conninfo))
        with Session(eng) as s, s.begin():
            user = create_owner(s, "pemilik@contoh.test", "Pemilik", PASSWORD)
            assert s.scalar(select(Membership.role).where(Membership.user_id == user.id)) == "owner"
        with Session(eng) as s, s.begin(), pytest.raises(SystemExit):
            create_owner(s, "kedua@contoh.test", "Kedua", PASSWORD)
        eng.dispose()
    finally:
        db.drop()
