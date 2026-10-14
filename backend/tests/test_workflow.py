"""Workflow request → draft → QA → approval lewat API (kontrak core 0.7.0), ke PostgreSQL sungguhan.

Menguji yang menjadi tanggung jawab API: matriks izin Rule 08, isolasi data per klien, field yang hanya boleh
diisi server, dan bahwa aturan database (migrasi 0004) sampai ke pengguna sebagai kode kontrak.
"""

from __future__ import annotations

import threading
from datetime import date, timedelta

import pytest

pyotp = pytest.importorskip("pyotp")
psycopg = pytest.importorskip("psycopg")

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine, func, select  # noqa: E402
from sqlalchemy.orm import Session, sessionmaker  # noqa: E402

from app.auth import crypto  # noqa: E402
from app.auth.deps import get_db  # noqa: E402
from app.auth.routes import throttle  # noqa: E402
from app.db.models import AuditLog, Client, FactConfirmation, FactSheet, Membership, Request, User  # noqa: E402
from app.main import app  # noqa: E402
from tests.conftest import TempDatabase, admin_url_or_skip, sqlalchemy_url  # noqa: E402

SECRET = "w" * 48
PASSWORD = "kopi-sawah-ubud-2026"
ORIGIN = "http://127.0.0.1:3000"


@pytest.fixture(scope="module")
def engine():
    db = TempDatabase(admin_url_or_skip())
    try:
        db.alembic("upgrade", "head")
        eng = create_engine(sqlalchemy_url(db.app_conninfo))
        with Session(eng) as s, s.begin():
            for code, sim in (("CTH", False), ("CTHB", False), ("CTHSIM", True)):
                s.add(Client(client_code=code, vertical="accommodation", business_type="villa", approver_role="owner", simulation=sim))
        yield eng
        eng.dispose()
    finally:
        db.drop()


@pytest.fixture(scope="module")
def factory(engine):
    # Satu tim per modul (hash Argon2 mahal); setiap test membuat request/draft sendiri sehingga tidak saling ganggu.
    with pytest.MonkeyPatch.context() as mp:
        mp.setenv("CLAU_SECRET_KEY", SECRET)
        throttle._fails.clear()
        make = sessionmaker(bind=engine, expire_on_commit=False)

        def override():
            with make() as s:
                yield s

        app.dependency_overrides[get_db] = override
        yield make
        app.dependency_overrides.clear()


counter = iter(range(100_000))


class Actor:
    """User yang sudah login: .post/.get otomatis membawa header CSRF."""

    def __init__(self, factory, role: str, scope: str = "agency", level: str = "L3") -> None:
        n = next(counter)
        secret = pyotp.random_base32() if role == "owner" else None
        with factory() as s, s.begin():
            user = User(display_name=f"{role} {n}", email=f"wf{n}@contoh.test", password_hash=crypto.hash_password(PASSWORD))
            s.add(user)
            s.flush()
            s.add(Membership(user_id=user.id, scope=scope, role=role, max_level=level))
            if secret:  # 2FA wajib untuk owner
                user.totp_secret_enc = crypto.encrypt_totp_secret(SECRET.encode(), user.id, secret)
                user.totp_enabled = True
        self.id = user.id
        self.http = TestClient(app, base_url="https://testserver", headers={"origin": ORIGIN})
        extra = {"totp_code": pyotp.TOTP(secret).now()} if secret else {}
        assert self.http.post("/auth/login", json={"email": user.email, "password": PASSWORD, **extra}).status_code == 200
        self.csrf = {"x-csrf-token": self.http.get("/auth/me").json()["csrf_token"]}

    def post(self, path: str, body: dict):
        return self.http.post(path, json=body, headers=self.csrf)

    def get(self, path: str, **params):
        return self.http.get(path, params=params)


@pytest.fixture(scope="module")
def team(factory):
    return {
        "owner": Actor(factory, "owner"),
        "lead": Actor(factory, "content_lead"),
        "lead2": Actor(factory, "content_lead"),
        "staff": Actor(factory, "content_staff", level="L1"),
        "approver": Actor(factory, "client_approver", scope="CTH", level="L2"),
        "approver_l1": Actor(factory, "client_approver", scope="CTH", level="L1"),
        "viewer": Actor(factory, "viewer", scope="CTH", level="L1"),
        "other": Actor(factory, "client_approver", scope="CTHB", level="L3"),
    }


def fact_sheet(factory, client="CTH", keys=("pool.private",), approved=True, confirmer=None) -> int:
    with factory() as s, s.begin():
        version = (s.scalar(select(func.max(FactSheet.version)).where(FactSheet.client_code == client)) or 0) + 1
        sheet = FactSheet(client_code=client, version=version, document_ref="workspace://fact-sheet", approved_at=func.now() if approved else None)
        s.add(sheet)
        s.flush()
        for key in keys:
            s.add(FactConfirmation(fact_sheet_id=sheet.id, fact_key=key, decision="confirmed", confirmed_by=confirmer))
        return sheet.id


def new_request(actor: Actor, client="CTH", intent="caption", **extra) -> dict:
    r = actor.post("/requests", {"client_code": client, "intent": intent, "text": "Caption pagi villa", **extra})
    assert r.status_code == 201, r.text
    return r.json()


def new_draft(actor: Actor, request_id: int, claims=(), **extra) -> dict:
    r = actor.post("/drafts", {"request_id": request_id, "content": "Pagi tenang di villa.", "claims": list(claims), **extra})
    assert r.status_code == 201, r.text
    return r.json()


POOL = {"text": "Kolam renang pribadi", "category": "facility", "evidence_label": "CLIENT CONFIRMATION", "fact_key": "pool.private"}


def code(r) -> str:
    return r.json()["error"]["code"]


# --- Alur utuh -----------------------------------------------------------------------------------


def test_full_l2_flow_with_confirmed_facts(factory, team):
    sheet = fact_sheet(factory, confirmer=team["approver"].id)
    req = new_request(team["staff"], intent="reel-script", deadline=str(date.today() + timedelta(days=5)), impact=2, risk=2)
    assert (req["pillar"], req["agent"], req["approval_min"], req["status"]) == (1, "reel-scripter", "L2", "open")
    assert (req["priority"], req["priority_score"], req["requested_by"]) == ("High", 6, team["staff"].id)

    draft = new_draft(team["staff"], req["id"], claims=[POOL], fact_sheet_id=sheet)
    assert (draft["version"], draft["mode"], draft["skill"], draft["created_by"], draft["latest"]) == (1, "NYATA", "draft-reel-script", team["staff"].id, True)
    assert draft["claims"][0]["fact_key"] == "pool.private"

    qa = team["lead"].post("/qa-records", {"draft_id": draft["id"], "gate": "claim-verification", "result": "Pass", "independent": True})
    assert qa.status_code == 201 and qa.json()["reviewer_role"] == "content_lead" and qa.json()["reviewer_id"] == team["lead"].id

    approval = team["approver"].post("/approvals", {"draft_id": draft["id"], "level": "L2", "decision": "Approved"})
    assert approval.status_code == 201, approval.text
    body = approval.json()
    assert (body["approver_role"], body["approver_id"], body["mode"]) == ("client_approver", team["approver"].id, "NYATA")
    assert team["approver"].get(f"/requests/{req['id']}").json()["status"] == "approved"

    with factory() as s:
        actions = s.scalars(select(AuditLog.action).where(AuditLog.object_id.in_([str(req["id"]), str(draft["id"]), str(qa.json()["id"]), str(body["id"])]))).all()
    assert {"request.create", "draft.create", "qa.create", "approval.create"} <= set(actions)


def test_revise_and_reject_update_request_status(team):
    req = new_request(team["staff"])
    draft = new_draft(team["staff"], req["id"])
    assert team["approver"].post("/approvals", {"draft_id": draft["id"], "level": "L1", "decision": "Revise"}).status_code == 201
    assert team["staff"].get(f"/requests/{req['id']}").json()["status"] == "in_progress"
    assert team["approver"].post("/approvals", {"draft_id": draft["id"], "level": "L1", "decision": "Rejected"}).status_code == 201
    assert team["staff"].get(f"/requests/{req['id']}").json()["status"] == "rejected"


# --- Request -------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("days", "impact", "risk", "priority"),
    [(None, 1, 1, "Low"), (10, 1, 1, "Normal"), (1, 3, 3, "Urgent"), (30, 0, 3, "Urgent"), (5, 2, 2, "High")],
)
def test_priority_engine(team, days, impact, risk, priority):
    deadline = None if days is None else str(date.today() + timedelta(days=days))
    req = new_request(team["staff"], deadline=deadline, impact=impact, risk=risk)
    assert req["priority"] == priority


def test_request_validation(team):
    staff = team["staff"]
    assert code(staff.post("/requests", {"client_code": "CTH", "intent": "nyanyi", "text": "x"})) == "unknown_intent"
    assert code(staff.post("/requests", {"client_code": "NOPE", "intent": "caption", "text": "x"})) == "client_not_found"
    assert staff.post("/requests", {"client_code": "CTH", "intent": "caption", "text": "x", "risk": 4}).status_code == 422
    assert staff.post("/requests", {"client_code": "CTH", "intent": "caption", "text": ""}).status_code == 422


@pytest.mark.parametrize(
    ("path", "field", "value"),
    [
        ("/requests", "requested_by_role", "owner"), ("/requests", "pillar", 1), ("/requests", "priority", "Urgent"),
        ("/drafts", "version", 1), ("/drafts", "mode", "NYATA"), ("/drafts", "created_by", 1),
        ("/qa-records", "reviewer_role", "owner"), ("/qa-records", "reviewer_id", 1),
        ("/approvals", "approver_role", "client_approver"), ("/approvals", "approver_id", 1), ("/approvals", "mode", "NYATA"),
    ],
)
def test_server_owned_fields_are_rejected(team, path, field, value):
    bodies = {
        "/requests": {"client_code": "CTH", "intent": "caption", "text": "x"},
        "/drafts": {"request_id": 1, "content": "x"},
        "/qa-records": {"draft_id": 1, "gate": "content-review", "result": "Pass", "independent": False},
        "/approvals": {"draft_id": 1, "level": "L1", "decision": "Revise"},
    }
    r = team["lead"].post(path, {**bodies[path], field: value})
    assert r.status_code == 422 and code(r) == "validation_error"


def test_planned_intent_request_ok_but_no_draft(team):
    req = new_request(team["staff"], intent="inquiry-reply")
    assert req["pillar"] == 2
    r = team["staff"].post("/drafts", {"request_id": req["id"], "content": "x"})
    assert r.status_code == 409 and code(r) == "intent_not_active"


# --- Matriks izin (Rule 08) -----------------------------------------------------------------------


@pytest.mark.parametrize(
    ("who", "status"),
    [("owner", 201), ("lead", 201), ("staff", 201), ("approver", 201), ("viewer", 403), ("other", 403)],
)
def test_who_can_create_request_for_cth(team, who, status):
    r = team[who].post("/requests", {"client_code": "CTH", "intent": "caption", "text": "x"})
    assert r.status_code == status


@pytest.mark.parametrize(("who", "status"), [("owner", 201), ("lead", 201), ("staff", 201), ("approver", 403), ("viewer", 403), ("other", 404)])
def test_who_can_write_draft(team, who, status):
    req = new_request(team["staff"])
    assert team[who].post("/drafts", {"request_id": req["id"], "content": "x"}).status_code == status


@pytest.mark.parametrize(
    ("who", "independent", "status"),
    [("lead2", True, 201), ("owner", True, 201), ("staff", False, 201), ("staff", True, 403),
     ("approver", False, 403), ("viewer", False, 403), ("other", False, 404)],
)
def test_who_can_record_qa(team, who, independent, status):
    draft = new_draft(team["lead"], new_request(team["lead"])["id"])
    r = team[who].post("/qa-records", {"draft_id": draft["id"], "gate": "claim-verification", "result": "Pass", "independent": independent})
    assert r.status_code == status, r.text
    if status == 403 and who == "staff":
        assert code(r) == "independent_review_not_allowed"


@pytest.mark.parametrize(("who", "status"), [("owner", 201), ("lead2", 201), ("approver", 201), ("approver_l1", 201), ("staff", 403), ("viewer", 403), ("other", 404)])
def test_who_can_approve_l1(team, who, status):
    draft = new_draft(team["lead"], new_request(team["lead"])["id"])
    assert team[who].post("/approvals", {"draft_id": draft["id"], "level": "L1", "decision": "Approved"}).status_code == status


def test_level_above_max_level_is_refused(team):
    draft = new_draft(team["lead"], new_request(team["lead"], intent="reel-script")["id"])
    r = team["approver_l1"].post("/approvals", {"draft_id": draft["id"], "level": "L2", "decision": "Approved"})
    assert r.status_code == 403 and code(r) == "level_not_allowed"


def test_reviewer_cannot_independently_review_own_draft(team):
    draft = new_draft(team["lead"], new_request(team["lead"])["id"])
    r = team["lead"].post("/qa-records", {"draft_id": draft["id"], "gate": "claim-verification", "result": "Pass", "independent": True})
    assert r.status_code == 409 and code(r) == "qa_reviewer_is_author"


# --- Isolasi klien (IDOR) -------------------------------------------------------------------------


def test_other_client_cannot_see_or_touch_cth_data(team):
    req = new_request(team["staff"])
    draft = new_draft(team["staff"], req["id"])
    qa = team["lead"].post("/qa-records", {"draft_id": draft["id"], "gate": "content-review", "result": "Pass", "independent": True}).json()
    approval = team["approver"].post("/approvals", {"draft_id": draft["id"], "level": "L1", "decision": "Revise"}).json()
    other = team["other"]
    for path in (f"/requests/{req['id']}", f"/drafts/{draft['id']}", f"/qa-records/{qa['id']}", f"/approvals/{approval['id']}"):
        r = other.get(path)
        assert r.status_code == 404 and code(r) == "not_found", path
    assert other.get("/requests", client_code="CTH").status_code == 403
    assert other.get("/drafts", client_code="CTH").status_code == 403
    for path, key in (("/requests", "client_code"), ("/drafts", "client_code")):
        assert all(item[key] == "CTHB" for item in other.get(path).json()["items"])
    assert other.get("/qa-records", draft_id=draft["id"]).json()["items"] == []
    assert other.get("/approvals", draft_id=draft["id"]).json()["items"] == []
    # Viewer klien CTH boleh membaca, tidak boleh menulis.
    assert team["viewer"].get(f"/drafts/{draft['id']}").status_code == 200


def test_draft_cannot_use_other_clients_fact_sheet(factory, team):
    other_sheet = fact_sheet(factory, client="CTHB", confirmer=team["other"].id)
    req = new_request(team["staff"])
    r = team["staff"].post("/drafts", {"request_id": req["id"], "content": "x", "fact_sheet_id": other_sheet})
    assert r.status_code == 409 and code(r) == "draft_client_mismatch"
    r = team["staff"].post("/drafts", {"request_id": req["id"], "content": "x", "brief_id": "CTHB-202610-01"})
    assert r.status_code == 409 and code(r) == "draft_client_mismatch"


# --- Aturan database sampai ke pengguna -----------------------------------------------------------


def test_claim_rules(team):
    req = new_request(team["staff"])
    r = team["staff"].post("/drafts", {"request_id": req["id"], "content": "x", "claims": [{**POOL, "fact_key": None}]})
    assert r.status_code == 422 and code(r) == "claim_fact_key_required"
    r = team["staff"].post("/drafts", {"request_id": req["id"], "content": "x", "claims": [{**POOL, "evidence_label": "DATA FINAL"}]})
    assert r.status_code == 422 and code(r) == "claim_source_required"
    ok = new_draft(team["staff"], req["id"], claims=[{"text": "Suasana tenang", "category": "experience", "evidence_label": "ASSUMPTION"}])
    assert ok["claims"][0]["fact_key"] is None


def test_unconfirmed_facts_block_approval(factory, team):
    sheet = fact_sheet(factory, keys=("pool.heated",), confirmer=team["approver"].id)
    draft = new_draft(team["staff"], new_request(team["staff"])["id"], claims=[POOL], fact_sheet_id=sheet)
    r = team["approver"].post("/approvals", {"draft_id": draft["id"], "level": "L1", "decision": "Approved"})
    assert r.status_code == 409 and code(r) == "facts_unconfirmed"


def test_only_latest_version_and_not_by_author(team):
    req = new_request(team["lead"])
    v1 = new_draft(team["lead"], req["id"])
    v2 = new_draft(team["staff"], req["id"])
    assert (v1["version"], v2["version"]) == (1, 2)
    assert team["staff"].get(f"/drafts/{v1['id']}").json()["latest"] is False
    r = team["approver"].post("/approvals", {"draft_id": v1["id"], "level": "L1", "decision": "Approved"})
    assert r.status_code == 409 and code(r) == "approval_version_mismatch"
    v3 = new_draft(team["lead"], req["id"])
    r = team["lead"].post("/approvals", {"draft_id": v3["id"], "level": "L1", "decision": "Approved"})
    assert r.status_code == 409 and code(r) == "approval_by_author"


def test_agency_l2_needs_written_client_evidence_and_minimum_level(team):
    draft = new_draft(team["staff"], new_request(team["staff"], intent="reel-script")["id"])
    r = team["approver"].post("/approvals", {"draft_id": draft["id"], "level": "L1", "decision": "Approved"})
    assert r.status_code == 409 and code(r) == "approval_level_too_low"
    assert team["lead"].post("/qa-records", {"draft_id": draft["id"], "gate": "claim-verification", "result": "Pass", "independent": True}).status_code == 201
    r = team["lead"].post("/approvals", {"draft_id": draft["id"], "level": "L2", "decision": "Approved", "channel_ref": "   "})
    assert r.status_code == 409 and code(r) == "approval_needs_written_evidence"
    r = team["lead"].post("/approvals", {"draft_id": draft["id"], "level": "L2", "decision": "Approved", "channel_ref": "email://arsip/approval-cth-2026-10-14"})
    assert r.status_code == 201 and r.json()["channel_ref"] == "email://arsip/approval-cth-2026-10-14"


def test_simulation_client_is_never_approved(factory, team):
    sim_approver = Actor(factory, "client_approver", scope="CTHSIM", level="L3")
    draft = new_draft(team["staff"], new_request(team["staff"], client="CTHSIM")["id"])
    assert draft["mode"] == "SIMULASI"
    r = sim_approver.post("/approvals", {"draft_id": draft["id"], "level": "L1", "decision": "Approved"})
    assert r.status_code == 409 and code(r) == "simulasi_not_approved"
    assert sim_approver.post("/approvals", {"draft_id": draft["id"], "level": "L1", "decision": "Revise"}).json()["mode"] == "SIMULASI"


# --- Keamanan & operasional -----------------------------------------------------------------------


def test_writes_need_csrf_and_reads_need_login(team):
    staff = team["staff"]
    r = staff.http.post("/requests", json={"client_code": "CTH", "intent": "caption", "text": "x"})
    assert r.status_code == 403 and code(r) == "csrf_failed"
    anon = TestClient(app, base_url="https://testserver")
    assert anon.get("/requests").status_code == 401
    r = staff.http.post("/requests", json={"client_code": "CTH", "intent": "caption", "text": "x"}, headers={**staff.csrf, "origin": "https://evil.example"})
    assert r.status_code == 403 and code(r) == "origin_not_allowed"


def test_concurrent_drafts_get_distinct_versions(team):
    req = new_request(team["staff"])
    writers = [team["staff"], team["lead"], team["lead2"], team["owner"]]
    results: list = []

    def write(actor):
        results.append(actor.post("/drafts", {"request_id": req["id"], "content": "paralel"}))

    threads = [threading.Thread(target=write, args=(a,)) for a in writers]
    for t in threads:
        t.start()
    for t in threads:
        t.join(10)
    assert all(r.status_code == 201 for r in results), [r.text for r in results]
    assert sorted(r.json()["version"] for r in results) == [1, 2, 3, 4]


def test_pagination(team):
    for _ in range(3):
        new_request(team["approver"])
    page = team["approver"].get("/requests", limit=2, offset=0).json()
    assert len(page["items"]) == 2 and page["total"] >= 3 and (page["limit"], page["offset"]) == (2, 0)
    assert team["approver"].get("/requests", limit=101).status_code == 422
    assert team["approver"].get("/requests", status="selesai").status_code == 422


def test_request_text_is_not_written_to_audit_log(factory, team):
    req = new_request(team["staff"], text="Rahasia: harga promo 999rb")
    with factory() as s:
        meta = s.scalar(select(AuditLog.meta).where(AuditLog.action == "request.create", AuditLog.object_id == str(req["id"])))
        stored = s.get(Request, req["id"])
    assert "999" not in str(meta) and stored.requested_by_role == "content_staff"
