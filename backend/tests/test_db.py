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
    request = new_request(c)
    sim_request = new_request(c, client="CTHSIM")
    nyata = insert(c, "drafts", request_id=request, skill="draft-caption", version=1, content="v1", mode="NYATA", created_by=author)
    sim = insert(c, "drafts", request_id=sim_request, skill="draft-caption", version=1, content="v1", mode="SIMULASI", agent_id="caption-writer")
    return {"author": author, "reviewer": reviewer, "approver": approver, "request": request, "sim_request": sim_request, "nyata": nyata, "sim": sim}


def approve(conn, draft, approver, level="L1", decision="Approved", mode="NYATA", role="client_approver", channel_ref=None):
    return insert(conn, "approvals", draft_id=draft, level=level, decision=decision, approver_id=approver, approver_role=role, mode=mode, channel_ref=channel_ref)


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
    base = {"draft_id": world["nyata"], "text": "Kolam renang pribadi", "category": "facility", "evidence_label": "DATA FINAL", "fact_key": "pool.private"}
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
            assert all(session.scalars(select(Client.simulation)))
            assert session.scalar(select(func.count()).select_from(Approval)) == 0
            session.rollback()
    finally:
        engine.dispose()


# --- Workflow (migrasi 0004, kontrak core 0.7.0) --------------------------------------------------


def fact_sheet(conn, client="CTH", approved=True, confirmed=("pool.private",), confirmer=None):
    sheet = insert(conn, "fact_sheets", client_code=client, version=1 + conn.execute("SELECT count(*) FROM fact_sheets WHERE client_code = %s", (client,)).fetchone()[0],
                   approved_at="2026-10-14T09:00:00+08:00" if approved else None, document_ref="workspace://fact-sheet")
    for key in confirmed:
        insert(conn, "fact_confirmations", fact_sheet_id=sheet, fact_key=key, decision="confirmed", confirmed_by=confirmer)
    return sheet


def factual_draft(conn, world, sheet=None, key="pool.private"):
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
    insert(app_conn, "claims", **base, fact_key="pool.private")
    insert(app_conn, "claims", **{**base, "category": "experience"})  # kesan/pengalaman: tanpa fact_key


def test_facts_unconfirmed_blocks_every_level(app_conn, world):
    """Approved (termasuk L1) ditolak sampai setiap fact_key klaim dikonfirmasi di fact sheet yang disetujui."""
    with violates(app_conn, "facts_unconfirmed"):  # draft tanpa fact sheet
        approve(app_conn, factual_draft(app_conn, world), world["approver"])
    unapproved = fact_sheet(app_conn, approved=False, confirmer=world["approver"])
    with violates(app_conn, "facts_unconfirmed"):
        approve(app_conn, factual_draft(app_conn, world, unapproved), world["approver"])
    sheet = fact_sheet(app_conn, confirmed=("pool.heated",), confirmer=world["approver"])
    with violates(app_conn, "facts_unconfirmed"):  # fakta lain dikonfirmasi, pool.private belum
        approve(app_conn, factual_draft(app_conn, world, sheet), world["approver"])
    good = fact_sheet(app_conn, confirmer=world["approver"])
    draft = factual_draft(app_conn, world, good)
    approve(app_conn, draft, world["approver"], decision="Revise")  # Revise/Rejected tidak butuh fakta
    approve(app_conn, draft, world["approver"])


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


def test_author_cannot_approve_own_draft(app_conn, world):
    with violates(app_conn, "approval_by_author"):
        approve(app_conn, world["nyata"], world["author"])


@pytest.mark.parametrize("role", ["owner", "content_lead"])
def test_agency_l2_approval_needs_written_client_evidence(app_conn, world, role):
    qa(app_conn, world["nyata"], world["reviewer"])
    with violates(app_conn, "approval_needs_written_evidence"):
        approve(app_conn, world["nyata"], world["approver"], level="L2", role=role, channel_ref="  ")
    approve(app_conn, world["nyata"], world["approver"], level="L1", role=role)  # L1: agency boleh tanpa bukti
    approve(app_conn, world["nyata"], world["approver"], level="L2", role=role, channel_ref="email://arsip/2026-10-14/approval-cth")


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
            insert(c, "clients", client_code="CTHOLD", vertical="accommodation", business_type="villa", approver_role="owner")
            req = insert(c, "requests", client_code="CTHOLD", intent="caption", pillar=1, requested_by_role="seed-simulasi")
            draft = insert(c, "drafts", request_id=req, skill="draft-caption", version=1, content="lama", mode="SIMULASI", agent_id="caption-writer")
            insert(c, "claims", draft_id=draft, text="Kolam pribadi", category="facility", evidence_label="ASSUMPTION")
            insert(c, "claims", draft_id=draft, text="Suasana tenang", category="experience", evidence_label="ASSUMPTION")
            c.commit()
        db.alembic("upgrade", "head")
        with psycopg.connect(db.app_conninfo) as c:
            assert c.execute("SELECT simulation FROM clients WHERE client_code = 'CTHOLD'").fetchone() == (True,)
            assert c.execute("SELECT approval_min, text, status FROM requests WHERE id = %s", (req,)).fetchone() == ("L3", "", "open")
            keys = sorted(r[0] or "-" for r in c.execute("SELECT fact_key FROM claims WHERE draft_id = %s", (draft,)))
            assert keys[0] == "-" and keys[1].startswith("legacy.")
            # Kolom tanpa default: baris baru wajib diisi server.
            with violates(c, "null value"):
                c.execute("INSERT INTO requests (client_code, intent, pillar, requested_by_role) VALUES ('CTHOLD', 'caption', 1, 'x')")
    finally:
        db.drop()
