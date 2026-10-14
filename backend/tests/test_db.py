"""Skema database & Constraint Wajib (core/shared/database-schema.md), diuji ke PostgreSQL sungguhan
lewat role aplikasi: aturan harus ditolak database sendiri, bukan hanya oleh kode API."""

from __future__ import annotations

import re
from contextlib import contextmanager
from pathlib import Path

import pytest

psycopg = pytest.importorskip("psycopg")

from app.db.models import Base  # noqa: E402

CORE_SCHEMA = Path(__file__).resolve().parents[2] / "core" / "shared" / "database-schema.md"


@contextmanager
def violates(conn, rule: str):
    """Statement di dalam blok harus ditolak dengan pesan berawalan `rule` (trigger) atau nama constraint."""
    with pytest.raises(psycopg.errors.IntegrityError) as err:
        with conn.transaction():
            yield
    assert rule in str(err.value), f"diharapkan pelanggaran {rule!r}, dapat: {err.value}"


def insert(conn, table: str, **values):
    cols = ", ".join(values)
    marks = ", ".join(["%s"] * len(values))
    returning = "client_code" if table == "clients" else "brief_id" if table == "briefs" else "id"
    row = conn.execute(f"INSERT INTO {table} ({cols}) VALUES ({marks}) RETURNING {returning}", list(values.values())).fetchone()
    return row[0] if row else None


def new_request(conn, client="CTH", approval_min="L1"):
    return insert(conn, "requests", client_code=client, intent="caption", pillar=1, approval_min=approval_min, text="caption pagi", requested_by_role="owner")


@pytest.fixture()
def world(app_conn):
    """Klien nyata (CTH) + klien fiktif (CTHSIM, simulation) + 3 user (pembuat, reviewer, approver) + satu request
    dan draft v1 per klien: draft NYATA buatan manusia dan draft SIMULASI buatan agent."""
    c = app_conn
    insert(c, "clients", client_code="CTH", vertical="accommodation", business_type="villa", approver_role="owner")
    insert(c, "clients", client_code="CTHSIM", vertical="accommodation", business_type="villa", approver_role="owner", simulation=True)
    author = insert(c, "users", display_name="Penulis Contoh", email="penulis@contoh.test")
    reviewer = insert(c, "users", display_name="Reviewer Contoh", email="reviewer@contoh.test")
    approver = insert(c, "users", display_name="Approver Contoh", email="approver@contoh.test")
    lead = insert(c, "users", display_name="Lead Contoh", email="lead@contoh.test")
    # Peran yang tercatat di QA/approval dicek ke memberships (migrasi 0004).
    for user, scope, role in ((author, "agency", "content_staff"), (reviewer, "agency", "content_lead"), (lead, "agency", "content_lead"),
                              (approver, "CTH", "client_approver"), (approver, "CTHSIM", "client_approver")):
        c.execute("INSERT INTO memberships (user_id, scope, role, max_level) VALUES (%s, %s, %s, 'L3')", (user, scope, role))
    request = new_request(c)
    sim_request = new_request(c, client="CTHSIM")
    nyata = insert(c, "drafts", request_id=request, skill="draft-caption", version=1, content="v1", mode="NYATA", created_by=author)
    sim = insert(c, "drafts", request_id=sim_request, skill="draft-caption", version=1, content="v1", mode="SIMULASI", agent_id="caption-writer")
    return {"author": author, "reviewer": reviewer, "approver": approver, "lead": lead, "request": request, "sim_request": sim_request, "nyata": nyata, "sim": sim}


def approve(conn, draft, approver, level="L1", decision="Approved", mode="NYATA", role="client_approver", channel_ref=None):
    return insert(conn, "approvals", draft_id=draft, level=level, decision=decision, approver_id=approver, approver_role=role, mode=mode, channel_ref=channel_ref)


def qa(conn, draft, reviewer, independent=True, result="Pass", gate="claim-verification", role="content_lead"):
    return insert(conn, "qa_records", draft_id=draft, gate=gate, result=result, reviewer_id=reviewer, reviewer_role=role, independent=independent)


# --- Skema --------------------------------------------------------------------------------------


def test_tables_match_core_contract(app_conn):
    if not CORE_SCHEMA.is_file():
        pytest.skip("submodule core belum di-init")
    contract = set(re.findall(r"^\| `([a-z_]+)` \|", CORE_SCHEMA.read_text(encoding="utf-8"), re.MULTILINE))
    rows = app_conn.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' AND table_name <> 'alembic_version'").fetchall()
    assert {r[0] for r in rows} == contract


def test_models_match_migrations(database):
    """Model SQLAlchemy dan migrasi tidak boleh berbeda (perubahan model wajib disertai migrasi)."""
    from alembic.autogenerate import compare_metadata
    from alembic.migration import MigrationContext
    from sqlalchemy import create_engine

    from tests.conftest import sqlalchemy_url

    engine = create_engine(sqlalchemy_url(database.migrator_conninfo))
    with engine.connect() as conn:
        diff = compare_metadata(MigrationContext.configure(conn), Base.metadata)
    engine.dispose()
    assert diff == [], f"model berbeda dengan migrasi: {diff}"


def test_migrations_downgrade_and_upgrade_cleanly(database):
    from tests.conftest import TempDatabase

    db = TempDatabase(database.admin_url)
    try:
        db.alembic("upgrade", "head")
        db.alembic("downgrade", "base")
        db.alembic("upgrade", "head")
    finally:
        db.drop()


# --- Hak akses role aplikasi (docs/security.md § 6) ---------------------------------------------


@pytest.mark.parametrize(
    "statement",
    [
        "CREATE TABLE evil (id int)",
        "DROP TABLE clients",
        "ALTER TABLE clients ADD COLUMN evil text",
        "TRUNCATE requests",
        "CREATE FUNCTION evil() RETURNS int LANGUAGE sql AS 'select 1'",
    ],
)
def test_app_role_has_no_ddl(app_conn, statement):
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        with app_conn.transaction():
            app_conn.execute(statement)


def test_audit_log_is_append_only(app_conn, database, world):
    entry = insert(app_conn, "audit_log", actor_id=world["author"], action="approve", object_type="draft", object_id="1")
    for statement in (f"UPDATE audit_log SET action = 'x' WHERE id = {entry}", f"DELETE FROM audit_log WHERE id = {entry}", "TRUNCATE audit_log"):
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            with app_conn.transaction():
                app_conn.execute(statement)


def test_audit_log_append_only_even_for_owner(database):
    with psycopg.connect(database.migrator_conninfo) as conn:
        entry = insert(conn, "audit_log", action="test", object_type="x", object_id="1")
        with violates(conn, "audit_log_append_only"):
            conn.execute("DELETE FROM audit_log WHERE id = %s", (entry,))
        with violates(conn, "audit_log_append_only"):
            conn.execute("TRUNCATE audit_log")
        conn.rollback()


# --- Constraint Wajib ---------------------------------------------------------------------------


def test_simulasi_is_never_approved(app_conn, world):
    with violates(app_conn, "simulasi_not_approved"):
        approve(app_conn, world["sim"], world["approver"], mode="SIMULASI")
    approve(app_conn, world["sim"], world["approver"], decision="Revise", mode="SIMULASI")


def test_approval_mode_must_match_draft(app_conn, world):
    with violates(app_conn, "approval_mode_mismatch"):
        approve(app_conn, world["sim"], world["approver"], decision="Revise", mode="NYATA")


def test_publication_requires_approval(app_conn, world):
    def publish():
        insert(app_conn, "publications", draft_id=world["nyata"], channel="instagram", published_at="2026-10-12T10:00:00+08:00", published_by_role="content_lead")

    with violates(app_conn, "publication_without_approval"):
        publish()
    approve(app_conn, world["nyata"], world["approver"], decision="Revise")
    with violates(app_conn, "publication_without_approval"):
        publish()
    approve(app_conn, world["nyata"], world["approver"])
    publish()


@pytest.mark.parametrize("level", ["L2", "L3"])
def test_l2_l3_need_independent_claim_verification(app_conn, world, level):
    draft, approver = world["nyata"], world["approver"]
    with violates(app_conn, "approval_needs_independent_review"):
        approve(app_conn, draft, approver, level=level)
    qa(app_conn, draft, world["author"], independent=False, role="content_staff")  # self-review: pre-check saja
    qa(app_conn, draft, world["reviewer"], result="Fail")
    qa(app_conn, draft, world["reviewer"], gate="content-review")
    with violates(app_conn, "approval_needs_independent_review"):
        approve(app_conn, draft, approver, level=level)
    qa(app_conn, draft, world["reviewer"], result="Pass")
    approve(app_conn, draft, approver, level=level)


def test_l1_does_not_need_independent_review(app_conn, world):
    approve(app_conn, world["nyata"], world["approver"], level="L1")


def test_reviewer_cannot_review_own_draft(app_conn, world):
    draft = insert(app_conn, "drafts", request_id=new_request(app_conn), skill="draft-caption", version=1, content="x", mode="NYATA", created_by=world["lead"])
    with violates(app_conn, "qa_reviewer_is_author"):
        qa(app_conn, draft, world["lead"], independent=True)


def test_agent_review_is_never_independent(app_conn, world):
    with violates(app_conn, "independent_is_human"):
        insert(app_conn, "qa_records", draft_id=world["sim"], gate="claim-verification", result="Pass", reviewer_role="agent", independent=True)


def test_data_final_claim_needs_source_and_date(app_conn, world):
    base = {"draft_id": world["nyata"], "text": "Kolam renang pribadi", "category": "facility", "evidence_label": "DATA FINAL", "fact_key": "facility.pool-private"}
    with violates(app_conn, "data_final_sourced"):
        insert(app_conn, "claims", **base)
    with violates(app_conn, "data_final_sourced"):
        insert(app_conn, "claims", **base, source="  ", source_date="2026-10-01")
    with violates(app_conn, "data_final_sourced"):
        insert(app_conn, "claims", **base, source="fact sheet v3")
    insert(app_conn, "claims", **base, source="fact sheet v3", source_date="2026-10-01")
    insert(app_conn, "claims", **{**base, "evidence_label": "ASSUMPTION"})


def test_approved_draft_version_cannot_be_edited(app_conn, world):
    with violates(app_conn, "draft_version_immutable"):
        app_conn.execute("UPDATE drafts SET content = 'diam-diam diubah' WHERE id = %s", (world["nyata"],))
    insert(app_conn, "drafts", request_id=world["request"], skill="draft-caption", version=2, content="revisi", mode="NYATA", created_by=world["author"])


@pytest.mark.parametrize(
    ("label", "rule"),
    [("ASUMSI", "ck_claims_evidence_label"), ("data final", "ck_claims_evidence_label")],
)
def test_evidence_label_is_exact(app_conn, world, label, rule):
    with violates(app_conn, rule):
        insert(app_conn, "claims", draft_id=world["nyata"], text="x", category="other", evidence_label=label)


@pytest.mark.parametrize(
    ("scope", "role", "ok"),
    [
        ("agency", "owner", True),
        ("CTH", "client_approver", True),
        ("CTH", "viewer", True),
        ("CTH", "owner", False),
        ("agency", "client_approver", False),
        ("cth", "viewer", False),
    ],
)
def test_membership_role_matches_scope(app_conn, world, scope, role, ok):
    user = insert(app_conn, "users", display_name="Baru", email="baru@contoh.test")
    values = {"user_id": user, "scope": scope, "role": role, "max_level": "L2"}
    if ok:
        app_conn.execute("INSERT INTO memberships (user_id, scope, role, max_level) VALUES (%(user_id)s, %(scope)s, %(role)s, %(max_level)s)", values)
    else:
        with violates(app_conn, "ck_memberships"):
            app_conn.execute("INSERT INTO memberships (user_id, scope, role, max_level) VALUES (%(user_id)s, %(scope)s, %(role)s, %(max_level)s)", values)


def test_email_unique_case_insensitive(app_conn, world):
    with violates(app_conn, "uq_users_email_lower"):
        insert(app_conn, "users", display_name="Duplikat", email="PENULIS@contoh.test")


def test_brief_id_belongs_to_client(app_conn, world):
    with violates(app_conn, "brief_id_client"):
        insert(app_conn, "briefs", brief_id="ABC-202610-01", client_code="CTH", schema_version="1.4", payload='{"a": 1}')
    insert(app_conn, "briefs", brief_id="CTH-202610-01", client_code="CTH", schema_version="1.4", payload='{"a": 1}')


def test_seed_is_simulasi_and_idempotent(database):
    from sqlalchemy import create_engine, func, select
    from sqlalchemy.orm import Session

    from app.db.models import Approval, Client, Draft
    from app.db.seed import CLIENTS, seed
    from tests.conftest import sqlalchemy_url

    engine = create_engine(sqlalchemy_url(database.app_conninfo))
    try:
        with Session(engine) as session, session.begin():
            assert seed(session) == len(CLIENTS)
            assert seed(session) == 0
            codes = session.scalars(select(Client.client_code)).all()
            assert codes and all(code.startswith("CTH") for code in codes)
            assert set(session.scalars(select(Draft.mode))) == {"SIMULASI"}
            assert all(session.scalars(select(Client.simulation)))
            assert session.scalar(select(func.count()).select_from(Approval)) == 0
            session.rollback()
    finally:
        engine.dispose()


# --- Workflow (migrasi 0004, kontrak core 0.7.0) --------------------------------------------------


def next_sheet_version(conn, client: str) -> int:
    return 1 + conn.execute("SELECT count(*) FROM fact_sheets WHERE client_code = %s", (client,)).fetchone()[0]


def add_fact(conn, sheet, key, value="ya"):
    return insert(conn, "facts", fact_sheet_id=sheet, fact_key=key, category=key.split(".", 1)[0], label=key, value=value)


def answer(conn, sheet, key, by, role="client_approver", decision="confirmed", value_after=None, channel_ref=None):
    return insert(conn, "fact_confirmations", fact_sheet_id=sheet, fact_key=key, decision=decision, value_after=value_after,
                  confirmed_by=by, confirmed_by_role=role, channel_ref=channel_ref)


def approve_sheet(conn, sheet, by, role="client_approver", ref=None):
    conn.execute("UPDATE fact_sheets SET approved_at = now(), approved_by = %s, approved_by_role = %s, approval_ref = %s WHERE id = %s", (by, role, ref, sheet))


def fact_sheet(conn, client="CTH", approved=True, confirmed=("facility.pool-private",), confirmer=None, created_by=None):
    """Alur migrasi 0005: versi baru (belum disetujui) → fakta → jawaban klien → disetujui klien."""
    sheet = insert(conn, "fact_sheets", client_code=client, version=next_sheet_version(conn, client), document_ref="workspace://fact-sheet", created_by=created_by)
    for key in confirmed:
        add_fact(conn, sheet, key)
        answer(conn, sheet, key, confirmer)
    if approved:
        approve_sheet(conn, sheet, confirmer)
    return sheet


def factual_draft(conn, world, sheet=None, key="facility.pool-private"):
    request = new_request(conn)
    draft = insert(conn, "drafts", request_id=request, skill="draft-caption", version=1, content="kolam pribadi", mode="NYATA", created_by=world["author"], fact_sheet_id=sheet)
    insert(conn, "claims", draft_id=draft, text="Kolam renang pribadi", category="facility", evidence_label="ASSUMPTION", fact_key=key)
    return draft


def test_factual_claim_needs_fact_key(app_conn, world):
    base = {"draft_id": world["nyata"], "text": "Kolam renang pribadi", "category": "facility", "evidence_label": "ASSUMPTION"}
    with violates(app_conn, "fact_key_required"):
        insert(app_conn, "claims", **base)
    with violates(app_conn, "fact_key_format"):
        insert(app_conn, "claims", **base, fact_key="Pool Private")
    with violates(app_conn, "fact_key_required"):  # kunci kategori lain tidak bisa dipinjam
        insert(app_conn, "claims", **{**base, "category": "price"}, fact_key="facility.pool-private")
    insert(app_conn, "claims", **base, fact_key="facility.pool-private")
    insert(app_conn, "claims", **{**base, "category": "experience"})  # kesan/pengalaman: tanpa fact_key


def test_facts_unconfirmed_blocks_approval(app_conn, world):
    """Approved ditolak sampai setiap fact_key klaim dikonfirmasi di fact sheet yang disetujui."""

    def approve_l2(draft):
        qa(app_conn, draft, world["reviewer"])
        approve(app_conn, draft, world["approver"], level="L2")

    with violates(app_conn, "facts_unconfirmed"):  # draft tanpa fact sheet
        approve_l2(factual_draft(app_conn, world))
    unapproved = fact_sheet(app_conn, approved=False, confirmer=world["approver"])
    with violates(app_conn, "facts_unconfirmed"):
        approve_l2(factual_draft(app_conn, world, unapproved))
    sheet = fact_sheet(app_conn, confirmed=("facility.pool-heated",), confirmer=world["approver"])
    with violates(app_conn, "facts_unconfirmed"):  # fakta lain dikonfirmasi, pool-private belum
        approve_l2(factual_draft(app_conn, world, sheet))
    good = fact_sheet(app_conn, confirmer=world["approver"])
    draft = factual_draft(app_conn, world, good)
    approve(app_conn, draft, world["approver"], level="L2", decision="Revise")  # Revise/Rejected tidak butuh fakta
    approve_l2(draft)


def test_factual_claim_raises_minimum_level_to_l2(app_conn, world):
    """Rule 08: L1 = konten rutin tanpa klaim baru; klaim fakta (harga, fasilitas, …) minimal L2."""
    draft = factual_draft(app_conn, world, fact_sheet(app_conn, confirmer=world["approver"]))
    with violates(app_conn, "approval_level_too_low"):
        approve(app_conn, draft, world["approver"], level="L1")
    with violates(app_conn, "approval_level_too_low"):  # juga untuk Revise/Rejected
        approve(app_conn, draft, world["approver"], level="L1", decision="Rejected")


def test_draft_cannot_use_other_clients_fact_sheet_or_brief(app_conn, world):
    other = fact_sheet(app_conn, client="CTHSIM", confirmer=world["approver"])
    with violates(app_conn, "draft_client_mismatch"):
        insert(app_conn, "drafts", request_id=world["request"], skill="draft-caption", version=2, content="x", mode="NYATA", created_by=world["author"], fact_sheet_id=other)
    insert(app_conn, "briefs", brief_id="CTHSIM-202610-01", client_code="CTHSIM", schema_version="1.4", payload='{"a": 1}')
    with violates(app_conn, "draft_client_mismatch"):
        insert(app_conn, "drafts", request_id=world["request"], skill="draft-caption", version=2, content="x", mode="NYATA", created_by=world["author"], brief_id="CTHSIM-202610-01")


def test_draft_mode_and_version_come_from_client_and_sequence(app_conn, world):
    with violates(app_conn, "draft_mode_mismatch"):
        insert(app_conn, "drafts", request_id=world["request"], skill="draft-caption", version=2, content="x", mode="SIMULASI", created_by=world["author"])
    with violates(app_conn, "draft_mode_mismatch"):
        insert(app_conn, "drafts", request_id=world["sim_request"], skill="draft-caption", version=2, content="x", mode="NYATA", created_by=world["author"])
    with violates(app_conn, "draft_version_sequence"):
        insert(app_conn, "drafts", request_id=world["request"], skill="draft-caption", version=5, content="x", mode="NYATA", created_by=world["author"])


def test_only_latest_version_can_be_approved(app_conn, world):
    v2 = insert(app_conn, "drafts", request_id=world["request"], skill="draft-caption", version=2, content="v2", mode="NYATA", created_by=world["author"])
    with violates(app_conn, "approval_version_mismatch"):
        approve(app_conn, world["nyata"], world["approver"])
    approve(app_conn, world["nyata"], world["approver"], decision="Revise")  # catatan untuk versi lama tetap boleh
    approve(app_conn, v2, world["approver"])


def test_approval_level_cannot_be_below_intent_minimum(app_conn, world):
    request = new_request(app_conn, approval_min="L2")
    draft = insert(app_conn, "drafts", request_id=request, skill="draft-reel-script", version=1, content="x", mode="NYATA", created_by=world["author"])
    with violates(app_conn, "approval_level_too_low"):
        approve(app_conn, draft, world["approver"], level="L1")
    qa(app_conn, draft, world["reviewer"])
    approve(app_conn, draft, world["approver"], level="L2")


@pytest.mark.parametrize("decision", ["Approved", "Revise", "Rejected"])
def test_author_cannot_decide_on_own_draft(app_conn, world, decision):
    draft = insert(app_conn, "drafts", request_id=new_request(app_conn), skill="draft-caption", version=1, content="x", mode="NYATA", created_by=world["lead"])
    with violates(app_conn, "approval_by_author"):
        approve(app_conn, draft, world["lead"], decision=decision, role="content_lead", channel_ref="https://mail.contoh.test/arsip/1")


@pytest.mark.parametrize("level", ["L1", "L2"])
def test_agency_approval_needs_written_client_evidence(app_conn, world, level):
    """Rule 08: persetujuan selalu dari klien; agency hanya mencatat persetujuan tertulis klien, di level apa pun."""
    qa(app_conn, world["nyata"], world["reviewer"])
    with violates(app_conn, "approval_needs_written_evidence"):
        approve(app_conn, world["nyata"], world["lead"], level=level, role="content_lead", channel_ref="  ")
    approve(app_conn, world["nyata"], world["lead"], level=level, role="content_lead", decision="Revise")  # Revise: tanpa bukti
    approve(app_conn, world["nyata"], world["lead"], level=level, role="content_lead", channel_ref="https://mail.contoh.test/arsip/approval-cth")


def test_recorded_role_must_be_real_membership(app_conn, world):
    with violates(app_conn, "approval_role_mismatch"):  # content_lead mengaku approver klien
        approve(app_conn, world["nyata"], world["lead"], role="client_approver")
    with violates(app_conn, "approval_role_mismatch"):  # approver klien CTH mengaku owner
        approve(app_conn, world["nyata"], world["approver"], role="owner", channel_ref="https://x.test/1")
    lead_draft = insert(app_conn, "drafts", request_id=new_request(app_conn), skill="draft-caption", version=1, content="x", mode="NYATA", created_by=world["lead"])
    with violates(app_conn, "qa_role_mismatch"):  # approver klien bukan staf agency
        qa(app_conn, lead_draft, world["approver"], role="content_lead", independent=False)
    with violates(app_conn, "independent_review_not_allowed"):  # content_staff: pre-check saja
        qa(app_conn, lead_draft, world["author"], role="content_staff", independent=True)


def test_latest_independent_claim_verification_counts(app_conn, world):
    qa(app_conn, world["nyata"], world["reviewer"], result="Pass")
    qa(app_conn, world["nyata"], world["lead"], result="Fail")  # Fail terbaru membatalkan Pass sebelumnya
    with violates(app_conn, "approval_needs_independent_review"):
        approve(app_conn, world["nyata"], world["approver"], level="L2")
    qa(app_conn, world["nyata"], world["reviewer"], result="Pass")
    approve(app_conn, world["nyata"], world["approver"], level="L2")


def test_finished_request_accepts_no_new_draft_or_decision(app_conn, world):
    approve(app_conn, world["nyata"], world["approver"])
    app_conn.execute("UPDATE requests SET status = 'approved' WHERE id = %s", (world["request"],))
    with violates(app_conn, "request_closed"):
        insert(app_conn, "drafts", request_id=world["request"], skill="draft-caption", version=2, content="x", mode="NYATA", created_by=world["author"])
    with violates(app_conn, "request_closed"):
        approve(app_conn, world["nyata"], world["approver"], decision="Rejected")


def test_publication_needs_latest_decision_approved_on_latest_version(app_conn, world):
    def publish(draft):
        insert(app_conn, "publications", draft_id=draft, channel="instagram", published_at="2026-10-14T10:00:00+08:00", published_by_role="content_lead")

    approve(app_conn, world["nyata"], world["approver"])
    approve(app_conn, world["nyata"], world["approver"], decision="Revise")  # keputusan terakhir bukan Approved
    with violates(app_conn, "publication_without_approval"):
        publish(world["nyata"])
    v2 = insert(app_conn, "drafts", request_id=world["request"], skill="draft-caption", version=2, content="v2", mode="NYATA", created_by=world["author"])
    approve(app_conn, v2, world["approver"])
    publish(v2)
    with violates(app_conn, "publication_without_approval"):  # v1 sudah digantikan v2
        publish(world["nyata"])


def test_fact_evidence_is_frozen(app_conn, world):
    sheet = fact_sheet(app_conn, confirmer=world["approver"])
    confirmation = app_conn.execute("SELECT id FROM fact_confirmations WHERE fact_sheet_id = %s", (sheet,)).fetchone()[0]
    with violates(app_conn, "decision_record_append_only"):
        app_conn.execute("UPDATE fact_confirmations SET decision = 'corrected' WHERE id = %s", (confirmation,))
    with violates(app_conn, "decision_record_append_only"):
        app_conn.execute("DELETE FROM fact_confirmations WHERE id = %s", (confirmation,))
    with violates(app_conn, "decision_record_append_only"):
        app_conn.execute("UPDATE fact_sheets SET document_ref = 'lain' WHERE id = %s", (sheet,))
    with violates(app_conn, "decision_record_append_only"):
        app_conn.execute("UPDATE fact_sheets SET approved_at = now() WHERE id = %s", (sheet,))
    with violates(app_conn, "decision_record_append_only"):
        app_conn.execute("UPDATE facts SET value = 'tidak' WHERE fact_sheet_id = %s", (sheet,))
    with violates(app_conn, "fact_sheet_frozen"):
        add_fact(app_conn, sheet, "facility.spa")
    with violates(app_conn, "fact_sheet_frozen"):
        answer(app_conn, sheet, "facility.pool-private", world["approver"])
    draft_sheet = fact_sheet(app_conn, approved=False, confirmer=world["approver"])
    approve_sheet(app_conn, draft_sheet, world["approver"])  # belum disetujui: boleh disetujui sekali


# --- Fact sheet & konfirmasi fakta (migrasi 0005, kontrak core 0.8.0) -----------------------------


def test_new_fact_sheet_starts_unapproved_in_version_order(app_conn, world):
    with violates(app_conn, "fact_sheet_approval_flow"):
        insert(app_conn, "fact_sheets", client_code="CTH", version=1, document_ref="workspace://x", approved_at="2026-10-14T09:00:00+08:00")
    with violates(app_conn, "fact_sheet_version_sequence"):
        insert(app_conn, "fact_sheets", client_code="CTH", version=2, document_ref="workspace://x")
    assert insert(app_conn, "fact_sheets", client_code="CTH", version=1, document_ref="workspace://x")
    with violates(app_conn, "fact_sheet_version_sequence"):
        insert(app_conn, "fact_sheets", client_code="CTH", version=1, document_ref="workspace://x")
    with violates(app_conn, "ck_fact_sheets_refs"):
        insert(app_conn, "fact_sheets", client_code="CTH", version=2, document_ref="x" * 501)


def test_facts_follow_key_rules(app_conn, world):
    sheet = fact_sheet(app_conn, approved=False, confirmed=())
    with violates(app_conn, "fact_key_format"):  # kunci kategori lain
        insert(app_conn, "facts", fact_sheet_id=sheet, fact_key="facility.harga", category="price", label="Harga", value="1")
    with violates(app_conn, "ck_facts_category"):  # kesan bukan fakta
        insert(app_conn, "facts", fact_sheet_id=sheet, fact_key="experience.tenang", category="experience", label="x", value="y")
    with violates(app_conn, "ck_facts_text"):
        insert(app_conn, "facts", fact_sheet_id=sheet, fact_key="facility.spa", category="facility", label="  ", value="ada")
    add_fact(app_conn, sheet, "facility.spa")
    with violates(app_conn, "uq_facts_fact_sheet_id_fact_key"):
        add_fact(app_conn, sheet, "facility.spa")
    with violates(app_conn, "decision_record_append_only"):
        app_conn.execute("DELETE FROM facts WHERE fact_sheet_id = %s", (sheet,))
    with violates(app_conn, "decision_record_append_only"):  # fact sheet tidak pernah dihapus
        app_conn.execute("DELETE FROM fact_sheets WHERE id = %s", (sheet,))


def test_answers_come_from_the_client(app_conn, world):
    sheet = fact_sheet(app_conn, approved=False, confirmed=(), created_by=world["lead"])
    add_fact(app_conn, sheet, "price.weekday", value="Rp 2.500.000")
    with violates(app_conn, "fact_not_in_sheet"):
        answer(app_conn, sheet, "price.weekend", world["approver"])
    with violates(app_conn, "approval_role_mismatch"):  # staf agency bukan approver klien
        answer(app_conn, sheet, "price.weekday", world["author"])
    with violates(app_conn, "approval_role_mismatch"):  # peran wajib dicatat
        answer(app_conn, sheet, "price.weekday", world["approver"], role=None)
    with violates(app_conn, "approval_role_mismatch"):  # approver CTH bukan agency
        answer(app_conn, sheet, "price.weekday", world["approver"], role="content_lead", channel_ref="https://mail.contoh.test/1")
    with violates(app_conn, "approval_needs_written_evidence"):
        answer(app_conn, sheet, "price.weekday", world["reviewer"], role="content_lead")
    with violates(app_conn, "approval_by_author"):  # pembuat fact sheet tidak menjawab faktanya
        answer(app_conn, sheet, "price.weekday", world["lead"], role="content_lead", channel_ref="https://mail.contoh.test/1")
    with violates(app_conn, "fact_value_required"):
        answer(app_conn, sheet, "price.weekday", world["approver"], decision="corrected", value_after=" ")
    with violates(app_conn, "ck_fact_confirmations_channel_ref"):
        answer(app_conn, sheet, "price.weekday", world["reviewer"], role="content_lead", channel_ref="javascript:alert(1)")
    first = answer(app_conn, sheet, "price.weekday", world["approver"], value_after="diabaikan")
    second = answer(app_conn, sheet, "price.weekday", world["reviewer"], role="content_lead", decision="corrected",
                    value_after="Rp 2.750.000", channel_ref="https://mail.contoh.test/koreksi")
    rows = app_conn.execute("SELECT id, value_before, value_after FROM fact_confirmations WHERE id IN (%s, %s) ORDER BY id", (first, second)).fetchall()
    # value_before diisi database dari nilai fakta; konfirmasi "benar" tidak menyimpan nilai lain.
    assert rows == [(first, "Rp 2.500.000", None), (second, "Rp 2.500.000", "Rp 2.750.000")]


def test_fact_sheet_approval_rules(app_conn, world):
    empty = fact_sheet(app_conn, approved=False, confirmed=())
    with violates(app_conn, "fact_sheet_empty"):
        approve_sheet(app_conn, empty, world["approver"])
    sheet = fact_sheet(app_conn, approved=False, confirmed=("facility.pool-private",), confirmer=world["approver"], created_by=world["lead"])
    add_fact(app_conn, sheet, "capacity.guests", value="4")
    with violates(app_conn, "facts_unconfirmed"):
        approve_sheet(app_conn, sheet, world["approver"])
    answer(app_conn, sheet, "capacity.guests", world["approver"], decision="corrected", value_after="6")
    with violates(app_conn, "approval_role_mismatch"):
        approve_sheet(app_conn, sheet, world["author"], role="content_staff")
    with violates(app_conn, "approval_role_mismatch"):
        approve_sheet(app_conn, sheet, world["author"], role="client_approver")
    with violates(app_conn, "approval_needs_written_evidence"):
        approve_sheet(app_conn, sheet, world["reviewer"], role="content_lead")
    with violates(app_conn, "approval_by_author"):
        approve_sheet(app_conn, sheet, world["lead"], role="content_lead", ref="https://mail.contoh.test/ok")
    with violates(app_conn, "fact_sheet_approval_flow"):  # isi lain tidak bisa diubah, termasuk saat menyetujui
        app_conn.execute("UPDATE fact_sheets SET document_ref = 'workspace://lain', approved_at = now(), approved_by = %s, approved_by_role = 'client_approver' WHERE id = %s",
                         (world["approver"], sheet))
    with violates(app_conn, "fact_sheet_approval_flow"):
        app_conn.execute("UPDATE fact_sheets SET document_ref = 'workspace://lain' WHERE id = %s", (sheet,))
    with violates(app_conn, "fact_sheet_approval_flow"):  # mengubah tanpa menyetujui (mis. menyisipkan bukti) ditolak
        app_conn.execute("UPDATE fact_sheets SET approval_ref = 'https://mail.contoh.test/x' WHERE id = %s", (sheet,))
    approve_sheet(app_conn, sheet, world["reviewer"], role="content_lead", ref="https://mail.contoh.test/ok")
    assert app_conn.execute("SELECT approved_by_role, approval_ref FROM fact_sheets WHERE id = %s", (sheet,)).fetchone() == ("content_lead", "https://mail.contoh.test/ok")


def test_draft_approval_uses_client_answers(app_conn, world):
    """Rantai utuh di database: fakta dikoreksi klien → fact sheet disetujui → draft dengan klaim itu boleh L2."""
    sheet = fact_sheet(app_conn, confirmed=(), approved=False)
    add_fact(app_conn, sheet, "facility.pool-private")
    answer(app_conn, sheet, "facility.pool-private", world["approver"], decision="corrected", value_after="Kolam bersama")
    approve_sheet(app_conn, sheet, world["approver"])
    draft = factual_draft(app_conn, world, sheet)
    qa(app_conn, draft, world["reviewer"])
    assert approve(app_conn, draft, world["approver"], level="L2")


def test_decision_records_and_claims_are_append_only(app_conn, world):
    claim = insert(app_conn, "claims", draft_id=world["nyata"], text="Suasana tenang", category="experience", evidence_label="ASSUMPTION")
    with violates(app_conn, "draft_version_immutable"):
        app_conn.execute("UPDATE claims SET text = 'diubah' WHERE id = %s", (claim,))
    with violates(app_conn, "draft_version_immutable"):
        app_conn.execute("DELETE FROM claims WHERE id = %s", (claim,))
    record = qa(app_conn, world["nyata"], world["reviewer"])
    with violates(app_conn, "draft_version_immutable"):  # klaim tidak bisa ditambah setelah QA
        insert(app_conn, "claims", draft_id=world["nyata"], text="Klaim susulan", category="other", evidence_label="ASSUMPTION")
    approval = approve(app_conn, world["nyata"], world["approver"])
    for table, row in (("qa_records", record), ("approvals", approval)):
        with violates(app_conn, "decision_record_append_only"):
            app_conn.execute(f"UPDATE {table} SET draft_id = draft_id WHERE id = %s", (row,))
        with violates(app_conn, "decision_record_append_only"):
            app_conn.execute(f"DELETE FROM {table} WHERE id = %s", (row,))


def test_request_values_are_checked(app_conn, world):
    base = {"client_code": "CTH", "intent": "caption", "pillar": 1, "approval_min": "L1", "text": "x", "requested_by_role": "owner"}
    with violates(app_conn, "ck_requests_approval_min"):
        insert(app_conn, "requests", **{**base, "approval_min": "L4"})
    with violates(app_conn, "ck_requests_status"):
        insert(app_conn, "requests", **base, status="done")
    with violates(app_conn, "ck_requests_impact_risk_range"):
        insert(app_conn, "requests", **base, risk=4)
    with violates(app_conn, "ck_requests_text_length"):
        insert(app_conn, "requests", **{**base, "text": "x" * 4001})


def test_concurrent_new_version_and_approval_of_old_version(database, world_committed):
    """Draft v2 dibuat (belum commit) sementara approval v1 dikirim: approval menunggu kunci request, lalu ditolak."""
    import threading

    draft_v1, request, author, approver = world_committed
    a = psycopg.connect(database.app_conninfo)
    b = psycopg.connect(database.app_conninfo)
    result: dict = {}
    try:
        a.execute("INSERT INTO drafts (request_id, skill, version, content, mode, created_by) VALUES (%s, 'draft-caption', 2, 'v2', 'NYATA', %s)", (request, author))

        def approve_old():
            try:
                b.execute("INSERT INTO approvals (draft_id, level, decision, approver_id, approver_role, mode) VALUES (%s, 'L1', 'Approved', %s, 'client_approver', 'NYATA')", (draft_v1, approver))
                result["ok"] = True
            except psycopg.errors.IntegrityError as exc:
                result["error"] = str(exc)

        t = threading.Thread(target=approve_old)
        t.start()
        t.join(1.0)
        assert t.is_alive(), "approval harus menunggu kunci request"
        a.commit()
        t.join(5.0)
        assert "approval_version_mismatch" in result.get("error", ""), result
    finally:
        b.rollback()
        a.close()
        b.close()


@pytest.fixture()
def world_committed(database):
    """Data yang di-commit (untuk test dua koneksi); database test sekali pakai dihapus di akhir sesi."""
    tag = secrets_token()
    with psycopg.connect(database.app_conninfo) as c:
        insert(c, "clients", client_code=f"RC{tag}", vertical="accommodation", business_type="villa", approver_role="owner")
        author = insert(c, "users", display_name="Penulis", email=f"p{tag}@contoh.test")
        approver = insert(c, "users", display_name="Approver", email=f"a{tag}@contoh.test")
        c.execute("INSERT INTO memberships (user_id, scope, role, max_level) VALUES (%s, %s, 'client_approver', 'L3')", (approver, f"RC{tag}"))
        request = new_request(c, client=f"RC{tag}")
        draft = insert(c, "drafts", request_id=request, skill="draft-caption", version=1, content="v1", mode="NYATA", created_by=author)
        c.commit()
    yield draft, request, author, approver


def secrets_token() -> str:
    import secrets

    return secrets.token_hex(3).upper()


def test_upgrade_0003_to_0004_keeps_existing_data(database):
    """Database yang sudah berisi data versi 0003 (seed lama) bisa di-upgrade, dan data lama tetap terkunci aman."""
    from tests.conftest import TempDatabase

    db = TempDatabase(database.admin_url)
    try:
        db.alembic("upgrade", "0003")
        with psycopg.connect(db.app_conninfo) as c:
            insert(c, "clients", client_code="CTHVILLA", vertical="accommodation", business_type="villa", approver_role="owner")
            insert(c, "clients", client_code="CTHNYATA", vertical="accommodation", business_type="villa", approver_role="owner")
            req = insert(c, "requests", client_code="CTHVILLA", intent="caption", pillar=1, requested_by_role="seed-simulasi")
            draft = insert(c, "drafts", request_id=req, skill="draft-caption", version=1, content="lama", mode="SIMULASI", agent_id="caption-writer")
            insert(c, "claims", draft_id=draft, text="Kolam pribadi", category="facility", evidence_label="ASSUMPTION")
            insert(c, "claims", draft_id=draft, text="Suasana tenang", category="experience", evidence_label="ASSUMPTION")
            c.commit()
        db.alembic("upgrade", "head")
        with psycopg.connect(db.app_conninfo) as c:
            # Hanya kode seed eksplisit yang ditandai SIMULASI; klien lain berawalan CTH tetap nyata.
            assert dict(c.execute("SELECT client_code, simulation FROM clients").fetchall()) == {"CTHVILLA": True, "CTHNYATA": False}
            assert c.execute("SELECT approval_min, text, status FROM requests WHERE id = %s", (req,)).fetchone() == ("L3", "", "open")
            keys = sorted(r[0] or "-" for r in c.execute("SELECT fact_key FROM claims WHERE draft_id = %s", (draft,)))
            assert keys[0] == "-" and keys[1].startswith("facility.legacy-")
            # Kolom tanpa default: baris baru wajib diisi server.
            with violates(c, "null value"):
                c.execute("INSERT INTO requests (client_code, intent, pillar, requested_by_role) VALUES ('CTHNYATA', 'caption', 1, 'x')")
    finally:
        db.drop()


def test_upgrade_0004_to_0005_keeps_existing_fact_sheets(database):
    """Fact sheet versi 0004 (tanpa daftar fakta) tetap apa adanya; versi berikutnya mengikuti alur baru."""
    from tests.conftest import TempDatabase

    db = TempDatabase(database.admin_url)
    try:
        db.alembic("upgrade", "0004")
        with psycopg.connect(db.app_conninfo) as c:
            insert(c, "clients", client_code="CTHLAMA", vertical="accommodation", business_type="villa", approver_role="owner")
            approver = insert(c, "users", display_name="Approver", email="approver@contoh.test")
            c.execute("INSERT INTO memberships (user_id, scope, role, max_level) VALUES (%s, 'CTHLAMA', 'client_approver', 'L3')", (approver,))
            old = insert(c, "fact_sheets", client_code="CTHLAMA", version=1, document_ref="workspace://lama", approved_at="2026-10-01T09:00:00+08:00")
            insert(c, "fact_confirmations", fact_sheet_id=old, fact_key="facility.pool-private", decision="confirmed", confirmed_by=approver)
            c.commit()
        db.alembic("upgrade", "head")
        with psycopg.connect(db.app_conninfo) as c:
            row = c.execute("SELECT approved_at IS NOT NULL, approved_by, created_by FROM fact_sheets WHERE id = %s", (old,)).fetchone()
            assert row == (True, None, None)
            with violates(c, "decision_record_append_only"):  # tetap beku
                c.execute("UPDATE fact_sheets SET document_ref = 'workspace://baru' WHERE id = %s", (old,))
            new = insert(c, "fact_sheets", client_code="CTHLAMA", version=2, document_ref="workspace://baru")
            add_fact(c, new, "facility.pool-private")
            answer(c, new, "facility.pool-private", approver)
            approve_sheet(c, new, approver)
    finally:
        db.drop()
