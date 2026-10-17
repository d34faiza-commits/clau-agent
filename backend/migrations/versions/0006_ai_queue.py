"""Antrean AI Tahap 2: ai_jobs, ai_calls, ai_budgets (kontrak core 0.9.0, AI-BOUNDARY 1.4.0).

Aturan (pesan berawalan kode aturan, SQLSTATE 23514, seperti 0001/0004/0005):
- ai_job_active: satu job queued/running per request (indeks unik parsial).
- request_closed: job baru hanya untuk request open/in_progress.
- ai_job_transition: job baru selalu queued; transisi queued → running/cancelled/failed (atau dijadwal ulang),
  running → queued (retry)/succeeded/failed; job selesai beku; kolom identitas job tidak bisa diubah.
- ai_job_draft_mismatch: job succeeded menunjuk draft agent (created_by NULL, agent_id sama) dari request yang sama.
- ai_record_append_only: ai_jobs tidak dihapus; ai_calls tidak diubah/dihapus (juga hak ubah dicabut dari role
  aplikasi, seperti audit_log).
- ai_draft_without_job: draft agent untuk klien NYATA hanya dari job AI yang sedang running untuk request itu.
  Draft agent SIMULASI (seed pilot) tetap boleh.
- Rule 08 untuk draft AI: peminta job = pembuat (qa_reviewer_is_author / approval_by_author), dan draft agent untuk
  klien NYATA minimal L2 (claim verification independen manusia wajib).

Revision ID: 0006
Revises: 0005
Create Date: 2026-10-16
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = '0006'
down_revision = '0005'
branch_labels = None
depends_on = None

ERROR_CODES = ("provider_error", "provider_unavailable", "refused", "invalid_output", "budget_exceeded", "request_closed",
               "fact_sheet_missing", "worker_timeout", "ai_disabled", "cancelled_by_user")
SLUG_RE = "^[a-z0-9]+(-[a-z0-9]+)*$"

RULES_SQL = r"""
CREATE FUNCTION clau_ai_job_rules() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE req_status text; req_intent text; d record;
BEGIN
  IF TG_OP = 'DELETE' THEN
    RAISE EXCEPTION 'ai_record_append_only: job AI tidak bisa dihapus' USING ERRCODE = 'check_violation';
  END IF;
  IF TG_OP = 'INSERT' THEN
    IF NEW.status <> 'queued' OR NEW.attempts <> 0 OR NEW.locked_at IS NOT NULL OR NEW.locked_by IS NOT NULL THEN
      RAISE EXCEPTION 'ai_job_transition: job baru harus queued' USING ERRCODE = 'check_violation';
    END IF;
    SELECT status, intent INTO req_status, req_intent FROM requests WHERE id = NEW.request_id;
    IF req_status NOT IN ('open', 'in_progress') THEN
      RAISE EXCEPTION 'request_closed: request sudah selesai' USING ERRCODE = 'check_violation';
    END IF;
    IF req_intent IS DISTINCT FROM NEW.intent THEN
      RAISE EXCEPTION 'ai_job_transition: intent job harus sama dengan request' USING ERRCODE = 'check_violation';
    END IF;
    RETURN NEW;
  END IF;
  -- UPDATE
  IF OLD.status IN ('succeeded', 'failed', 'cancelled') THEN
    RAISE EXCEPTION 'ai_job_transition: job yang sudah selesai tidak bisa diubah' USING ERRCODE = 'check_violation';
  END IF;
  IF (NEW.request_id, NEW.agent_id, NEW.intent, NEW.kind, NEW.requested_by, NEW.created_at, NEW.max_attempts)
     IS DISTINCT FROM (OLD.request_id, OLD.agent_id, OLD.intent, OLD.kind, OLD.requested_by, OLD.created_at, OLD.max_attempts) THEN
    RAISE EXCEPTION 'ai_job_transition: identitas job tidak bisa diubah' USING ERRCODE = 'check_violation';
  END IF;
  -- queued → queued hanya untuk menjadwal ulang (run_after), percobaan tidak berubah.
  IF NOT ((OLD.status = 'queued' AND NEW.status IN ('running', 'cancelled', 'failed'))
       OR (OLD.status = 'queued' AND NEW.status = 'queued' AND NEW.attempts = OLD.attempts)
       OR (OLD.status = 'running' AND NEW.status IN ('queued', 'succeeded', 'failed'))) THEN
    RAISE EXCEPTION 'ai_job_transition: % -> % tidak diizinkan', OLD.status, NEW.status USING ERRCODE = 'check_violation';
  END IF;
  IF NEW.attempts < OLD.attempts OR (NEW.status = 'running' AND NEW.attempts <> OLD.attempts + 1) THEN
    RAISE EXCEPTION 'ai_job_transition: percobaan hanya bertambah satu saat job diambil' USING ERRCODE = 'check_violation';
  END IF;
  IF NEW.status = 'succeeded' THEN
    SELECT request_id, created_by, agent_id INTO d FROM drafts WHERE id = NEW.draft_id;
    IF d.request_id IS DISTINCT FROM NEW.request_id OR d.created_by IS NOT NULL OR d.agent_id IS DISTINCT FROM NEW.agent_id THEN
      RAISE EXCEPTION 'ai_job_draft_mismatch: draft hasil bukan draft agent dari request ini' USING ERRCODE = 'check_violation';
    END IF;
  END IF;
  RETURN NEW;
END $$;
CREATE TRIGGER trg_ai_jobs_rules BEFORE INSERT OR UPDATE OR DELETE ON ai_jobs
  FOR EACH ROW EXECUTE FUNCTION clau_ai_job_rules();

CREATE FUNCTION clau_ai_record_append_only() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  RAISE EXCEPTION 'ai_record_append_only: catatan AI tidak bisa diubah atau dihapus' USING ERRCODE = 'check_violation';
END $$;
CREATE TRIGGER trg_ai_calls_append_only BEFORE UPDATE OR DELETE ON ai_calls
  FOR EACH ROW EXECUTE FUNCTION clau_ai_record_append_only();
CREATE TRIGGER trg_ai_calls_no_truncate BEFORE TRUNCATE ON ai_calls
  FOR EACH STATEMENT EXECUTE FUNCTION clau_ai_record_append_only();
CREATE TRIGGER trg_ai_jobs_no_truncate BEFORE TRUNCATE ON ai_jobs
  FOR EACH STATEMENT EXECUTE FUNCTION clau_ai_record_append_only();

-- Draft agent (created_by NULL) untuk klien NYATA hanya dari job AI yang sedang berjalan untuk request itu.
CREATE FUNCTION clau_draft_agent_needs_job() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF NEW.created_by IS NULL AND NEW.mode = 'NYATA' AND NOT EXISTS (
       SELECT 1 FROM ai_jobs j
       WHERE j.request_id = NEW.request_id AND j.status = 'running' AND j.agent_id = NEW.agent_id) THEN
    RAISE EXCEPTION 'ai_draft_without_job: draft agent untuk klien nyata hanya dari job AI yang berjalan'
      USING ERRCODE = 'check_violation';
  END IF;
  RETURN NEW;
END $$;
CREATE TRIGGER trg_drafts_agent_needs_job BEFORE INSERT ON drafts
  FOR EACH ROW EXECUTE FUNCTION clau_draft_agent_needs_job();

-- Rule 08 untuk draft AI: peminta job (ai_jobs.requested_by) = pembuat draft agent. Ia tidak boleh menjadi reviewer
-- independen maupun memutuskan approval draft itu (draft agent punya created_by NULL, jadi aturan 0001/0004 saja tidak
-- menangkapnya; temuan audit 2026-10-16).
CREATE FUNCTION clau_ai_draft_requester(draft_id bigint) RETURNS bigint LANGUAGE sql STABLE AS $$
  SELECT j.requested_by FROM ai_jobs j JOIN drafts d ON d.id = j.draft_id
   WHERE j.draft_id = $1 AND d.created_by IS NULL
$$;
CREATE FUNCTION clau_qa_not_ai_requester() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF NEW.independent AND NEW.reviewer_id IS NOT NULL AND NEW.reviewer_id = clau_ai_draft_requester(NEW.draft_id) THEN
    RAISE EXCEPTION 'qa_reviewer_is_author: peminta draft AI tidak boleh menjadi reviewer independen'
      USING ERRCODE = 'check_violation';
  END IF;
  RETURN NEW;
END $$;
CREATE TRIGGER trg_qa_records_not_ai_requester BEFORE INSERT OR UPDATE ON qa_records
  FOR EACH ROW EXECUTE FUNCTION clau_qa_not_ai_requester();
CREATE FUNCTION clau_approval_not_ai_requester() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF NEW.approver_id = clau_ai_draft_requester(NEW.draft_id) THEN
    RAISE EXCEPTION 'approval_by_author: peminta draft AI tidak boleh memutuskan approval draft itu'
      USING ERRCODE = 'check_violation';
  END IF;
  RETURN NEW;
END $$;
CREATE TRIGGER trg_approvals_not_ai_requester BEFORE INSERT ON approvals
  FOR EACH ROW EXECUTE FUNCTION clau_approval_not_ai_requester();

-- Draft agent untuk klien NYATA minimal L2: selalu butuh claim verification independen oleh manusia. AI fact-check
-- hanya melihat klaim yang dilaporkan model; isi draft (klaim yang tidak dilaporkan) tetap wajib dibaca manusia.
CREATE OR REPLACE FUNCTION clau_draft_min_level(d drafts, req requests) RETURNS text LANGUAGE plpgsql STABLE AS $$
BEGIN
  IF req.approval_min = 'L1' AND (
       EXISTS (SELECT 1 FROM claims WHERE draft_id = d.id AND fact_key IS NOT NULL)
       OR (d.created_by IS NULL AND d.mode = 'NYATA')) THEN
    RETURN 'L2';
  END IF;
  RETURN req.approval_min;
END $$;

-- Seperti audit_log: hak ubah/hapus ai_calls dan hapus ai_jobs dicabut dari semua role selain pemilik.
DO $$
DECLARE r record;
BEGIN
  FOR r IN SELECT DISTINCT grantee FROM information_schema.role_table_grants
           WHERE table_schema = 'public' AND table_name = 'ai_calls'
             AND privilege_type IN ('UPDATE', 'DELETE', 'TRUNCATE') AND grantee <> current_user
  LOOP
    EXECUTE format('REVOKE UPDATE, DELETE, TRUNCATE ON ai_calls FROM %I', r.grantee);
  END LOOP;
  FOR r IN SELECT DISTINCT grantee FROM information_schema.role_table_grants
           WHERE table_schema = 'public' AND table_name = 'ai_jobs'
             AND privilege_type IN ('DELETE', 'TRUNCATE') AND grantee <> current_user
  LOOP
    EXECUTE format('REVOKE DELETE, TRUNCATE ON ai_jobs FROM %I', r.grantee);
  END LOOP;
END $$;
"""

DOWN_SQL = """
-- Kembalikan level minimum 0004 (tanpa aturan draft agent).
CREATE OR REPLACE FUNCTION clau_draft_min_level(d drafts, req requests) RETURNS text LANGUAGE plpgsql STABLE AS $$
BEGIN
  IF req.approval_min = 'L1' AND EXISTS (SELECT 1 FROM claims WHERE draft_id = d.id AND fact_key IS NOT NULL) THEN
    RETURN 'L2';
  END IF;
  RETURN req.approval_min;
END $$;
DROP TRIGGER IF EXISTS trg_approvals_not_ai_requester ON approvals;
DROP FUNCTION IF EXISTS clau_approval_not_ai_requester();
DROP TRIGGER IF EXISTS trg_qa_records_not_ai_requester ON qa_records;
DROP FUNCTION IF EXISTS clau_qa_not_ai_requester();
DROP FUNCTION IF EXISTS clau_ai_draft_requester(bigint);
DROP TRIGGER IF EXISTS trg_drafts_agent_needs_job ON drafts;
DROP FUNCTION IF EXISTS clau_draft_agent_needs_job();
DROP FUNCTION IF EXISTS clau_ai_record_append_only() CASCADE;
DROP FUNCTION IF EXISTS clau_ai_job_rules() CASCADE;
"""


def upgrade() -> None:
    codes = ", ".join(f"'{c}'" for c in ERROR_CODES)
    op.create_table(
        'ai_jobs',
        sa.Column('id', sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column('request_id', sa.BigInteger(), nullable=False),
        sa.Column('agent_id', sa.Text(), nullable=False),
        sa.Column('intent', sa.Text(), nullable=False),
        sa.Column('kind', sa.Text(), server_default='draft', nullable=False),
        sa.Column('status', sa.Text(), server_default='queued', nullable=False),
        sa.Column('attempts', sa.SmallInteger(), server_default='0', nullable=False),
        sa.Column('max_attempts', sa.SmallInteger(), server_default='3', nullable=False),
        sa.Column('run_after', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('locked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('locked_by', sa.Text(), nullable=True),
        sa.Column('error_code', sa.Text(), nullable=True),
        sa.Column('fact_sheet_id', sa.BigInteger(), nullable=True),
        sa.Column('draft_id', sa.BigInteger(), nullable=True),
        sa.Column('requested_by', sa.BigInteger(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("status IN ('queued', 'running', 'succeeded', 'failed', 'cancelled')", name=op.f('ck_ai_jobs_status')),
        sa.CheckConstraint("kind IN ('draft')", name=op.f('ck_ai_jobs_kind')),
        sa.CheckConstraint(f"error_code IS NULL OR error_code IN ({codes})", name=op.f('ck_ai_jobs_error_code')),
        sa.CheckConstraint(f"agent_id ~ '{SLUG_RE}' AND intent ~ '{SLUG_RE}'", name=op.f('ck_ai_jobs_ids_format')),
        sa.CheckConstraint("max_attempts BETWEEN 1 AND 5 AND attempts BETWEEN 0 AND max_attempts", name=op.f('ck_ai_jobs_attempts_range')),
        sa.CheckConstraint("locked_by IS NULL OR char_length(locked_by) <= 100", name=op.f('ck_ai_jobs_locked_by_length')),
        sa.CheckConstraint(
            "(status IN ('queued', 'running') AND finished_at IS NULL AND draft_id IS NULL AND error_code IS NULL)"
            " OR (status = 'succeeded' AND finished_at IS NOT NULL AND draft_id IS NOT NULL AND error_code IS NULL)"
            " OR (status = 'failed' AND finished_at IS NOT NULL AND draft_id IS NULL AND error_code IS NOT NULL)"
            " OR (status = 'cancelled' AND finished_at IS NOT NULL AND draft_id IS NULL)",
            name=op.f('ck_ai_jobs_status_fields')),
        sa.ForeignKeyConstraint(['request_id'], ['requests.id'], name=op.f('fk_ai_jobs_request_id_requests')),
        sa.ForeignKeyConstraint(['fact_sheet_id'], ['fact_sheets.id'], name=op.f('fk_ai_jobs_fact_sheet_id_fact_sheets')),
        sa.ForeignKeyConstraint(['draft_id'], ['drafts.id'], name=op.f('fk_ai_jobs_draft_id_drafts')),
        sa.ForeignKeyConstraint(['requested_by'], ['users.id'], name=op.f('fk_ai_jobs_requested_by_users')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_ai_jobs')),
        sa.UniqueConstraint('draft_id', name=op.f('uq_ai_jobs_draft_id')),
    )
    op.create_index(op.f('ix_ai_jobs_request_id'), 'ai_jobs', ['request_id'])
    op.create_index(op.f('ix_ai_jobs_requested_by'), 'ai_jobs', ['requested_by'])
    op.create_index('uq_ai_jobs_one_active', 'ai_jobs', ['request_id'], unique=True,
                    postgresql_where=sa.text("status IN ('queued', 'running')"))
    op.create_index('ix_ai_jobs_queue', 'ai_jobs', ['run_after'], postgresql_where=sa.text("status = 'queued'"))

    op.create_table(
        'ai_calls',
        sa.Column('id', sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column('job_id', sa.BigInteger(), nullable=False),
        sa.Column('provider', sa.Text(), nullable=False),
        sa.Column('model', sa.Text(), nullable=False),
        sa.Column('prompt_version', sa.Text(), nullable=False),
        sa.Column('input_tokens', sa.Integer(), server_default='0', nullable=False),
        sa.Column('output_tokens', sa.Integer(), server_default='0', nullable=False),
        sa.Column('cache_read_tokens', sa.Integer(), server_default='0', nullable=False),
        sa.Column('cache_write_tokens', sa.Integer(), server_default='0', nullable=False),
        sa.Column('cost_micro_usd', sa.BigInteger(), server_default='0', nullable=False),
        sa.Column('stop_reason', sa.Text(), nullable=True),
        sa.Column('provider_request_id', sa.Text(), nullable=True),
        sa.Column('latency_ms', sa.Integer(), server_default='0', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint(
            "input_tokens >= 0 AND output_tokens >= 0 AND cache_read_tokens >= 0 AND cache_write_tokens >= 0"
            " AND cost_micro_usd >= 0 AND latency_ms >= 0", name=op.f('ck_ai_calls_non_negative')),
        sa.CheckConstraint(
            "char_length(provider) BETWEEN 1 AND 50 AND char_length(model) BETWEEN 1 AND 100"
            " AND char_length(prompt_version) BETWEEN 1 AND 64 AND char_length(coalesce(stop_reason, '')) <= 50"
            " AND char_length(coalesce(provider_request_id, '')) <= 200", name=op.f('ck_ai_calls_text_length')),
        sa.ForeignKeyConstraint(['job_id'], ['ai_jobs.id'], name=op.f('fk_ai_calls_job_id_ai_jobs')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_ai_calls')),
    )
    op.create_index(op.f('ix_ai_calls_job_id'), 'ai_calls', ['job_id'])
    op.create_index('ix_ai_calls_created_at', 'ai_calls', ['created_at'])

    op.create_table(
        'ai_budgets',
        sa.Column('scope', sa.Text(), nullable=False),
        sa.Column('month', sa.Date(), nullable=False),
        sa.Column('limit_micro_usd', sa.BigInteger(), nullable=False),
        sa.Column('alert_at_pct', sa.SmallInteger(), server_default='80', nullable=False),
        sa.Column('updated_by', sa.BigInteger(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint("scope = 'global' OR scope ~ '^[A-Z0-9]{2,12}$'", name=op.f('ck_ai_budgets_scope')),
        sa.CheckConstraint("month = date_trunc('month', month)::date", name=op.f('ck_ai_budgets_month_first_day')),
        sa.CheckConstraint("limit_micro_usd > 0 AND limit_micro_usd <= 100000000000", name=op.f('ck_ai_budgets_limit_range')),
        sa.CheckConstraint("alert_at_pct BETWEEN 1 AND 100", name=op.f('ck_ai_budgets_alert_range')),
        sa.ForeignKeyConstraint(['updated_by'], ['users.id'], name=op.f('fk_ai_budgets_updated_by_users')),
        sa.PrimaryKeyConstraint('scope', 'month', name=op.f('pk_ai_budgets')),
    )
    op.execute(RULES_SQL)


def downgrade() -> None:
    op.execute(DOWN_SQL)
    op.drop_table('ai_budgets')
    op.drop_index('ix_ai_calls_created_at', table_name='ai_calls')
    op.drop_index(op.f('ix_ai_calls_job_id'), table_name='ai_calls')
    op.drop_table('ai_calls')
    op.drop_index('ix_ai_jobs_queue', table_name='ai_jobs')
    op.drop_index('uq_ai_jobs_one_active', table_name='ai_jobs')
    op.drop_index(op.f('ix_ai_jobs_requested_by'), table_name='ai_jobs')
    op.drop_index(op.f('ix_ai_jobs_request_id'), table_name='ai_jobs')
    op.drop_table('ai_jobs')
