"""Workflow request → draft → QA → approval (Tahap 1 PR 3, kontrak core 0.7.0).

Kolom baru: clients.simulation, requests.{approval_min, text, deadline, impact, risk, requested_by},
drafts.fact_sheet_id, claims.fact_key. Aturan baru ditegakkan database (trigger), sama seperti migrasi 0001:
pesan error berawalan kode aturan (SQLSTATE 23514) yang diteruskan API apa adanya.

Data lama (seed SIMULASI lokal) tetap valid: klaim fakta lama mendapat fact_key legacy.<id> (tidak pernah
terkonfirmasi, jadi tetap terkunci), requests lama mendapat approval_min L3 (paling ketat) dan text kosong.

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-14
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = '0004'
down_revision = '0003'
branch_labels = None
depends_on = None

FACTUAL = ("facility", "location", "price", "rating", "certification", "halal-dietary", "food-beverage",
           "treatment", "capacity", "safety", "license", "itinerary")
FACTUAL_SQL = ", ".join(f"'{c}'" for c in FACTUAL)

RULES_SQL = """
-- Draft baru: request dikunci (urutan versi & approval tidak bisa balapan), versi = berikutnya, brief & fact sheet
-- milik klien request, mode mengikuti klien (SIMULASI tidak bisa dipilih bebas).
CREATE FUNCTION clau_draft_rules() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE req_client text; sim boolean; next_version integer; client_mode text;
BEGIN
  SELECT r.client_code, c.simulation INTO req_client, sim
    FROM requests r JOIN clients c ON c.client_code = r.client_code
   WHERE r.id = NEW.request_id FOR UPDATE OF r;
  SELECT coalesce(max(version), 0) + 1 INTO next_version FROM drafts WHERE request_id = NEW.request_id;
  IF NEW.version <> next_version THEN
    RAISE EXCEPTION 'draft_version_sequence: versi draft harus % (versi berikutnya di request ini)', next_version
      USING ERRCODE = 'check_violation';
  END IF;
  IF NEW.brief_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM briefs WHERE brief_id = NEW.brief_id AND client_code = req_client) THEN
    RAISE EXCEPTION 'draft_client_mismatch: brief bukan milik klien request ini' USING ERRCODE = 'check_violation';
  END IF;
  IF NEW.fact_sheet_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM fact_sheets WHERE id = NEW.fact_sheet_id AND client_code = req_client) THEN
    RAISE EXCEPTION 'draft_client_mismatch: fact sheet bukan milik klien request ini' USING ERRCODE = 'check_violation';
  END IF;
  client_mode := (CASE WHEN sim THEN 'SIMULASI' ELSE 'NYATA' END);
  IF NEW.mode IS DISTINCT FROM client_mode THEN
    RAISE EXCEPTION 'draft_mode_mismatch: mode draft harus mengikuti klien (%)', client_mode
      USING ERRCODE = 'check_violation';
  END IF;
  RETURN NEW;
END $$;
CREATE TRIGGER trg_drafts_rules BEFORE INSERT ON drafts FOR EACH ROW EXECUTE FUNCTION clau_draft_rules();

-- Isi versi draft tidak bisa diubah (0001), sekarang termasuk fact sheet dan pembuatnya.
CREATE OR REPLACE FUNCTION clau_draft_version_immutable() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF (NEW.content, NEW.version, NEW.mode, NEW.request_id, NEW.brief_id, NEW.skill, NEW.fact_sheet_id, NEW.created_by, NEW.agent_id)
     IS DISTINCT FROM (OLD.content, OLD.version, OLD.mode, OLD.request_id, OLD.brief_id, OLD.skill, OLD.fact_sheet_id, OLD.created_by, OLD.agent_id) THEN
    RAISE EXCEPTION 'draft_version_immutable: isi draft versi % tidak bisa diubah; simpan sebagai versi baru', OLD.version
      USING ERRCODE = 'check_violation';
  END IF;
  RETURN NEW;
END $$;

-- Klaim bagian dari isi versi draft: tidak bisa diubah/dihapus, dan tidak bisa ditambah setelah draft di-QA/di-approve.
CREATE FUNCTION clau_claims_immutable() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF TG_OP <> 'INSERT' OR EXISTS (SELECT 1 FROM qa_records WHERE draft_id = NEW.draft_id)
                       OR EXISTS (SELECT 1 FROM approvals WHERE draft_id = NEW.draft_id) THEN
    RAISE EXCEPTION 'draft_version_immutable: klaim draft tidak bisa diubah; simpan sebagai versi baru'
      USING ERRCODE = 'check_violation';
  END IF;
  RETURN NEW;
END $$;
CREATE TRIGGER trg_claims_immutable BEFORE INSERT OR UPDATE OR DELETE ON claims
  FOR EACH ROW EXECUTE FUNCTION clau_claims_immutable();

-- QA dan approval adalah catatan keputusan: append-only (rule 08: approval tertulis dan dapat ditelusuri).
CREATE FUNCTION clau_decision_record_append_only() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  RAISE EXCEPTION 'decision_record_append_only: % tidak bisa diubah atau dihapus; catat keputusan baru', TG_TABLE_NAME
    USING ERRCODE = 'check_violation';
END $$;
CREATE TRIGGER trg_qa_records_append_only BEFORE UPDATE OR DELETE ON qa_records
  FOR EACH ROW EXECUTE FUNCTION clau_decision_record_append_only();
CREATE TRIGGER trg_approvals_append_only BEFORE UPDATE OR DELETE ON approvals
  FOR EACH ROW EXECUTE FUNCTION clau_decision_record_append_only();

-- Approval (0001: mode & review independen) + aturan 0.7.0. Request dikunci dulu agar draft versi baru yang
-- dibuat bersamaan tidak lolos cek "versi terbaru".
CREATE OR REPLACE FUNCTION clau_approval_rules() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE d drafts%ROWTYPE; req requests%ROWTYPE; missing text;
BEGIN
  SELECT * INTO d FROM drafts WHERE id = NEW.draft_id;
  SELECT * INTO req FROM requests WHERE id = d.request_id FOR UPDATE;
  IF NEW.mode IS DISTINCT FROM d.mode THEN
    RAISE EXCEPTION 'approval_mode_mismatch: mode approval (%) harus sama dengan mode draft (%)', NEW.mode, d.mode
      USING ERRCODE = 'check_violation';
  END IF;
  IF NEW.decision <> 'Approved' THEN
    RETURN NEW;
  END IF;
  IF array_position(ARRAY['L1','L2','L3'], NEW.level) < array_position(ARRAY['L1','L2','L3'], req.approval_min) THEN
    RAISE EXCEPTION 'approval_level_too_low: intent % butuh approval minimal %', req.intent, req.approval_min
      USING ERRCODE = 'check_violation';
  END IF;
  IF d.created_by IS NOT NULL AND d.created_by = NEW.approver_id THEN
    RAISE EXCEPTION 'approval_by_author: pembuat draft tidak boleh menyetujui drafnya sendiri'
      USING ERRCODE = 'check_violation';
  END IF;
  IF NEW.level IN ('L2', 'L3') AND NEW.approver_role IN ('owner', 'content_lead', 'content_staff')
     AND coalesce(btrim(NEW.channel_ref), '') = '' THEN
    RAISE EXCEPTION 'approval_needs_written_evidence: approval % oleh agency wajib bukti tertulis klien (channel_ref)', NEW.level
      USING ERRCODE = 'check_violation';
  END IF;
  IF NEW.level IN ('L2', 'L3') AND NOT EXISTS (
       SELECT 1 FROM qa_records q
       WHERE q.draft_id = NEW.draft_id AND q.gate = 'claim-verification' AND q.independent
         AND q.result IN ('Pass', 'Conditional')) THEN
    RAISE EXCEPTION 'approval_needs_independent_review: approval % butuh claim verification independen yang lulus', NEW.level
      USING ERRCODE = 'check_violation';
  END IF;
  IF EXISTS (SELECT 1 FROM drafts WHERE request_id = d.request_id AND version > d.version) THEN
    RAISE EXCEPTION 'approval_version_mismatch: draft versi % bukan versi terbaru request ini', d.version
      USING ERRCODE = 'check_violation';
  END IF;
  SELECT string_agg(DISTINCT c.fact_key, ', ') INTO missing
    FROM claims c
   WHERE c.draft_id = NEW.draft_id AND c.fact_key IS NOT NULL
     AND NOT EXISTS (
       SELECT 1 FROM fact_sheets fs JOIN fact_confirmations fc ON fc.fact_sheet_id = fs.id
        WHERE fs.id = d.fact_sheet_id AND fs.approved_at IS NOT NULL
          AND fc.fact_key = c.fact_key AND fc.decision IN ('confirmed', 'corrected'));
  IF missing IS NOT NULL THEN
    RAISE EXCEPTION 'facts_unconfirmed: fakta belum dikonfirmasi di fact sheet yang disetujui: %', missing
      USING ERRCODE = 'check_violation';
  END IF;
  RETURN NEW;
END $$;
"""

# Versi 0001 untuk downgrade.
OLD_RULES_SQL = """
DROP TRIGGER IF EXISTS trg_drafts_rules ON drafts;
DROP TRIGGER IF EXISTS trg_claims_immutable ON claims;
DROP TRIGGER IF EXISTS trg_qa_records_append_only ON qa_records;
DROP TRIGGER IF EXISTS trg_approvals_append_only ON approvals;
DROP FUNCTION IF EXISTS clau_draft_rules();
DROP FUNCTION IF EXISTS clau_claims_immutable();
DROP FUNCTION IF EXISTS clau_decision_record_append_only();
CREATE OR REPLACE FUNCTION clau_draft_version_immutable() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF (NEW.content, NEW.version, NEW.mode, NEW.request_id, NEW.brief_id, NEW.skill)
     IS DISTINCT FROM (OLD.content, OLD.version, OLD.mode, OLD.request_id, OLD.brief_id, OLD.skill) THEN
    RAISE EXCEPTION 'draft_version_immutable: isi draft versi % tidak bisa diubah; simpan sebagai versi baru', OLD.version
      USING ERRCODE = 'check_violation';
  END IF;
  RETURN NEW;
END $$;
CREATE OR REPLACE FUNCTION clau_approval_rules() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE draft_mode text;
BEGIN
  SELECT mode INTO draft_mode FROM drafts WHERE id = NEW.draft_id;
  IF NEW.mode IS DISTINCT FROM draft_mode THEN
    RAISE EXCEPTION 'approval_mode_mismatch: mode approval (%) harus sama dengan mode draft (%)', NEW.mode, draft_mode
      USING ERRCODE = 'check_violation';
  END IF;
  IF NEW.decision = 'Approved' AND NEW.level IN ('L2', 'L3') AND NOT EXISTS (
       SELECT 1 FROM qa_records q
       WHERE q.draft_id = NEW.draft_id AND q.gate = 'claim-verification' AND q.independent
         AND q.result IN ('Pass', 'Conditional')) THEN
    RAISE EXCEPTION 'approval_needs_independent_review: approval % butuh claim verification independen yang lulus', NEW.level
      USING ERRCODE = 'check_violation';
  END IF;
  RETURN NEW;
END $$;
"""


def upgrade() -> None:
    op.add_column('clients', sa.Column('simulation', sa.Boolean(), server_default='false', nullable=False))
    # Klien seed fiktif (kode berawalan CTH = "Contoh", app/db/seed.py) ditandai SIMULASI.
    op.execute("UPDATE clients SET simulation = true WHERE client_code LIKE 'CTH%'")

    op.add_column('requests', sa.Column('approval_min', sa.Text(), server_default='L3', nullable=False))
    op.add_column('requests', sa.Column('text', sa.Text(), server_default='', nullable=False))
    op.add_column('requests', sa.Column('deadline', sa.Date(), nullable=True))
    op.add_column('requests', sa.Column('impact', sa.SmallInteger(), server_default='1', nullable=False))
    op.add_column('requests', sa.Column('risk', sa.SmallInteger(), server_default='1', nullable=False))
    op.add_column('requests', sa.Column('requested_by', sa.BigInteger(), nullable=True))
    # Default hanya untuk mengisi baris lama; baris baru wajib diisi server (dari registry & body).
    op.alter_column('requests', 'approval_min', server_default=None)
    op.alter_column('requests', 'text', server_default=None)
    op.create_foreign_key(op.f('fk_requests_requested_by_users'), 'requests', 'users', ['requested_by'], ['id'])
    op.create_index(op.f('ix_requests_requested_by'), 'requests', ['requested_by'], unique=False)
    op.create_index('ix_requests_created_at', 'requests', ['created_at'], unique=False)
    op.create_check_constraint(op.f('ck_requests_approval_min'), 'requests', "approval_min IN ('L1', 'L2', 'L3')")
    op.create_check_constraint(op.f('ck_requests_status'), 'requests', "status IN ('open', 'in_progress', 'approved', 'rejected', 'closed')")
    op.create_check_constraint(op.f('ck_requests_impact_risk_range'), 'requests', 'impact BETWEEN 0 AND 3 AND risk BETWEEN 0 AND 3')
    op.create_check_constraint(op.f('ck_requests_text_length'), 'requests', 'char_length(text) <= 4000')

    op.add_column('drafts', sa.Column('fact_sheet_id', sa.BigInteger(), nullable=True))
    op.create_foreign_key(op.f('fk_drafts_fact_sheet_id_fact_sheets'), 'drafts', 'fact_sheets', ['fact_sheet_id'], ['id'])
    op.create_index(op.f('ix_drafts_fact_sheet_id'), 'drafts', ['fact_sheet_id'], unique=False)

    op.add_column('claims', sa.Column('fact_key', sa.Text(), nullable=True))
    op.create_check_constraint(
        op.f('ck_claims_fact_key_format'), 'claims',
        "fact_key IS NULL OR (fact_key ~ '^[a-z0-9]+([._-][a-z0-9]+)*$' AND char_length(fact_key) <= 64)",
    )
    # Klaim fakta lama (seed SIMULASI lokal) diberi kunci legacy.<id>: tidak pernah ada di fact sheet, jadi
    # approval-nya tetap terkunci (facts_unconfirmed) sampai dibuat versi draft baru dengan fact_key sungguhan.
    op.execute(f"UPDATE claims SET fact_key = 'legacy.' || id WHERE fact_key IS NULL AND category IN ({FACTUAL_SQL})")
    op.create_check_constraint(op.f('ck_claims_fact_key_required'), 'claims', f"fact_key IS NOT NULL OR NOT (category IN ({FACTUAL_SQL}))")

    op.create_index('ix_fact_confirmations_sheet_key', 'fact_confirmations', ['fact_sheet_id', 'fact_key'], unique=False)
    op.execute(RULES_SQL)


def downgrade() -> None:
    op.execute(OLD_RULES_SQL)
    op.drop_index('ix_fact_confirmations_sheet_key', table_name='fact_confirmations')
    op.drop_constraint(op.f('ck_claims_fact_key_required'), 'claims', type_='check')
    op.drop_constraint(op.f('ck_claims_fact_key_format'), 'claims', type_='check')
    op.drop_column('claims', 'fact_key')
    op.drop_index(op.f('ix_drafts_fact_sheet_id'), table_name='drafts')
    op.drop_constraint(op.f('fk_drafts_fact_sheet_id_fact_sheets'), 'drafts', type_='foreignkey')
    op.drop_column('drafts', 'fact_sheet_id')
    for ck in ('text_length', 'impact_risk_range', 'status', 'approval_min'):
        op.drop_constraint(op.f(f'ck_requests_{ck}'), 'requests', type_='check')
    op.drop_index('ix_requests_created_at', table_name='requests')
    op.drop_index(op.f('ix_requests_requested_by'), table_name='requests')
    op.drop_constraint(op.f('fk_requests_requested_by_users'), 'requests', type_='foreignkey')
    for col in ('requested_by', 'risk', 'impact', 'deadline', 'text', 'approval_min'):
        op.drop_column('requests', col)
    op.drop_column('clients', 'simulation')
