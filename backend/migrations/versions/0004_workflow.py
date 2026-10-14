"""Workflow request → draft → QA → approval (Tahap 1 PR 3, kontrak core 0.7.0).

Kolom baru: clients.simulation, requests.{approval_min, text, deadline, impact, risk, requested_by},
drafts.fact_sheet_id, claims.fact_key. Aturan baru ditegakkan database (trigger), sama seperti migrasi 0001:
pesan error berawalan kode aturan (SQLSTATE 23514) yang diteruskan API apa adanya.

Data lama (seed SIMULASI lokal) tetap valid: klaim fakta lama mendapat fact_key <kategori>.legacy-<id> (tidak pernah
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
-- Request yang sudah selesai (approved/rejected/closed) tidak menerima draft atau keputusan baru: revisi setelah
-- selesai = request baru (jejak keputusan tidak tercampur).
CREATE FUNCTION clau_request_open(req requests) RETURNS void LANGUAGE plpgsql AS $$
BEGIN
  IF req.status NOT IN ('open', 'in_progress') THEN
    RAISE EXCEPTION 'request_closed: request % sudah %; buat request baru', req.id, req.status
      USING ERRCODE = 'check_violation';
  END IF;
END $$;

-- Draft baru: request dikunci (urutan versi & approval tidak bisa balapan), versi = berikutnya, brief & fact sheet
-- milik klien request, mode mengikuti klien (SIMULASI tidak bisa dipilih bebas).
CREATE FUNCTION clau_draft_rules() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE req requests%ROWTYPE; sim boolean; next_version integer; client_mode text;
BEGIN
  SELECT * INTO req FROM requests WHERE id = NEW.request_id FOR UPDATE;
  PERFORM clau_request_open(req);
  SELECT simulation INTO sim FROM clients WHERE client_code = req.client_code;
  SELECT coalesce(max(version), 0) + 1 INTO next_version FROM drafts WHERE request_id = NEW.request_id;
  IF NEW.version <> next_version THEN
    RAISE EXCEPTION 'draft_version_sequence: versi draft harus % (versi berikutnya di request ini)', next_version
      USING ERRCODE = 'check_violation';
  END IF;
  IF NEW.brief_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM briefs WHERE brief_id = NEW.brief_id AND client_code = req.client_code) THEN
    RAISE EXCEPTION 'draft_client_mismatch: brief bukan milik klien request ini' USING ERRCODE = 'check_violation';
  END IF;
  IF NEW.fact_sheet_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM fact_sheets WHERE id = NEW.fact_sheet_id AND client_code = req.client_code) THEN
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

-- Catatan keputusan & bukti append-only (rule 08: approval tertulis dan dapat ditelusuri): QA, approval, dan
-- konfirmasi fakta. Fact sheet yang sudah disetujui tidak bisa diubah isinya.
CREATE FUNCTION clau_decision_record_append_only() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  RAISE EXCEPTION 'decision_record_append_only: % tidak bisa diubah atau dihapus; catat keputusan baru', TG_TABLE_NAME
    USING ERRCODE = 'check_violation';
END $$;
CREATE TRIGGER trg_qa_records_append_only BEFORE UPDATE OR DELETE ON qa_records
  FOR EACH ROW EXECUTE FUNCTION clau_decision_record_append_only();
CREATE TRIGGER trg_approvals_append_only BEFORE UPDATE OR DELETE ON approvals
  FOR EACH ROW EXECUTE FUNCTION clau_decision_record_append_only();
CREATE TRIGGER trg_fact_confirmations_append_only BEFORE UPDATE OR DELETE ON fact_confirmations
  FOR EACH ROW EXECUTE FUNCTION clau_decision_record_append_only();
CREATE FUNCTION clau_fact_sheet_frozen() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF OLD.approved_at IS NOT NULL THEN
    RAISE EXCEPTION 'decision_record_append_only: fact sheet versi % sudah disetujui; buat versi baru', OLD.version
      USING ERRCODE = 'check_violation';
  END IF;
  RETURN CASE WHEN TG_OP = 'DELETE' THEN OLD ELSE NEW END;
END $$;
CREATE TRIGGER trg_fact_sheets_frozen BEFORE UPDATE OR DELETE ON fact_sheets
  FOR EACH ROW EXECUTE FUNCTION clau_fact_sheet_frozen();

-- Peran yang tercatat harus benar-benar peran user itu (bukan sekadar teks dari aplikasi).
CREATE FUNCTION clau_has_role(user_id bigint, scope text, role text) RETURNS boolean LANGUAGE sql STABLE AS $$
  SELECT EXISTS (SELECT 1 FROM memberships m WHERE m.user_id = $1 AND m.scope = $2 AND m.role = $3)
$$;

-- QA: peran reviewer sesuai membership agency; review independen hanya owner/content_lead (rule 08).
CREATE FUNCTION clau_qa_rules() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF NEW.reviewer_id IS NOT NULL AND NOT clau_has_role(NEW.reviewer_id, 'agency', NEW.reviewer_role) THEN
    RAISE EXCEPTION 'qa_role_mismatch: reviewer tidak punya peran % di agency', NEW.reviewer_role
      USING ERRCODE = 'check_violation';
  END IF;
  IF NEW.independent AND NEW.reviewer_id IS NOT NULL AND NEW.reviewer_role NOT IN ('owner', 'content_lead') THEN
    RAISE EXCEPTION 'independent_review_not_allowed: review independen hanya oleh owner/content lead'
      USING ERRCODE = 'check_violation';
  END IF;
  RETURN NEW;
END $$;
CREATE TRIGGER trg_qa_records_rules BEFORE INSERT ON qa_records FOR EACH ROW EXECUTE FUNCTION clau_qa_rules();

-- Level minimum efektif draft: minimum intent (router; risk 3 → L3 saat request dibuat), dinaikkan ke L2 bila draft
-- memuat klaim fakta (rule 08: harga, promo, klaim fasilitas = L2; L1 = konten rutin tanpa klaim baru).
CREATE FUNCTION clau_draft_min_level(d drafts, req requests) RETURNS text LANGUAGE plpgsql STABLE AS $$
BEGIN
  IF req.approval_min = 'L1' AND EXISTS (SELECT 1 FROM claims WHERE draft_id = d.id AND fact_key IS NOT NULL) THEN
    RETURN 'L2';
  END IF;
  RETURN req.approval_min;
END $$;

-- Approval (0001: mode & review independen) + aturan 0.7.0. Request dikunci dulu agar draft versi baru yang
-- dibuat bersamaan tidak lolos cek "versi terbaru". Cek peran, pembuat, dan level berlaku untuk SEMUA keputusan
-- (Revise/Rejected juga mengubah status request).
CREATE OR REPLACE FUNCTION clau_approval_rules() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE d drafts%ROWTYPE; req requests%ROWTYPE; min_level text; missing text; last_cv text;
BEGIN
  SELECT * INTO d FROM drafts WHERE id = NEW.draft_id;
  SELECT * INTO req FROM requests WHERE id = d.request_id FOR UPDATE;
  IF NEW.mode IS DISTINCT FROM d.mode THEN
    RAISE EXCEPTION 'approval_mode_mismatch: mode approval (%) harus sama dengan mode draft (%)', NEW.mode, d.mode
      USING ERRCODE = 'check_violation';
  END IF;
  PERFORM clau_request_open(req);
  IF NOT (
       (NEW.approver_role IN ('owner', 'content_lead') AND clau_has_role(NEW.approver_id, 'agency', NEW.approver_role))
    OR (NEW.approver_role = 'client_approver' AND clau_has_role(NEW.approver_id, req.client_code, 'client_approver'))) THEN
    RAISE EXCEPTION 'approval_role_mismatch: approver tidak punya peran % untuk klien ini', NEW.approver_role
      USING ERRCODE = 'check_violation';
  END IF;
  IF d.created_by IS NOT NULL AND d.created_by = NEW.approver_id THEN
    RAISE EXCEPTION 'approval_by_author: pembuat draft tidak boleh memutuskan approval drafnya sendiri'
      USING ERRCODE = 'check_violation';
  END IF;
  min_level := clau_draft_min_level(d, req);
  IF array_position(ARRAY['L1','L2','L3'], NEW.level) < array_position(ARRAY['L1','L2','L3'], min_level) THEN
    RAISE EXCEPTION 'approval_level_too_low: draft ini butuh approval minimal %', min_level
      USING ERRCODE = 'check_violation';
  END IF;
  IF NEW.decision <> 'Approved' THEN
    RETURN NEW;
  END IF;
  -- Rule 08: persetujuan selalu dari klien. Agency hanya mencatat persetujuan tertulis klien (bukti wajib).
  IF NEW.approver_role <> 'client_approver' AND coalesce(btrim(NEW.channel_ref), '') = '' THEN
    RAISE EXCEPTION 'approval_needs_written_evidence: approval oleh agency wajib bukti tertulis klien (channel_ref)'
      USING ERRCODE = 'check_violation';
  END IF;
  IF NEW.level IN ('L2', 'L3') THEN
    -- Yang berlaku = claim verification independen TERAKHIR (Fail setelah Pass membatalkan).
    SELECT q.result INTO last_cv FROM qa_records q
     WHERE q.draft_id = NEW.draft_id AND q.gate = 'claim-verification' AND q.independent
     ORDER BY q.created_at DESC, q.id DESC LIMIT 1;
    IF last_cv IS NULL OR last_cv NOT IN ('Pass', 'Conditional') THEN
      RAISE EXCEPTION 'approval_needs_independent_review: approval % butuh claim verification independen terakhir yang lulus', NEW.level
        USING ERRCODE = 'check_violation';
    END IF;
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

-- Tandai tayang (0001) diperketat: keputusan TERAKHIR untuk draft itu harus Approved, dan draft = versi terbaru.
CREATE OR REPLACE FUNCTION clau_publication_requires_approval() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE last_decision text;
BEGIN
  SELECT decision INTO last_decision FROM approvals WHERE draft_id = NEW.draft_id ORDER BY decided_at DESC, id DESC LIMIT 1;
  IF last_decision IS DISTINCT FROM 'Approved' OR EXISTS (
       SELECT 1 FROM drafts d JOIN drafts newer ON newer.request_id = d.request_id AND newer.version > d.version
        WHERE d.id = NEW.draft_id) THEN
    RAISE EXCEPTION 'publication_without_approval: draft % belum punya approval Approved yang berlaku', NEW.draft_id
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
DROP TRIGGER IF EXISTS trg_fact_confirmations_append_only ON fact_confirmations;
DROP TRIGGER IF EXISTS trg_fact_sheets_frozen ON fact_sheets;
DROP TRIGGER IF EXISTS trg_qa_records_rules ON qa_records;
DROP FUNCTION IF EXISTS clau_draft_rules();
DROP FUNCTION IF EXISTS clau_claims_immutable();
DROP FUNCTION IF EXISTS clau_decision_record_append_only();
DROP FUNCTION IF EXISTS clau_fact_sheet_frozen();
DROP FUNCTION IF EXISTS clau_qa_rules();
CREATE OR REPLACE FUNCTION clau_draft_version_immutable() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF (NEW.content, NEW.version, NEW.mode, NEW.request_id, NEW.brief_id, NEW.skill)
     IS DISTINCT FROM (OLD.content, OLD.version, OLD.mode, OLD.request_id, OLD.brief_id, OLD.skill) THEN
    RAISE EXCEPTION 'draft_version_immutable: isi draft versi % tidak bisa diubah; simpan sebagai versi baru', OLD.version
      USING ERRCODE = 'check_violation';
  END IF;
  RETURN NEW;
END $$;
CREATE OR REPLACE FUNCTION clau_publication_requires_approval() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM approvals WHERE draft_id = NEW.draft_id AND decision = 'Approved') THEN
    RAISE EXCEPTION 'publication_without_approval: draft % belum punya approval Approved', NEW.draft_id
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
DROP FUNCTION IF EXISTS clau_draft_min_level(drafts, requests);
DROP FUNCTION IF EXISTS clau_has_role(bigint, text, text);
DROP FUNCTION IF EXISTS clau_request_open(requests);
"""


def upgrade() -> None:
    op.add_column('clients', sa.Column('simulation', sa.Boolean(), server_default='false', nullable=False))
    # Klien seed fiktif (daftar eksplisit app/db/seed.py, bukan prefix: klien nyata tidak ikut tertandai).
    op.execute("UPDATE clients SET simulation = true WHERE client_code IN ('CTHVILLA', 'CTHCAFE', 'CTHWED', 'CTHTRIP')")

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
    # Klaim fakta lama (seed SIMULASI lokal) diberi kunci <kategori>.legacy-<id>: tidak pernah ada di fact sheet, jadi
    # approval-nya tetap terkunci (facts_unconfirmed) sampai dibuat versi draft baru dengan fact_key sungguhan.
    op.execute(f"UPDATE claims SET fact_key = category || '.legacy-' || id WHERE fact_key IS NULL AND category IN ({FACTUAL_SQL})")
    op.create_check_constraint(
        op.f('ck_claims_fact_key_required'), 'claims', f"NOT (category IN ({FACTUAL_SQL})) OR (fact_key IS NOT NULL AND split_part(fact_key, '.', 1) = category)"
    )

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
