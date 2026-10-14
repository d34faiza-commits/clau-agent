"""Klien, fact sheet, dan Konfirmasi Fakta lewat API (kontrak core 0.8.0), ke PostgreSQL sungguhan.

Menguji tanggung jawab API (siapa boleh apa, isolasi per klien, validasi body) dan bahwa aturan migrasi 0005 sampai
ke pengguna sebagai kode kontrak. Rantai utuh: fakta dijawab klien → fact sheet disetujui → draft berklaim fakta
bisa di-approve L2.
"""

from __future__ import annotations

import pytest

pytest.importorskip("pyotp")
pytest.importorskip("psycopg")

from sqlalchemy import select  # noqa: E402

from app.db.models import AuditLog  # noqa: E402
from tests.test_workflow import EVIDENCE, Actor, code, engine, factory, new_draft, new_request, team  # noqa: E402,F401

FACTS = [
    {"fact_key": "facility.pool-private", "category": "facility", "label": "Kolam renang pribadi", "value": "Ada, 4 x 8 m"},
    {"fact_key": "price.weekday", "category": "price", "label": "Harga weekday per malam", "value": "Rp 2.500.000"},
]
SHEET = {"client_code": "CTH", "document_ref": "workspace://cth/fact-sheet", "facts": FACTS}


def new_sheet(actor: Actor, **extra) -> dict:
    r = actor.post("/fact-sheets", {**SHEET, **extra})
    assert r.status_code == 201, r.text
    return r.json()


def by_key(sheet: dict) -> dict:
    return {f["fact_key"]: f for f in sheet["facts"]}


# --- Alur utuh -----------------------------------------------------------------------------------


def test_client_confirms_facts_then_draft_can_be_approved(team):
    sheet = new_sheet(team["lead"])
    assert (sheet["status"], sheet["facts_total"], sheet["facts_answered"], sheet["created_by"]) == ("pending", 2, 0, team["lead"].id)
    assert sheet["approved_at"] is None and {f["status"] for f in sheet["facts"]} == {"pending"}

    approver = team["approver"]
    sid = sheet["id"]
    r = approver.post(f"/fact-sheets/{sid}/confirmations", {"fact_key": "facility.pool-private", "decision": "confirmed"})
    assert r.status_code == 201, r.text
    assert (r.json()["value_before"], r.json()["value_after"], r.json()["confirmed_by_role"]) == ("Ada, 4 x 8 m", None, "client_approver")
    assert approver.post(f"/fact-sheets/{sid}/approve", {}).status_code == 409  # satu fakta belum dijawab
    r = approver.post(f"/fact-sheets/{sid}/confirmations", {"fact_key": "price.weekday", "decision": "corrected", "value_after": "Rp 2.750.000"})
    assert r.status_code == 201, r.text

    detail = approver.get(f"/fact-sheets/{sid}").json()
    facts = by_key(detail)
    assert detail["status"] == "ready" and detail["facts_answered"] == 2
    assert (facts["price.weekday"]["status"], facts["price.weekday"]["current_value"]) == ("corrected", "Rp 2.750.000")
    assert facts["facility.pool-private"]["current_value"] == "Ada, 4 x 8 m"

    r = approver.post(f"/fact-sheets/{sid}/approve", {})
    assert r.status_code == 200, r.text
    assert (r.json()["status"], r.json()["approved_by"], r.json()["approved_by_role"]) == ("approved", approver.id, "client_approver")

    claim = {"text": "Kolam renang pribadi", "category": "facility", "evidence_label": "CLIENT CONFIRMATION", "fact_key": "facility.pool-private"}
    draft = new_draft(team["staff"], new_request(team["staff"])["id"], claims=[claim], fact_sheet_id=sid)
    qa = team["lead"].post("/qa-records", {"draft_id": draft["id"], "gate": "claim-verification", "result": "Pass", "independent": True})
    assert qa.status_code == 201
    r = approver.post("/approvals", {"draft_id": draft["id"], "level": "L2", "decision": "Approved"})
    assert r.status_code == 201, r.text


def test_versions_count_up_per_client(team):
    first = new_sheet(team["staff"])
    second = new_sheet(team["staff"])
    assert second["version"] == first["version"] + 1
    listed = team["approver"].get("/fact-sheets", client_code="CTH").json()["items"]
    assert [s["version"] for s in listed] == sorted((s["version"] for s in listed), reverse=True)


# --- Siapa boleh apa -----------------------------------------------------------------------------


@pytest.mark.parametrize(("who", "status"), [("owner", 201), ("lead", 201), ("staff", 201), ("approver", 403), ("viewer", 403), ("other", 403)])
def test_who_can_write_a_fact_sheet(team, who, status):
    assert team[who].post("/fact-sheets", SHEET).status_code == status


@pytest.mark.parametrize(
    ("who", "evidence", "status", "rule"),
    [("approver", False, 201, None), ("approver_l1", False, 201, None), ("lead2", True, 201, None),
     ("owner", False, 409, "approval_needs_written_evidence"), ("lead", True, 409, "approval_by_author"),
     ("staff", True, 403, "forbidden"), ("viewer", False, 403, "forbidden"), ("other", False, 404, "not_found")],
)
def test_who_can_answer_a_fact(team, who, evidence, status, rule):
    """Jawaban dari klien; agency hanya mencatat jawaban tertulis klien (bukti), dan bukan pembuat fact sheet."""
    sheet = new_sheet(team["lead"])
    body = {"fact_key": "price.weekday", "decision": "confirmed", **(EVIDENCE if evidence else {})}
    r = team[who].post(f"/fact-sheets/{sheet['id']}/confirmations", body)
    assert r.status_code == status, r.text
    if rule:
        assert code(r) == rule


def test_who_can_approve_a_fact_sheet(team):
    sheet = new_sheet(team["lead"])
    sid = sheet["id"]
    for key in ("facility.pool-private", "price.weekday"):
        assert team["approver_l1"].post(f"/fact-sheets/{sid}/confirmations", {"fact_key": key, "decision": "confirmed"}).status_code == 201
    assert team["staff"].post(f"/fact-sheets/{sid}/approve", {}).status_code == 403
    assert team["viewer"].post(f"/fact-sheets/{sid}/approve", {}).status_code == 403
    assert team["other"].post(f"/fact-sheets/{sid}/approve", {}).status_code == 404
    r = team["owner"].post(f"/fact-sheets/{sid}/approve", {})
    assert r.status_code == 409 and code(r) == "approval_needs_written_evidence"
    r = team["lead"].post(f"/fact-sheets/{sid}/approve", {"approval_ref": EVIDENCE["channel_ref"]})
    assert r.status_code == 409 and code(r) == "approval_by_author"
    r = team["owner"].post(f"/fact-sheets/{sid}/approve", {"approval_ref": EVIDENCE["channel_ref"]})
    assert r.status_code == 200 and r.json()["approval_ref"] == EVIDENCE["channel_ref"]


def test_approved_fact_sheet_is_frozen(team):
    sheet = new_sheet(team["lead"], facts=[FACTS[0]])
    sid = sheet["id"]
    assert team["approver"].post(f"/fact-sheets/{sid}/confirmations", {"fact_key": "facility.pool-private", "decision": "confirmed"}).status_code == 201
    assert team["approver"].post(f"/fact-sheets/{sid}/approve", {}).status_code == 200
    r = team["approver"].post(f"/fact-sheets/{sid}/approve", {})
    assert r.status_code == 409 and code(r) == "fact_sheet_frozen"
    r = team["approver"].post(f"/fact-sheets/{sid}/confirmations", {"fact_key": "facility.pool-private", "decision": "corrected", "value_after": "Tidak ada"})
    assert r.status_code == 409 and code(r) == "fact_sheet_frozen"


def test_answer_rules_reach_the_user(team):
    sid = new_sheet(team["lead"])["id"]
    r = team["approver"].post(f"/fact-sheets/{sid}/confirmations", {"fact_key": "price.weekend", "decision": "confirmed"})
    assert r.status_code == 409 and code(r) == "fact_not_in_sheet"
    r = team["approver"].post(f"/fact-sheets/{sid}/approve", {})
    assert r.status_code == 409 and code(r) == "facts_unconfirmed"


# --- Isolasi klien -------------------------------------------------------------------------------


def test_other_client_cannot_see_fact_sheets(team):
    sheet = new_sheet(team["lead"])
    other = team["other"]
    r = other.get(f"/fact-sheets/{sheet['id']}")
    assert r.status_code == 404 and code(r) == "not_found"
    assert other.get("/fact-sheets", client_code="CTH").status_code == 403
    assert all(s["client_code"] == "CTHB" for s in other.get("/fact-sheets").json()["items"])
    assert team["viewer"].get(f"/fact-sheets/{sheet['id']}").status_code == 200  # viewer CTH boleh membaca
    assert {c["client_code"] for c in other.get("/clients").json()["items"]} == {"CTHB"}
    assert {c["client_code"] for c in team["staff"].get("/clients").json()["items"]} >= {"CTH", "CTHB", "CTHSIM"}


# --- Validasi ------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "change",
    [
        {"facts": []},
        {"facts": [{**FACTS[0], "fact_key": "price.kolam"}]},  # kunci kategori lain
        {"facts": [{**FACTS[0], "category": "experience", "fact_key": "experience.tenang"}]},  # kesan bukan fakta
        {"facts": [FACTS[0], FACTS[0]]},  # kunci dobel
        {"facts": [{**FACTS[0], "value": "   "}]},
        {"facts": [{**FACTS[0], "value": "a\x00b"}]},
        {"document_ref": "javascript:alert(1)"},
        {"version": 7},  # diisi server
        {"approved_at": "2026-10-14T09:00:00+08:00"},
    ],
)
def test_fact_sheet_body_is_validated(team, change):
    r = team["lead"].post("/fact-sheets", {**SHEET, **change})
    assert r.status_code == 422 and code(r) == "validation_error", r.text


@pytest.mark.parametrize(
    "body",
    [
        {"fact_key": "price.weekday", "decision": "corrected"},
        {"fact_key": "price.weekday", "decision": "corrected", "value_after": "  "},
        {"fact_key": "price.weekday", "decision": "maybe"},
        {"fact_key": "price.weekday", "decision": "confirmed", "channel_ref": "data:text/html,x"},
        {"fact_key": "price.weekday", "decision": "confirmed", "confirmed_by_role": "client_approver"},
    ],
)
def test_answer_body_is_validated(team, body):
    sid = new_sheet(team["lead"])["id"]
    r = team["approver"].post(f"/fact-sheets/{sid}/confirmations", body)
    assert r.status_code == 422 and code(r) == "validation_error", r.text


# --- Klien ---------------------------------------------------------------------------------------


def test_only_owner_adds_clients(team):
    body = {"client_code": "CTHBARU", "vertical": "food-beverage", "business_type": "cafe", "location_area": "Canggu", "approver_role": "owner"}
    assert team["lead"].post("/clients", body).status_code == 403
    assert team["approver"].post("/clients", body).status_code == 403
    r = team["owner"].post("/clients", body)
    assert r.status_code == 201 and r.json()["simulation"] is False
    r = team["owner"].post("/clients", body)
    assert r.status_code == 409 and code(r) == "client_exists"
    for bad in ({**body, "client_code": "cth baru"}, {**body, "vertical": "casino"}, {**body, "client_code": "CTHX", "extra": 1}):
        assert team["owner"].post("/clients", bad).status_code == 422


def test_audit_log_has_no_fact_values(factory, team):
    sid = new_sheet(team["lead"])["id"]
    team["approver"].post(f"/fact-sheets/{sid}/confirmations", {"fact_key": "price.weekday", "decision": "corrected", "value_after": "Rp 9.999.999"})
    with factory() as s:
        rows = s.scalars(select(AuditLog).where(AuditLog.object_type == "fact_sheet", AuditLog.object_id == str(sid))).all()
    assert {r.action for r in rows} == {"fact_sheet.create", "fact.answer"}
    dumped = repr([r.meta for r in rows])
    assert "2.500.000" not in dumped and "9.999.999" not in dumped and "Kolam" not in dumped
