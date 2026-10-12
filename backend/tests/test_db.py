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


@pytest.fixture()
def world(app_conn):
    """Klien SIMULASI + 3 user (pembuat, reviewer, approver) + request + draft NYATA & SIMULASI."""
    c = app_conn
    insert(c, "clients", client_code="CTH", vertical="accommodation", business_type="villa", approver_role="owner")
    author = insert(c, "users", display_name="Penulis Contoh", email="penulis@contoh.test")
    reviewer = insert(c, "users", display_name="Reviewer Contoh", email="reviewer@contoh.test")
    approver = insert(c, "users", display_name="Approver Contoh", email="approver@contoh.test")
    request = insert(c, "requests", client_code="CTH", intent="caption", pillar=1, requested_by_role="owner")
    nyata = insert(c, "drafts", request_id=request, skill="draft-caption", version=1, content="v1", mode="NYATA", created_by=author)
    sim = insert(c, "drafts", request_id=request, skill="draft-caption", version=2, content="v2", mode="SIMULASI", agent_id="caption-writer")
    return {"author": author, "reviewer": reviewer, "approver": approver, "request": request, "nyata": nyata, "sim": sim}


def approve(conn, draft, approver, level="L1", decision="Approved", mode="NYATA"):
    return insert(conn, "approvals", draft_id=draft, level=level, decision=decision, approver_id=approver, approver_role="client_approver", mode=mode)


def qa(conn, draft, reviewer, independent=True, result="Pass", gate="claim-verification"):
    return insert(conn, "qa_records", draft_id=draft, gate=gate, result=result, reviewer_id=reviewer, reviewer_role="content_lead", independent=independent)


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
    qa(app_conn, draft, world["author"], independent=False)  # self-review: pre-check saja
    qa(app_conn, draft, world["reviewer"], result="Fail")
    qa(app_conn, draft, world["reviewer"], gate="content-review")
    with violates(app_conn, "approval_needs_independent_review"):
        approve(app_conn, draft, approver, level=level)
    qa(app_conn, draft, world["reviewer"], result="Pass")
    approve(app_conn, draft, approver, level=level)


def test_l1_does_not_need_independent_review(app_conn, world):
    approve(app_conn, world["nyata"], world["approver"], level="L1")


def test_reviewer_cannot_review_own_draft(app_conn, world):
    with violates(app_conn, "qa_reviewer_is_author"):
        qa(app_conn, world["nyata"], world["author"], independent=True)


def test_agent_review_is_never_independent(app_conn, world):
    with violates(app_conn, "independent_is_human"):
        insert(app_conn, "qa_records", draft_id=world["sim"], gate="claim-verification", result="Pass", reviewer_role="agent", independent=True)


def test_data_final_claim_needs_source_and_date(app_conn, world):
    base = {"draft_id": world["nyata"], "text": "Kolam renang pribadi", "category": "facility", "evidence_label": "DATA FINAL"}
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
    insert(app_conn, "drafts", request_id=world["request"], skill="draft-caption", version=3, content="revisi", mode="NYATA", created_by=world["author"])


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
    values = {"user_id": world["approver"], "scope": scope, "role": role, "max_level": "L2"}
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
            assert session.scalar(select(func.count()).select_from(Approval)) == 0
            session.rollback()
    finally:
        engine.dispose()
