"""Skema awal: 15 tabel core/shared/database-schema.md + Constraint Wajib di database.

CHECK constraint ikut tabel (dari app/db/models.py). Aturan yang melibatkan tabel lain memakai trigger
(fungsi clau_*), dan audit_log dibuat append-only. Semua error aturan memakai SQLSTATE 23514
(check_violation) dengan pesan berawalan kode aturan, agar API bisa memetakannya ke error kontrak.

Revision ID: 0001
Revises:
Create Date: 2026-10-12
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = '0001'
down_revision = None
branch_labels = None
depends_on = None


# Constraint Wajib yang melibatkan lebih dari satu tabel (core/shared/database-schema.md).
RULES_SQL = """
-- Reviewer independen tidak boleh pembuat draft (rule 08). Agent sudah ditolak oleh CHECK
-- ck_qa_records_independent_is_human.
CREATE FUNCTION clau_qa_reviewer_not_author() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF NEW.independent AND EXISTS (SELECT 1 FROM drafts WHERE id = NEW.draft_id AND created_by = NEW.reviewer_id) THEN
    RAISE EXCEPTION 'qa_reviewer_is_author: pembuat draft tidak boleh menjadi reviewer independen'
      USING ERRCODE = 'check_violation';
  END IF;
  RETURN NEW;
END $$;
CREATE TRIGGER trg_qa_records_reviewer_not_author BEFORE INSERT OR UPDATE ON qa_records
  FOR EACH ROW EXECUTE FUNCTION clau_qa_reviewer_not_author();

-- Approval: mode sama dengan draft yang disetujui; L2/L3 Approved butuh claim verification independen
-- yang lulus (Pass, atau Conditional = pengecualian terkontrol dengan approval tertulis, qa/content-review.md).
CREATE FUNCTION clau_approval_rules() RETURNS trigger LANGUAGE plpgsql AS $$
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
CREATE TRIGGER trg_approvals_rules BEFORE INSERT OR UPDATE ON approvals
  FOR EACH ROW EXECUTE FUNCTION clau_approval_rules();

-- Tidak ada catatan tayang tanpa approval Approved untuk draft (versi) yang sama.
CREATE FUNCTION clau_publication_requires_approval() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM approvals WHERE draft_id = NEW.draft_id AND decision = 'Approved') THEN
    RAISE EXCEPTION 'publication_without_approval: draft % belum punya approval Approved', NEW.draft_id
      USING ERRCODE = 'check_violation';
  END IF;
  RETURN NEW;
END $$;
CREATE TRIGGER trg_publications_requires_approval BEFORE INSERT OR UPDATE ON publications
  FOR EACH ROW EXECUTE FUNCTION clau_publication_requires_approval();

-- Approval terikat ke versi draft: isi versi yang sudah tersimpan tidak bisa diubah; revisi = baris baru.
CREATE FUNCTION clau_draft_version_immutable() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF (NEW.content, NEW.version, NEW.mode, NEW.request_id, NEW.brief_id, NEW.skill)
     IS DISTINCT FROM (OLD.content, OLD.version, OLD.mode, OLD.request_id, OLD.brief_id, OLD.skill) THEN
    RAISE EXCEPTION 'draft_version_immutable: isi draft versi % tidak bisa diubah; simpan sebagai versi baru', OLD.version
      USING ERRCODE = 'check_violation';
  END IF;
  RETURN NEW;
END $$;
CREATE TRIGGER trg_drafts_version_immutable BEFORE UPDATE ON drafts
  FOR EACH ROW EXECUTE FUNCTION clau_draft_version_immutable();

-- audit_log append-only, juga untuk pemilik tabel.
CREATE FUNCTION clau_audit_log_append_only() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  RAISE EXCEPTION 'audit_log_append_only: audit_log tidak bisa diubah atau dihapus'
    USING ERRCODE = 'check_violation';
END $$;
CREATE TRIGGER trg_audit_log_no_update_delete BEFORE UPDATE OR DELETE ON audit_log
  FOR EACH ROW EXECUTE FUNCTION clau_audit_log_append_only();
CREATE TRIGGER trg_audit_log_no_truncate BEFORE TRUNCATE ON audit_log
  FOR EACH STATEMENT EXECUTE FUNCTION clau_audit_log_append_only();

-- Role aplikasi mendapat SELECT/INSERT/UPDATE/DELETE lewat default privileges (app/db/bootstrap.py);
-- untuk audit_log hak ubah/hapus dicabut dari semua role selain pemilik.
DO $$
DECLARE r record;
BEGIN
  FOR r IN SELECT DISTINCT grantee FROM information_schema.role_table_grants
           WHERE table_schema = 'public' AND table_name = 'audit_log'
             AND privilege_type IN ('UPDATE', 'DELETE', 'TRUNCATE') AND grantee <> current_user
  LOOP
    EXECUTE format('REVOKE UPDATE, DELETE, TRUNCATE ON audit_log FROM %I', r.grantee);
  END LOOP;
END $$;
"""

DROP_RULES_SQL = """
DROP FUNCTION IF EXISTS clau_audit_log_append_only() CASCADE;
DROP FUNCTION IF EXISTS clau_draft_version_immutable() CASCADE;
DROP FUNCTION IF EXISTS clau_publication_requires_approval() CASCADE;
DROP FUNCTION IF EXISTS clau_approval_rules() CASCADE;
DROP FUNCTION IF EXISTS clau_qa_reviewer_not_author() CASCADE;
"""


def upgrade() -> None:
    op.create_table('clients',
    sa.Column('client_code', sa.Text(), nullable=False),
    sa.Column('vertical', sa.Text(), nullable=False),
    sa.Column('business_type', sa.Text(), nullable=False),
    sa.Column('location_area', sa.Text(), nullable=True),
    sa.Column('approver_role', sa.Text(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("client_code ~ '^[A-Z0-9]{2,12}$'", name=op.f('ck_clients_client_code_format')),
    sa.CheckConstraint("vertical IN ('accommodation', 'food-beverage', 'spa-wellness', 'experience', 'wedding-event', 'travel-tour')", name=op.f('ck_clients_vertical')),
    sa.PrimaryKeyConstraint('client_code', name=op.f('pk_clients'))
    )
    op.create_table('users',
    sa.Column('id', sa.BigInteger(), sa.Identity(always=True), nullable=False),
    sa.Column('display_name', sa.Text(), nullable=False),
    sa.Column('email', sa.Text(), nullable=False),
    sa.Column('locale', sa.Text(), server_default='id', nullable=False),
    sa.Column('timezone', sa.Text(), server_default='Asia/Makassar', nullable=False),
    sa.Column('salutation', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("email ~ '^[^@[:space:]]+@[^@[:space:]]+$'", name=op.f('ck_users_email_format')),
    sa.CheckConstraint("locale IN ('id', 'en')", name=op.f('ck_users_locale')),
    sa.CheckConstraint("timezone IN ('Asia/Jakarta', 'Asia/Makassar', 'Asia/Jayapura')", name=op.f('ck_users_timezone')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_users'))
    )
    op.create_index('uq_users_email_lower', 'users', [sa.literal_column('lower(email)')], unique=True)
    op.create_table('audit_log',
    sa.Column('id', sa.BigInteger(), sa.Identity(always=True), nullable=False),
    sa.Column('actor_id', sa.BigInteger(), nullable=True),
    sa.Column('action', sa.Text(), nullable=False),
    sa.Column('object_type', sa.Text(), nullable=False),
    sa.Column('object_id', sa.Text(), nullable=False),
    sa.Column('meta', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['actor_id'], ['users.id'], name=op.f('fk_audit_log_actor_id_users')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_audit_log'))
    )
    op.create_index(op.f('ix_audit_log_actor_id'), 'audit_log', ['actor_id'], unique=False)
    op.create_index('ix_audit_log_object', 'audit_log', ['object_type', 'object_id'], unique=False)
    op.create_table('briefs',
    sa.Column('brief_id', sa.Text(), nullable=False),
    sa.Column('client_code', sa.Text(), nullable=False),
    sa.Column('schema_version', sa.Text(), nullable=False),
    sa.Column('payload', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('status', sa.Text(), server_default='draft', nullable=False),
    sa.CheckConstraint("brief_id ~ '^[A-Z0-9]{2,12}-[0-9]{6}-[0-9]{2}$'", name=op.f('ck_briefs_brief_id_format')),
    sa.CheckConstraint("jsonb_typeof(payload) = 'object'", name=op.f('ck_briefs_payload_object')),
    sa.CheckConstraint("split_part(brief_id, '-', 1) = client_code", name=op.f('ck_briefs_brief_id_client')),
    sa.ForeignKeyConstraint(['client_code'], ['clients.client_code'], name=op.f('fk_briefs_client_code_clients')),
    sa.PrimaryKeyConstraint('brief_id', name=op.f('pk_briefs'))
    )
    op.create_index(op.f('ix_briefs_client_code'), 'briefs', ['client_code'], unique=False)
    op.create_table('consent_refs',
    sa.Column('id', sa.BigInteger(), sa.Identity(always=True), nullable=False),
    sa.Column('client_code', sa.Text(), nullable=False),
    sa.Column('consent_ref', sa.Text(), nullable=False),
    sa.Column('scope', sa.Text(), nullable=False),
    sa.Column('valid_until', sa.Date(), nullable=True),
    sa.ForeignKeyConstraint(['client_code'], ['clients.client_code'], name=op.f('fk_consent_refs_client_code_clients')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_consent_refs'))
    )
    op.create_index(op.f('ix_consent_refs_client_code'), 'consent_refs', ['client_code'], unique=False)
    op.create_table('fact_sheets',
    sa.Column('id', sa.BigInteger(), sa.Identity(always=True), nullable=False),
    sa.Column('client_code', sa.Text(), nullable=False),
    sa.Column('version', sa.Integer(), nullable=False),
    sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('document_ref', sa.Text(), nullable=False),
    sa.CheckConstraint('version >= 1', name=op.f('ck_fact_sheets_version_positive')),
    sa.ForeignKeyConstraint(['client_code'], ['clients.client_code'], name=op.f('fk_fact_sheets_client_code_clients')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_fact_sheets')),
    sa.UniqueConstraint('client_code', 'version', name=op.f('uq_fact_sheets_client_code_version'))
    )
    op.create_index(op.f('ix_fact_sheets_client_code'), 'fact_sheets', ['client_code'], unique=False)
    op.create_table('memberships',
    sa.Column('user_id', sa.BigInteger(), nullable=False),
    sa.Column('scope', sa.Text(), nullable=False),
    sa.Column('role', sa.Text(), nullable=False),
    sa.Column('max_level', sa.Text(), nullable=False),
    sa.CheckConstraint("NOT (role IN ('owner', 'content_lead', 'content_staff')) OR scope = 'agency'", name=op.f('ck_memberships_agency_role_scope')),
    sa.CheckConstraint("max_level IN ('L1', 'L2', 'L3')", name=op.f('ck_memberships_max_level')),
    sa.CheckConstraint("role <> 'client_approver' OR scope <> 'agency'", name=op.f('ck_memberships_client_approver_scope')),
    sa.CheckConstraint("role IN ('owner', 'content_lead', 'content_staff', 'viewer', 'client_approver')", name=op.f('ck_memberships_role')),
    sa.CheckConstraint("scope = 'agency' OR scope ~ '^[A-Z0-9]{2,12}$'", name=op.f('ck_memberships_scope_format')),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_memberships_user_id_users')),
    sa.PrimaryKeyConstraint('user_id', 'scope', name=op.f('pk_memberships'))
    )
    op.create_table('notifications',
    sa.Column('id', sa.BigInteger(), sa.Identity(always=True), nullable=False),
    sa.Column('user_id', sa.BigInteger(), nullable=False),
    sa.Column('type', sa.Text(), nullable=False),
    sa.Column('object_ref', sa.Text(), nullable=False),
    sa.Column('channel', sa.Text(), nullable=False),
    sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('read_at', sa.DateTime(timezone=True), nullable=True),
    sa.CheckConstraint("channel IN ('in_app', 'email', 'whatsapp')", name=op.f('ck_notifications_channel')),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_notifications_user_id_users')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_notifications'))
    )
    op.create_index(op.f('ix_notifications_user_id'), 'notifications', ['user_id'], unique=False)
    op.create_table('requests',
    sa.Column('id', sa.BigInteger(), sa.Identity(always=True), nullable=False),
    sa.Column('client_code', sa.Text(), nullable=False),
    sa.Column('intent', sa.Text(), nullable=False),
    sa.Column('pillar', sa.SmallInteger(), nullable=False),
    sa.Column('priority', sa.Text(), server_default='Normal', nullable=False),
    sa.Column('status', sa.Text(), server_default='open', nullable=False),
    sa.Column('requested_by_role', sa.Text(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("intent ~ '^[a-z0-9]+(-[a-z0-9]+)*$'", name=op.f('ck_requests_intent_format')),
    sa.CheckConstraint("priority IN ('Low', 'Normal', 'High', 'Urgent')", name=op.f('ck_requests_priority')),
    sa.CheckConstraint('pillar BETWEEN 1 AND 5', name=op.f('ck_requests_pillar_range')),
    sa.ForeignKeyConstraint(['client_code'], ['clients.client_code'], name=op.f('fk_requests_client_code_clients')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_requests'))
    )
    op.create_index(op.f('ix_requests_client_code'), 'requests', ['client_code'], unique=False)
    op.create_table('drafts',
    sa.Column('id', sa.BigInteger(), sa.Identity(always=True), nullable=False),
    sa.Column('request_id', sa.BigInteger(), nullable=False),
    sa.Column('brief_id', sa.Text(), nullable=True),
    sa.Column('skill', sa.Text(), nullable=False),
    sa.Column('version', sa.Integer(), nullable=False),
    sa.Column('content', sa.Text(), nullable=False),
    sa.Column('mode', sa.Text(), nullable=False),
    sa.Column('created_by', sa.BigInteger(), nullable=True),
    sa.Column('agent_id', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("agent_id IS NULL OR agent_id ~ '^[a-z0-9]+(-[a-z0-9]+)*$'", name=op.f('ck_drafts_agent_id_format')),
    sa.CheckConstraint("mode IN ('NYATA', 'SIMULASI')", name=op.f('ck_drafts_mode')),
    sa.CheckConstraint('created_by IS NOT NULL OR agent_id IS NOT NULL', name=op.f('ck_drafts_has_author')),
    sa.CheckConstraint('version >= 1', name=op.f('ck_drafts_version_positive')),
    sa.ForeignKeyConstraint(['brief_id'], ['briefs.brief_id'], name=op.f('fk_drafts_brief_id_briefs')),
    sa.ForeignKeyConstraint(['created_by'], ['users.id'], name=op.f('fk_drafts_created_by_users')),
    sa.ForeignKeyConstraint(['request_id'], ['requests.id'], name=op.f('fk_drafts_request_id_requests')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_drafts')),
    sa.UniqueConstraint('request_id', 'version', name=op.f('uq_drafts_request_id_version'))
    )
    op.create_index(op.f('ix_drafts_brief_id'), 'drafts', ['brief_id'], unique=False)
    op.create_index(op.f('ix_drafts_created_by'), 'drafts', ['created_by'], unique=False)
    op.create_index(op.f('ix_drafts_request_id'), 'drafts', ['request_id'], unique=False)
    op.create_table('fact_confirmations',
    sa.Column('id', sa.BigInteger(), sa.Identity(always=True), nullable=False),
    sa.Column('fact_sheet_id', sa.BigInteger(), nullable=False),
    sa.Column('fact_key', sa.Text(), nullable=False),
    sa.Column('value_before', sa.Text(), nullable=True),
    sa.Column('value_after', sa.Text(), nullable=True),
    sa.Column('decision', sa.Text(), nullable=False),
    sa.Column('confirmed_by', sa.BigInteger(), nullable=False),
    sa.Column('confirmed_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("decision IN ('confirmed', 'corrected')", name=op.f('ck_fact_confirmations_decision')),
    sa.ForeignKeyConstraint(['confirmed_by'], ['users.id'], name=op.f('fk_fact_confirmations_confirmed_by_users')),
    sa.ForeignKeyConstraint(['fact_sheet_id'], ['fact_sheets.id'], name=op.f('fk_fact_confirmations_fact_sheet_id_fact_sheets')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_fact_confirmations'))
    )
    op.create_index(op.f('ix_fact_confirmations_confirmed_by'), 'fact_confirmations', ['confirmed_by'], unique=False)
    op.create_index(op.f('ix_fact_confirmations_fact_sheet_id'), 'fact_confirmations', ['fact_sheet_id'], unique=False)
    op.create_table('approvals',
    sa.Column('id', sa.BigInteger(), sa.Identity(always=True), nullable=False),
    sa.Column('draft_id', sa.BigInteger(), nullable=False),
    sa.Column('level', sa.Text(), nullable=False),
    sa.Column('decision', sa.Text(), nullable=False),
    sa.Column('approver_id', sa.BigInteger(), nullable=False),
    sa.Column('approver_role', sa.Text(), nullable=False),
    sa.Column('channel_ref', sa.Text(), nullable=True),
    sa.Column('decided_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('mode', sa.Text(), nullable=False),
    sa.CheckConstraint("NOT (decision = 'Approved' AND mode = 'SIMULASI')", name=op.f('ck_approvals_simulasi_not_approved')),
    sa.CheckConstraint("decision IN ('Approved', 'Revise', 'Rejected')", name=op.f('ck_approvals_decision')),
    sa.CheckConstraint("level IN ('L1', 'L2', 'L3')", name=op.f('ck_approvals_level')),
    sa.CheckConstraint("mode IN ('NYATA', 'SIMULASI')", name=op.f('ck_approvals_mode')),
    sa.ForeignKeyConstraint(['approver_id'], ['users.id'], name=op.f('fk_approvals_approver_id_users')),
    sa.ForeignKeyConstraint(['draft_id'], ['drafts.id'], name=op.f('fk_approvals_draft_id_drafts')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_approvals'))
    )
    op.create_index(op.f('ix_approvals_approver_id'), 'approvals', ['approver_id'], unique=False)
    op.create_index(op.f('ix_approvals_draft_id'), 'approvals', ['draft_id'], unique=False)
    op.create_table('claims',
    sa.Column('id', sa.BigInteger(), sa.Identity(always=True), nullable=False),
    sa.Column('draft_id', sa.BigInteger(), nullable=False),
    sa.Column('text', sa.Text(), nullable=False),
    sa.Column('category', sa.Text(), nullable=False),
    sa.Column('evidence_label', sa.Text(), nullable=False),
    sa.Column('source', sa.Text(), nullable=True),
    sa.Column('source_date', sa.Date(), nullable=True),
    sa.Column('implied', sa.Boolean(), server_default='false', nullable=False),
    sa.CheckConstraint("category IN ('facility', 'location', 'price', 'rating', 'certification', 'halal-dietary', 'food-beverage', 'treatment', 'experience', 'capacity', 'safety', 'license', 'itinerary', 'other')", name=op.f('ck_claims_category')),
    sa.CheckConstraint("evidence_label <> 'DATA FINAL' OR (coalesce(btrim(source), '') <> '' AND source_date IS NOT NULL)", name=op.f('ck_claims_data_final_sourced')),
    sa.CheckConstraint("evidence_label IN ('DATA FINAL', 'ASSUMPTION', 'CLIENT CONFIRMATION', 'FIELD VERIFICATION', 'RISK', 'NEXT ACTION')", name=op.f('ck_claims_evidence_label')),
    sa.ForeignKeyConstraint(['draft_id'], ['drafts.id'], name=op.f('fk_claims_draft_id_drafts')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_claims'))
    )
    op.create_index(op.f('ix_claims_draft_id'), 'claims', ['draft_id'], unique=False)
    op.create_table('publications',
    sa.Column('id', sa.BigInteger(), sa.Identity(always=True), nullable=False),
    sa.Column('draft_id', sa.BigInteger(), nullable=False),
    sa.Column('channel', sa.Text(), nullable=False),
    sa.Column('published_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('url_ref', sa.Text(), nullable=True),
    sa.Column('published_by_role', sa.Text(), nullable=False),
    sa.ForeignKeyConstraint(['draft_id'], ['drafts.id'], name=op.f('fk_publications_draft_id_drafts')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_publications'))
    )
    op.create_index(op.f('ix_publications_draft_id'), 'publications', ['draft_id'], unique=False)
    op.create_table('qa_records',
    sa.Column('id', sa.BigInteger(), sa.Identity(always=True), nullable=False),
    sa.Column('draft_id', sa.BigInteger(), nullable=False),
    sa.Column('gate', sa.Text(), nullable=False),
    sa.Column('result', sa.Text(), nullable=False),
    sa.Column('reviewer_id', sa.BigInteger(), nullable=True),
    sa.Column('reviewer_role', sa.Text(), nullable=False),
    sa.Column('independent', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("gate IN ('claim-verification', 'content-review', 'privacy-rights-review', 'visual-ai-review', 'publication-checklist')", name=op.f('ck_qa_records_gate')),
    sa.CheckConstraint("result IN ('Pass', 'Conditional', 'Fail', 'N/A')", name=op.f('ck_qa_records_result')),
    sa.CheckConstraint('NOT independent OR reviewer_id IS NOT NULL', name=op.f('ck_qa_records_independent_is_human')),
    sa.ForeignKeyConstraint(['draft_id'], ['drafts.id'], name=op.f('fk_qa_records_draft_id_drafts')),
    sa.ForeignKeyConstraint(['reviewer_id'], ['users.id'], name=op.f('fk_qa_records_reviewer_id_users')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_qa_records'))
    )
    op.create_index(op.f('ix_qa_records_draft_id'), 'qa_records', ['draft_id'], unique=False)
    op.create_index(op.f('ix_qa_records_reviewer_id'), 'qa_records', ['reviewer_id'], unique=False)

    op.execute(RULES_SQL)

def downgrade() -> None:
    op.execute(DROP_RULES_SQL)
    op.drop_index(op.f('ix_qa_records_reviewer_id'), table_name='qa_records')
    op.drop_index(op.f('ix_qa_records_draft_id'), table_name='qa_records')
    op.drop_table('qa_records')
    op.drop_index(op.f('ix_publications_draft_id'), table_name='publications')
    op.drop_table('publications')
    op.drop_index(op.f('ix_claims_draft_id'), table_name='claims')
    op.drop_table('claims')
    op.drop_index(op.f('ix_approvals_draft_id'), table_name='approvals')
    op.drop_index(op.f('ix_approvals_approver_id'), table_name='approvals')
    op.drop_table('approvals')
    op.drop_index(op.f('ix_fact_confirmations_fact_sheet_id'), table_name='fact_confirmations')
    op.drop_index(op.f('ix_fact_confirmations_confirmed_by'), table_name='fact_confirmations')
    op.drop_table('fact_confirmations')
    op.drop_index(op.f('ix_drafts_request_id'), table_name='drafts')
    op.drop_index(op.f('ix_drafts_created_by'), table_name='drafts')
    op.drop_index(op.f('ix_drafts_brief_id'), table_name='drafts')
    op.drop_table('drafts')
    op.drop_index(op.f('ix_requests_client_code'), table_name='requests')
    op.drop_table('requests')
    op.drop_index(op.f('ix_notifications_user_id'), table_name='notifications')
    op.drop_table('notifications')
    op.drop_table('memberships')
    op.drop_index(op.f('ix_fact_sheets_client_code'), table_name='fact_sheets')
    op.drop_table('fact_sheets')
    op.drop_index(op.f('ix_consent_refs_client_code'), table_name='consent_refs')
    op.drop_table('consent_refs')
    op.drop_index(op.f('ix_briefs_client_code'), table_name='briefs')
    op.drop_table('briefs')
    op.drop_index('ix_audit_log_object', table_name='audit_log')
    op.drop_index(op.f('ix_audit_log_actor_id'), table_name='audit_log')
    op.drop_table('audit_log')
    op.drop_index('uq_users_email_lower', table_name='users')
    op.drop_table('users')
    op.drop_table('clients')
