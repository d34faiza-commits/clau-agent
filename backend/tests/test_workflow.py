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
from app.db.models import AuditLog, Brief, Client, Fact, FactConfirmation, FactSheet, Membership, Request, User  # noqa: E402
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
        secret = pyotp.random_base32() if role in ("owner", "content_lead") else None
        with factory() as s, s.begin():
            user = User(display_name=f"{role} {n}", email=f"wf{n}@contoh.test", password_hash=crypto.hash_password(PASSWORD))
            s.add(user)
            s.flush()
            s.add(Membership(user_id=user.id, scope=scope, role=role, max_level=level))
            if secret:  # 2FA wajib untuk owner & content_lead
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


def fact_sheet(factory, client="CTH", keys=("facility.pool-private",), approved=True, confirmer=None) -> int:
    """Fact sheet lewat alur migrasi 0005 (langsung ke database): fakta → jawaban approver klien → disetujui."""
    with factory() as s, s.begin():
        version = (s.scalar(select(func.max(FactSheet.version)).where(FactSheet.client_code == client)) or 0) + 1
        sheet = FactSheet(client_code=client, version=version, document_ref="workspace://fact-sheet")
        s.add(sheet)
        s.flush()
        for key in keys:
            s.add(Fact(fact_sheet_id=sheet.id, fact_key=key, category=key.split(".", 1)[0], label=key, value="ya"))
            s.flush()
            s.add(FactConfirmation(fact_sheet_id=sheet.id, fact_key=key, decision="confirmed", confirmed_by=confirmer, confirmed_by_role="client_approver"))
            s.flush()
        if approved:
            sheet.approved_at, sheet.approved_by, sheet.approved_by_role = func.now(), confirmer, "client_approver"
        return sheet.id


def new_request(actor: Actor, client="CTH", intent="caption", **extra) -> dict:
    r = actor.post("/requests", {"client_code": client, "intent": intent, "text": "Caption pagi villa", **extra})
    assert r.status_code == 201, r.text
    return r.json()


def new_draft(actor: Actor, request_id: int, claims=(), **extra) -> dict:
    r = actor.post("/drafts", {"content_flags": [], "request_id": request_id, "content": "Pagi tenang di villa.", "claims": list(claims), **extra})
    assert r.status_code == 201, r.text
    return r.json()


POOL = {"text": "Kolam renang pribadi", "category": "facility", "evidence_label": "CLIENT CONFIRMATION", "fact_key": "facility.pool-private"}
# Bukti tertulis klien yang dicatat agency (rule 08): link ke email/pesan yang diarsipkan.
EVIDENCE = {"channel_ref": "https://mail.contoh.test/arsip/approval-cth"}


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
    assert draft["claims"][0]["fact_key"] == "facility.pool-private"

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
    r = team["staff"].post("/drafts", {"content_flags": [], "request_id": req["id"], "content": "x"})
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
    assert team[who].post("/drafts", {"content_flags": [], "request_id": req["id"], "content": "x"}).status_code == status


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


@pytest.mark.parametrize(
    ("who", "evidence", "status"),
    [("owner", True, 201), ("lead2", True, 201), ("owner", False, 409), ("lead2", False, 409), ("approver", False, 201),
     ("approver_l1", False, 201), ("staff", True, 403), ("viewer", True, 403), ("other", True, 404)],
)
def test_who_can_approve_l1(team, who, evidence, status):
    """Rule 08: persetujuan dari klien. Agency hanya mencatat persetujuan tertulis klien (bukti wajib), juga untuk L1."""
    draft = new_draft(team["lead"], new_request(team["lead"])["id"])
    r = team[who].post("/approvals", {"draft_id": draft["id"], "level": "L1", "decision": "Approved", **(EVIDENCE if evidence else {})})
    assert r.status_code == status, r.text
    if status == 409:
        assert code(r) == "approval_needs_written_evidence"


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
    new_request(team["other"], client="CTHB")  # data milik CTHB sendiri, agar list tidak kosong
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
    items = other.get("/requests").json()["items"]
    assert items and {item["client_code"] for item in items} == {"CTHB"}
    assert all(item["client_code"] == "CTHB" for item in other.get("/drafts").json()["items"])
    assert other.get("/qa-records", draft_id=draft["id"]).json()["items"] == []
    assert other.get("/approvals", draft_id=draft["id"]).json()["items"] == []
    # Viewer klien CTH boleh membaca, tidak boleh menulis.
    assert team["viewer"].get(f"/drafts/{draft['id']}").status_code == 200


def test_draft_cannot_use_other_clients_fact_sheet(factory, team):
    other_sheet = fact_sheet(factory, client="CTHB", keys=(), approved=False, confirmer=team["other"].id)
    with factory() as s, s.begin():
        if s.get(Brief, "CTHB-202610-01") is None:
            s.add(Brief(brief_id="CTHB-202610-01", client_code="CTHB", schema_version="1.4", payload={"x": 1}))
    req = new_request(team["staff"])
    r = team["staff"].post("/drafts", {"content_flags": [], "request_id": req["id"], "content": "x", "fact_sheet_id": other_sheet})
    assert r.status_code == 409 and code(r) == "draft_client_mismatch"
    r = team["staff"].post("/drafts", {"content_flags": [], "request_id": req["id"], "content": "x", "brief_id": "CTHB-202610-01"})
    assert r.status_code == 409 and code(r) == "draft_client_mismatch"


# --- Aturan database sampai ke pengguna -----------------------------------------------------------


def test_claim_rules(team):
    req = new_request(team["staff"])
    r = team["staff"].post("/drafts", {"content_flags": [], "request_id": req["id"], "content": "x", "claims": [{**POOL, "fact_key": None}]})
    assert r.status_code == 422 and code(r) == "claim_fact_key_required"
    r = team["staff"].post("/drafts", {"content_flags": [], "request_id": req["id"], "content": "x", "claims": [{**POOL, "evidence_label": "DATA FINAL"}]})
    assert r.status_code == 422 and code(r) == "claim_source_required"
    ok = new_draft(team["staff"], req["id"], claims=[{"text": "Suasana tenang", "category": "experience", "evidence_label": "ASSUMPTION"}])
    assert ok["claims"][0]["fact_key"] is None


def test_unconfirmed_facts_block_approval(factory, team):
    sheet = fact_sheet(factory, keys=("facility.pool-heated",), confirmer=team["approver"].id)
    draft = new_draft(team["staff"], new_request(team["staff"])["id"], claims=[POOL], fact_sheet_id=sheet)
    # Klaim fakta menaikkan level minimum caption (L1) ke L2 (rule 08).
    r = team["approver"].post("/approvals", {"draft_id": draft["id"], "level": "L1", "decision": "Approved"})
    assert r.status_code == 409 and code(r) == "approval_level_too_low"
    assert team["lead"].post("/qa-records", {"draft_id": draft["id"], "gate": "claim-verification", "result": "Pass", "independent": True}).status_code == 201
    r = team["approver"].post("/approvals", {"draft_id": draft["id"], "level": "L2", "decision": "Approved"})
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
    for decision in ("Approved", "Revise", "Rejected"):  # pembuat tidak memutuskan apa pun atas drafnya
        r = team["lead"].post("/approvals", {"draft_id": v3["id"], "level": "L1", "decision": decision, **EVIDENCE})
        assert r.status_code == 409 and code(r) == "approval_by_author"


def test_agency_l2_needs_written_client_evidence_and_minimum_level(team):
    draft = new_draft(team["staff"], new_request(team["staff"], intent="reel-script")["id"])
    r = team["approver"].post("/approvals", {"draft_id": draft["id"], "level": "L1", "decision": "Approved"})
    assert r.status_code == 409 and code(r) == "approval_level_too_low"
    assert team["lead"].post("/qa-records", {"draft_id": draft["id"], "gate": "claim-verification", "result": "Pass", "independent": True}).status_code == 201
    r = team["lead2"].post("/approvals", {"draft_id": draft["id"], "level": "L2", "decision": "Approved"})
    assert r.status_code == 409 and code(r) == "approval_needs_written_evidence"
    for bad in ("   ", "javascript:alert(1)", "data:text/html,x", "email://arsip/1", "https://a b"):
        r = team["lead2"].post("/approvals", {"draft_id": draft["id"], "level": "L2", "decision": "Approved", "channel_ref": bad})
        assert r.status_code == 422, bad
    r = team["lead2"].post("/approvals", {"draft_id": draft["id"], "level": "L2", "decision": "Approved", **EVIDENCE})
    assert r.status_code == 201 and r.json()["channel_ref"] == EVIDENCE["channel_ref"]


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
        results.append(actor.post("/drafts", {"content_flags": [], "request_id": req["id"], "content": "paralel"}))

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


# --- Temuan audit 2026-10-14 ----------------------------------------------------------------------


def test_risk_3_means_l3(team):
    """Risiko 3 (krisis, legal, review negatif) = L3 (rule 08), walau minimum intent lebih rendah."""
    req = new_request(team["staff"], risk=3)
    assert (req["approval_min"], req["priority"]) == ("L3", "Urgent")
    draft = new_draft(team["staff"], req["id"])
    r = team["approver"].post("/approvals", {"draft_id": draft["id"], "level": "L2", "decision": "Approved"})
    assert r.status_code == 409 and code(r) == "approval_level_too_low"


def test_lower_level_approver_cannot_reject_higher_level_content(team):
    draft = new_draft(team["staff"], new_request(team["staff"], intent="reel-script")["id"])
    r = team["approver_l1"].post("/approvals", {"draft_id": draft["id"], "level": "L2", "decision": "Rejected"})
    assert r.status_code == 403 and code(r) == "level_not_allowed"
    r = team["approver_l1"].post("/approvals", {"draft_id": draft["id"], "level": "L1", "decision": "Rejected"})
    assert r.status_code == 409 and code(r) == "approval_level_too_low"


def test_finished_request_accepts_no_new_draft_or_decision(team):
    req = new_request(team["staff"])
    draft = new_draft(team["staff"], req["id"])
    assert team["approver"].post("/approvals", {"draft_id": draft["id"], "level": "L1", "decision": "Approved"}).status_code == 201
    r = team["staff"].post("/drafts", {"content_flags": [], "request_id": req["id"], "content": "revisi setelah approved"})
    assert r.status_code == 409 and code(r) == "request_closed"
    r = team["approver"].post("/approvals", {"draft_id": draft["id"], "level": "L1", "decision": "Rejected"})
    assert r.status_code == 409 and code(r) == "request_closed"
    assert team["staff"].get(f"/requests/{req['id']}").json()["status"] == "approved"


def test_newer_failed_independent_review_blocks_l2(team):
    draft = new_draft(team["staff"], new_request(team["staff"], intent="reel-script")["id"])
    for who, result in (("lead", "Pass"), ("owner", "Fail")):
        r = team[who].post("/qa-records", {"draft_id": draft["id"], "gate": "claim-verification", "result": result, "independent": True})
        assert r.status_code == 201, r.text
    r = team["approver"].post("/approvals", {"draft_id": draft["id"], "level": "L2", "decision": "Approved"})
    assert r.status_code == 409 and code(r) == "approval_needs_independent_review"


@pytest.mark.parametrize("text", ["   ", "a\\u0000b"])
def test_blank_or_nul_text_is_rejected(team, text):
    body = '{"client_code": "CTH", "intent": "caption", "text": "%s"}' % text
    r = team["staff"].http.post("/requests", content=body, headers={**team["staff"].csrf, "content-type": "application/json"})
    assert r.status_code == 422 and code(r) == "validation_error", r.text


def test_large_unicode_draft_fits_body_limit(team):
    req = new_request(team["staff"])
    r = team["staff"].post("/drafts", {"content_flags": [], "request_id": req["id"], "content": "\U0001F334" * 10_000})
    assert r.status_code == 201, r.text


def test_role_and_level_come_from_the_same_membership(factory, team):
    """Content lead agency yang juga viewer L1 di CTH: approval memakai peran & level dari satu membership yang sama."""
    lead = Actor(factory, "content_lead")
    with factory() as s, s.begin():
        s.add(Membership(user_id=lead.id, scope="CTH", role="viewer", max_level="L1"))
    draft = new_draft(team["staff"], new_request(team["staff"], intent="reel-script")["id"])
    assert team["lead"].post("/qa-records", {"draft_id": draft["id"], "gate": "claim-verification", "result": "Pass", "independent": True}).status_code == 201
    r = lead.post("/approvals", {"draft_id": draft["id"], "level": "L2", "decision": "Approved", **EVIDENCE})
    assert r.status_code == 201, r.text
    assert r.json()["approver_role"] == "content_lead"


# --- Penanda isi konten & level approval otomatis (kontrak core 0.10.0, TASK-032) -----------------------


def reasons(draft: dict) -> set[str]:
    return {x["rule"] for x in draft["min_level_reasons"]}


def flags(draft: dict) -> dict[str, str]:
    return {f["flag"]: f["source"] for f in draft["content_flags"]}


def test_draft_must_state_content_flags(team):
    req = new_request(team["staff"])
    r = team["staff"].post("/drafts", {"request_id": req["id"], "content": "x"})
    assert r.status_code == 422 and code(r) == "content_flags_required"
    r = team["staff"].post("/drafts", {"request_id": req["id"], "content": "x", "content_flags": ["bukan-penanda"]})
    assert r.status_code == 422
    plain = new_draft(team["staff"], req["id"])
    assert (plain["min_level"], plain["content_flags"], plain["min_level_reasons"]) == ("L1", [], [])


def test_negative_review_reply_is_l3_and_positive_stays_l1(team):
    """Celah 1: balasan review negatif = L3 (Rule 08), dari rating, tanpa bergantung staf mengisi risk 3."""
    r = team["staff"].post("/requests", {"client_code": "CTH", "intent": "review-reply", "text": "Balas review Google"})
    assert r.status_code == 422 and code(r) == "review_rating_required"
    negative = new_draft(team["staff"], new_request(team["staff"], intent="review-reply", review_rating=2)["id"])
    assert negative["min_level"] == "L3" and flags(negative) == {"negative_review": "server"}
    r = team["approver"].post("/approvals", {"draft_id": negative["id"], "level": "L2", "decision": "Revise"})
    assert r.status_code == 409 and code(r) == "approval_level_too_low"
    positive = new_draft(team["staff"], new_request(team["staff"], intent="review-reply", review_rating=5)["id"])
    assert positive["min_level"] == "L1" and positive["content_flags"] == []


def test_localize_follows_source_draft_level(team):
    """Celah 2: terjemahan balasan review negatif tetap L3."""
    source = new_draft(team["staff"], new_request(team["staff"], intent="review-reply", review_rating=1)["id"])
    r = team["staff"].post("/requests", {"client_code": "CTH", "intent": "localize", "text": "Terjemahkan ke EN"})
    assert r.status_code == 422 and code(r) == "source_draft_required"
    other = new_draft(team["staff"], new_request(team["staff"], client="CTHB")["id"])
    r = team["staff"].post("/requests", {"client_code": "CTH", "intent": "localize", "text": "x", "source_draft_id": other["id"]})
    assert r.status_code == 409 and code(r) == "source_draft_invalid"
    req = new_request(team["staff"], intent="localize", source_draft_id=source["id"])
    assert req["source_draft_id"] == source["id"]
    translated = new_draft(team["staff"], req["id"])
    assert translated["min_level"] == "L3" and f"source_draft:{source['id']}" in reasons(translated)
    r = team["approver"].post("/approvals", {"draft_id": translated["id"], "level": "L2", "decision": "Revise"})
    assert r.status_code == 409 and code(r) == "approval_level_too_low"


@pytest.mark.parametrize(
    ("content", "flag", "level"),
    [
        ("Promo menginap Rp 1.500.000 per malam", "price_promo", "L2"),  # celah 3: harga di teks tanpa klaim
        ("Diskon 20% untuk tamu bulan ini", "price_promo", "L2"),
        ("Best rate langsung di website", "price_promo", "L2"),
        ("Upacara Melasti di pantai depan villa", "religion_culture", "L3"),  # celah 6
        ("Buka puasa Ramadan bersama keluarga", "religion_culture", "L3"),
    ],
)
def test_server_safety_net_flags_content(team, content, flag, level):
    draft = new_draft(team["staff"], new_request(team["staff"])["id"], content=content)
    assert flags(draft).get(flag) == "server" and draft["min_level"] == level


@pytest.mark.parametrize("content", [
    "Pagi tenang di villa, kopi hangat di teras.",
    "Upacara pernikahan di tepi tebing, momen sakral saat matahari terbenam.",  # bahasa wedding biasa, bukan topik agama
    "Rated 4.8 oleh tamu kami",
])
def test_plain_caption_is_not_flagged(team, content):
    draft = new_draft(team["staff"], new_request(team["staff"])["id"], content=content)
    assert draft["content_flags"] == [] and draft["min_level"] == "L1"


@pytest.mark.parametrize(("flag", "level"), [("people", "L2"), ("paid_ads", "L3"), ("influencer", "L3"), ("crisis", "L3")])
def test_author_flags_raise_level(team, flag, level):
    """Celah 4–5: konten dengan orang = L2; iklan berbayar & influencer = L3 (Rule 08)."""
    draft = new_draft(team["staff"], new_request(team["staff"])["id"], content_flags=[flag])
    assert flags(draft) == {flag: "author"} and draft["min_level"] == level and f"flag:{flag}" in reasons(draft)


def test_ota_listing_intent_gets_server_flag(team):
    draft = new_draft(team["staff"], new_request(team["staff"], intent="ota-listing")["id"])
    assert flags(draft) == {"ota_listing": "server"} and draft["min_level"] == "L2"


def test_author_flag_same_as_server_flag_is_not_duplicated(team):
    draft = new_draft(team["staff"], new_request(team["staff"])["id"], content="Diskon 10%", content_flags=["price_promo", "price_promo"])
    assert draft["content_flags"] and flags(draft) == {"price_promo": "server"} and len(draft["content_flags"]) == 1


def test_adding_and_removing_flags(team):
    draft = new_draft(team["staff"], new_request(team["staff"])["id"], content="Diskon 15% weekday")
    path = f"/drafts/{draft['id']}/flags"
    r = team["staff"].post(path, {"flag": "people"})
    assert r.status_code == 201 and r.json()["source"] == "staff"
    assert code(team["staff"].post(path, {"flag": "people"})) == "flag_exists"
    for who in ("approver", "viewer"):
        assert team[who].post(path, {"flag": "crisis"}).status_code == 403
    assert team["other"].post(path, {"flag": "crisis"}).status_code == 404
    # QA reviewer menambah penanda: sumber qa.
    assert team["lead"].post("/qa-records", {"draft_id": draft["id"], "gate": "content-review", "result": "Conditional", "independent": True}).status_code == 201
    r = team["lead"].post(path, {"flag": "paid_ads"})
    assert r.status_code == 201 and r.json()["source"] == "qa"
    assert team["staff"].get(f"/drafts/{draft['id']}").json()["min_level"] == "L3"
    # Hapus: hanya owner/content lead, dengan alasan; penanda server tidak bisa dihapus; sekali saja.
    assert team["staff"].post(f"{path}/paid_ads/remove", {"reason": "bukan iklan berbayar, organik"}).status_code == 403
    assert team["lead2"].post(f"{path}/paid_ads/remove", {"reason": "pendek"}).status_code == 422
    r = team["lead2"].post(f"{path}/paid_ads/remove", {"reason": "bukan iklan berbayar, post organik"})
    assert r.status_code == 200 and r.json()["removed_by"] == team["lead2"].id and r.json()["removed_at"]
    assert code(team["lead2"].post(f"{path}/paid_ads/remove", {"reason": "bukan iklan berbayar, post organik"})) == "flag_not_active"
    assert code(team["lead2"].post(f"{path}/price_promo/remove", {"reason": "diskon ini sudah disetujui"})) == "flag_not_removable"
    after = team["staff"].get(f"/drafts/{draft['id']}").json()
    assert flags(after) == {"price_promo": "server", "people": "staff"} and after["min_level"] == "L2"


def test_no_new_flags_after_request_finished(factory, team):
    draft = new_draft(team["staff"], new_request(team["staff"])["id"])
    assert team["approver"].post("/approvals", {"draft_id": draft["id"], "level": "L1", "decision": "Rejected"}).status_code == 201
    r = team["staff"].post(f"/drafts/{draft['id']}/flags", {"flag": "people"})
    assert r.status_code == 409 and code(r) == "request_closed"


def test_database_guards_flags_directly(factory, team):
    """Aturan penanda dijaga database, bukan hanya API (kontrak core database-schema § Constraint Wajib)."""
    from sqlalchemy import text
    from sqlalchemy.exc import IntegrityError, ProgrammingError

    draft = new_draft(team["staff"], new_request(team["staff"])["id"], content="Harga spesial Rp 900.000", content_flags=["people"])
    cases = [
        ("UPDATE draft_flags SET removed_by = :u, removed_at = now(), removed_reason = 'dihapus langsung' WHERE draft_id = :d AND flag = 'price_promo'",
         team["owner"].id, "flag_not_removable"),
        ("UPDATE draft_flags SET removed_by = :u, removed_at = now(), removed_reason = 'dihapus langsung' WHERE draft_id = :d AND flag = 'people'",
         team["staff"].id, "approval_role_mismatch"),
        ("UPDATE draft_flags SET flag = 'crisis' WHERE draft_id = :d AND flag = 'people' AND :u > 0", team["owner"].id, "decision_record_append_only"),
    ]
    for sql, user, rule in cases:
        with factory() as s:
            with pytest.raises(IntegrityError, match=rule):
                s.execute(text(sql), {"d": draft["id"], "u": user})
                s.flush()
    with factory() as s:  # hak DELETE dicabut dari role aplikasi (lapis kedua: trigger append-only)
        with pytest.raises(ProgrammingError, match="permission denied"):
            s.execute(text("DELETE FROM draft_flags WHERE draft_id = :d"), {"d": draft["id"]})
    with factory() as s, s.begin():  # rating & draft asal tidak bisa diubah setelah request dibuat
        req_id = new_request(team["staff"], intent="review-reply", review_rating=4)["id"]
        with pytest.raises(IntegrityError, match="decision_record_append_only"):
            s.execute(text("UPDATE requests SET review_rating = 5 WHERE id = :r"), {"r": req_id})
            s.flush()


def test_new_version_inherits_human_flags(team):
    """Versi baru tidak bisa menurunkan level dengan diam-diam: penanda manusia versi sebelumnya ikut."""
    req = new_request(team["staff"])
    v1 = new_draft(team["staff"], req["id"], content_flags=["people"])
    assert team["lead"].post(f"/drafts/{v1['id']}/flags", {"flag": "influencer"}).status_code == 201
    v2 = new_draft(team["staff"], req["id"], content="Versi baru tanpa centang")
    assert flags(v2) == {"people": "author", "influencer": "staff"} and v2["min_level"] == "L3"
    assert {f["added_by"] for f in v2["content_flags"]} == {team["staff"].id, team["lead"].id}
    # Dihapus dengan alasan di v2 → v3 tidak mewarisinya lagi.
    assert team["lead2"].post(f"/drafts/{v2['id']}/flags/influencer/remove", {"reason": "bukan kolaborasi, foto staf sendiri"}).status_code == 200
    v3 = new_draft(team["staff"], req["id"])
    assert flags(v3) == {"people": "author"} and v3["min_level"] == "L2"
