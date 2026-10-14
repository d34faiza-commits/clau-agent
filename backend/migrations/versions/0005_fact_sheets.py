"""Fact sheet, konfirmasi fakta, dan persetujuan fact sheet (Tahap 1 PR 3b, kontrak core 0.8.0).

Tabel baru `facts` (daftar fakta per versi fact sheet). Kolom baru: fact_sheets.{created_by, created_at,
approved_by, approved_by_role, approval_ref}, fact_confirmations.{confirmed_by_role, channel_ref}.

Alur (rule 08, design/user-flow/client-portal-flow.md § Konfirmasi Fakta):
1. Agency membuat versi fact sheet beserta daftar fakta (belum disetujui).
2. Approver klien mengonfirmasi atau mengoreksi setiap fakta (atau owner/content lead mencatat jawaban tertulis
   klien dengan bukti).
3. Fact sheet disetujui setelah semua fakta dijawab; sesudah itu dibekukan (perubahan = versi baru).

Seperti 0001/0004, aturan ditegakkan trigger dengan pesan berawalan kode aturan (SQLSTATE 23514).

Data lama: fact sheet yang sudah ada tetap apa adanya (tanpa pembuat/penyetuju tercatat). Aturan baru hanya
berlaku untuk baris baru dan perubahan berikutnya.

Revision ID: 0005
Revises: 0004
Create Date: 2026-10-14
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = '0005'
down_revision = '0004'
branch_labels = None
depends_on = None

FACTUAL = ("facility", "location", "price", "rating", "certification", "halal-dietary", "food-beverage",
           "treatment", "capacity", "safety", "license", "itinerary")
FACTUAL_SQL = ", ".join(f"'{c}'" for c in FACTUAL)
# Tanpa spasi, karakter kontrol (termasuk C1), dan karakter format tak terlihat (zero-width, bidi override) yang
# bisa memalsukan tampilan link bukti.
INVISIBLE = "\u200b-\u200f\u202a-\u202e\u2060-\u2069\ufeff"
REF_RE = f"^(https://|mailto:|workspace://)[^[:space:][:cntrl:]\u0080-\u009f{INVISIBLE}]+$"

RULES_SQL = r"""
-- Peran pencatat jawaban klien: approver klien itu sendiri, atau owner/content lead agency yang mencatat
-- jawaban tertulis klien (bukti wajib). Dipakai untuk konfirmasi fakta dan persetujuan fact sheet.
CREATE FUNCTION clau_client_answer_role_ok(user_id bigint, client text, role text) RETURNS boolean LANGUAGE sql STABLE AS $$
  SELECT ($3 IN ('owner', 'content_lead') AND clau_has_role($1, 'agency', $3))
      OR ($3 = 'client_approver' AND clau_has_role($1, $2, 'client_approver'))
$$;

-- Fact sheet baru: belum disetujui, versi = berikutnya per klien (klien dikunci agar versi tidak balapan).
CREATE FUNCTION clau_fact_sheet_insert_rules() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE next_version integer;
BEGIN
  PERFORM 1 FROM clients WHERE client_code = NEW.client_code FOR NO KEY UPDATE;
  IF NEW.approved_at IS NOT NULL OR NEW.approved_by IS NOT NULL THEN
    RAISE EXCEPTION 'fact_sheet_approval_flow: fact sheet baru belum disetujui; setujui setelah semua fakta dikonfirmasi'
      USING ERRCODE = 'check_violation';
  END IF;
  SELECT coalesce(max(version), 0) + 1 INTO next_version FROM fact_sheets WHERE client_code = NEW.client_code;
  IF NEW.version <> next_version THEN
    RAISE EXCEPTION 'fact_sheet_version_sequence: versi fact sheet harus % (versi berikutnya klien ini)', next_version
      USING ERRCODE = 'check_violation';
  END IF;
  RETURN NEW;
END $$;
CREATE TRIGGER trg_fact_sheets_insert_rules BEFORE INSERT ON fact_sheets
  FOR EACH ROW EXECUTE FUNCTION clau_fact_sheet_insert_rules();

-- Perubahan fact sheet = hanya persetujuan (sekali). Sudah disetujui = beku. Tidak pernah dihapus (draft & jejak
-- konfirmasi merujuk ke versinya).
CREATE OR REPLACE FUNCTION clau_fact_sheet_frozen() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE missing text;
BEGIN
  IF TG_OP = 'DELETE' OR OLD.approved_at IS NOT NULL THEN
    RAISE EXCEPTION 'decision_record_append_only: fact sheet versi % tidak bisa diubah atau dihapus; buat versi baru', OLD.version
      USING ERRCODE = 'check_violation';
  END IF;
  IF (NEW.id, NEW.client_code, NEW.version, NEW.document_ref, NEW.created_by, NEW.created_at)
     IS DISTINCT FROM (OLD.id, OLD.client_code, OLD.version, OLD.document_ref, OLD.created_by, OLD.created_at)
     OR NEW.approved_at IS NULL THEN
    RAISE EXCEPTION 'fact_sheet_approval_flow: fact sheet hanya bisa disetujui; isi lain = versi baru'
      USING ERRCODE = 'check_violation';
  END IF;
  IF NEW.approved_by IS NULL OR NOT clau_client_answer_role_ok(NEW.approved_by, NEW.client_code, NEW.approved_by_role) THEN
    RAISE EXCEPTION 'approval_role_mismatch: penyetuju tidak punya peran % untuk klien ini', NEW.approved_by_role
      USING ERRCODE = 'check_violation';
  END IF;
  IF NEW.approved_by_role <> 'client_approver' AND coalesce(btrim(NEW.approval_ref), '') = '' THEN
    RAISE EXCEPTION 'approval_needs_written_evidence: persetujuan fact sheet oleh agency wajib bukti tertulis klien'
      USING ERRCODE = 'check_violation';
  END IF;
  IF OLD.created_by IS NOT NULL AND OLD.created_by = NEW.approved_by THEN
    RAISE EXCEPTION 'approval_by_author: pembuat fact sheet tidak boleh menyetujuinya'
      USING ERRCODE = 'check_violation';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM facts WHERE fact_sheet_id = OLD.id) THEN
    RAISE EXCEPTION 'fact_sheet_empty: fact sheet tanpa fakta tidak bisa disetujui' USING ERRCODE = 'check_violation';
  END IF;
  SELECT string_agg(f.fact_key, ', ' ORDER BY f.fact_key) INTO missing FROM facts f
   WHERE f.fact_sheet_id = OLD.id
     AND NOT EXISTS (SELECT 1 FROM fact_confirmations fc WHERE fc.fact_sheet_id = OLD.id AND fc.fact_key = f.fact_key);
  IF missing IS NOT NULL THEN
    RAISE EXCEPTION 'facts_unconfirmed: fakta belum dijawab klien: %', missing USING ERRCODE = 'check_violation';
  END IF;
  RETURN NEW;
END $$;

-- Fakta hanya ditambah selama fact sheet belum disetujui; isinya append-only (koreksi = jawaban klien, bukan edit).
CREATE FUNCTION clau_facts_rules() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE approved timestamptz;
BEGIN
  IF TG_OP <> 'INSERT' THEN
    RAISE EXCEPTION 'decision_record_append_only: fakta tidak bisa diubah atau dihapus; buat versi fact sheet baru'
      USING ERRCODE = 'check_violation';
  END IF;
  -- Kunci baris fact sheet (juga yang belum disetujui) agar tidak balapan dengan persetujuannya.
  SELECT approved_at INTO approved FROM fact_sheets WHERE id = NEW.fact_sheet_id FOR SHARE;
  IF approved IS NOT NULL THEN
    RAISE EXCEPTION 'fact_sheet_frozen: fact sheet sudah disetujui; buat versi baru' USING ERRCODE = 'check_violation';
  END IF;
  RETURN NEW;
END $$;
CREATE TRIGGER trg_facts_rules BEFORE INSERT OR UPDATE OR DELETE ON facts
  FOR EACH ROW EXECUTE FUNCTION clau_facts_rules();

-- Jawaban klien per fakta: fact sheet dikunci (tidak balapan dengan persetujuan), belum disetujui, fakta ada di
-- versi itu, peran sesuai membership, bukti tertulis bila dicatat agency, bukan pembuat fact sheet, koreksi
-- wajib nilai baru. value_before = nilai fakta saat dijawab.
CREATE FUNCTION clau_fact_confirmation_rules() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE sheet fact_sheets%ROWTYPE; fact_value text;
BEGIN
  SELECT * INTO sheet FROM fact_sheets WHERE id = NEW.fact_sheet_id FOR UPDATE;
  IF sheet.approved_at IS NOT NULL THEN
    RAISE EXCEPTION 'fact_sheet_frozen: fact sheet sudah disetujui; buat versi baru' USING ERRCODE = 'check_violation';
  END IF;
  SELECT value INTO fact_value FROM facts WHERE fact_sheet_id = NEW.fact_sheet_id AND fact_key = NEW.fact_key;
  IF NOT FOUND THEN
    RAISE EXCEPTION 'fact_not_in_sheet: fakta % tidak ada di fact sheet ini', NEW.fact_key USING ERRCODE = 'check_violation';
  END IF;
  IF NEW.confirmed_by_role IS NULL OR NOT clau_client_answer_role_ok(NEW.confirmed_by, sheet.client_code, NEW.confirmed_by_role) THEN
    RAISE EXCEPTION 'approval_role_mismatch: pengonfirmasi tidak punya peran % untuk klien ini', NEW.confirmed_by_role
      USING ERRCODE = 'check_violation';
  END IF;
  IF NEW.confirmed_by_role <> 'client_approver' AND coalesce(btrim(NEW.channel_ref), '') = '' THEN
    RAISE EXCEPTION 'approval_needs_written_evidence: konfirmasi fakta oleh agency wajib bukti tertulis klien'
      USING ERRCODE = 'check_violation';
  END IF;
  IF sheet.created_by IS NOT NULL AND sheet.created_by = NEW.confirmed_by THEN
    RAISE EXCEPTION 'approval_by_author: pembuat fact sheet tidak boleh mengonfirmasi faktanya'
      USING ERRCODE = 'check_violation';
  END IF;
  IF NEW.decision = 'corrected' AND coalesce(btrim(NEW.value_after), '') = '' THEN
    RAISE EXCEPTION 'fact_value_required: koreksi wajib berisi nilai yang benar' USING ERRCODE = 'check_violation';
  END IF;
  IF NEW.decision = 'corrected' AND btrim(NEW.value_after) = btrim(fact_value) THEN
    RAISE EXCEPTION 'fact_value_unchanged: koreksi sama dengan nilai awal; pilih "benar" bila nilainya sudah tepat'
      USING ERRCODE = 'check_violation';
  END IF;
  IF NEW.decision = 'confirmed' THEN
    NEW.value_after := NULL;
  END IF;
  NEW.value_before := fact_value;
  RETURN NEW;
END $$;
CREATE TRIGGER trg_fact_confirmations_rules BEFORE INSERT ON fact_confirmations
  FOR EACH ROW EXECUTE FUNCTION clau_fact_confirmation_rules();

-- Approved untuk draft berklaim fakta (melengkapi facts_unconfirmed 0004): fact sheet draft harus disetujui lewat
-- alur jawaban klien (bukan data 0004 tanpa penyetuju), setiap kunci ada di daftar faktanya, dan fact sheet itu
-- versi disetujui TERBARU klien (versi lama yang sudah dikoreksi tidak bisa dipakai lagi).
-- Nama trigger diurutkan setelah trg_approvals_rules (0004): pelanggaran level/peran dilaporkan lebih dulu.
CREATE FUNCTION clau_approval_fact_sheet_rules() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE d drafts%ROWTYPE; sheet fact_sheets%ROWTYPE; missing text;
BEGIN
  IF NEW.decision <> 'Approved' THEN
    RETURN NEW;
  END IF;
  SELECT * INTO d FROM drafts WHERE id = NEW.draft_id;
  IF NOT EXISTS (SELECT 1 FROM claims WHERE draft_id = d.id AND fact_key IS NOT NULL) THEN
    RETURN NEW;
  END IF;
  SELECT * INTO sheet FROM fact_sheets WHERE id = d.fact_sheet_id;
  IF sheet.id IS NULL OR sheet.approved_by IS NULL THEN
    RAISE EXCEPTION 'facts_unconfirmed: draft berklaim fakta butuh fact sheet yang disetujui klien'
      USING ERRCODE = 'check_violation';
  END IF;
  SELECT string_agg(DISTINCT c.fact_key, ', ') INTO missing FROM claims c
   WHERE c.draft_id = d.id AND c.fact_key IS NOT NULL
     AND NOT EXISTS (SELECT 1 FROM facts f WHERE f.fact_sheet_id = sheet.id AND f.fact_key = c.fact_key);
  IF missing IS NOT NULL THEN
    RAISE EXCEPTION 'facts_unconfirmed: fakta tidak ada di fact sheet draft: %', missing USING ERRCODE = 'check_violation';
  END IF;
  IF EXISTS (SELECT 1 FROM fact_sheets n WHERE n.client_code = sheet.client_code AND n.approved_at IS NOT NULL AND n.version > sheet.version) THEN
    RAISE EXCEPTION 'fact_sheet_superseded: fact sheet v% sudah digantikan versi yang lebih baru; buat draft baru dengan versi terbaru', sheet.version
      USING ERRCODE = 'check_violation';
  END IF;
  RETURN NEW;
END $$;
CREATE TRIGGER trg_approvals_rules_fact_sheet BEFORE INSERT ON approvals
  FOR EACH ROW EXECUTE FUNCTION clau_approval_fact_sheet_rules();
"""

DOWN_SQL = """
DROP TRIGGER IF EXISTS trg_approvals_rules_fact_sheet ON approvals;
DROP FUNCTION IF EXISTS clau_approval_fact_sheet_rules();
DROP TRIGGER IF EXISTS trg_fact_confirmations_rules ON fact_confirmations;
DROP TRIGGER IF EXISTS trg_facts_rules ON facts;
DROP TRIGGER IF EXISTS trg_fact_sheets_insert_rules ON fact_sheets;
DROP FUNCTION IF EXISTS clau_fact_confirmation_rules();
DROP FUNCTION IF EXISTS clau_facts_rules();
DROP FUNCTION IF EXISTS clau_fact_sheet_insert_rules();
-- Versi 0004.
CREATE OR REPLACE FUNCTION clau_fact_sheet_frozen() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF OLD.approved_at IS NOT NULL THEN
    RAISE EXCEPTION 'decision_record_append_only: fact sheet versi % sudah disetujui; buat versi baru', OLD.version
      USING ERRCODE = 'check_violation';
  END IF;
  RETURN CASE WHEN TG_OP = 'DELETE' THEN OLD ELSE NEW END;
END $$;
DROP FUNCTION IF EXISTS clau_client_answer_role_ok(bigint, text, text);
"""


def upgrade() -> None:
    op.add_column('fact_sheets', sa.Column('created_by', sa.BigInteger(), nullable=True))
    op.add_column('fact_sheets', sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False))
    op.add_column('fact_sheets', sa.Column('approved_by', sa.BigInteger(), nullable=True))
    op.add_column('fact_sheets', sa.Column('approved_by_role', sa.Text(), nullable=True))
    op.add_column('fact_sheets', sa.Column('approval_ref', sa.Text(), nullable=True))
    op.create_foreign_key(op.f('fk_fact_sheets_created_by_users'), 'fact_sheets', 'users', ['created_by'], ['id'])
    op.create_foreign_key(op.f('fk_fact_sheets_approved_by_users'), 'fact_sheets', 'users', ['approved_by'], ['id'])
    op.create_check_constraint(op.f('ck_fact_sheets_approved_by_role'), 'fact_sheets',
                               "approved_by_role IS NULL OR approved_by_role IN ('owner', 'content_lead', 'client_approver')")
    op.create_check_constraint(op.f('ck_fact_sheets_approval_complete'), 'fact_sheets',
                               "approved_by IS NULL OR (approved_at IS NOT NULL AND approved_by_role IS NOT NULL)")
    op.create_check_constraint(op.f('ck_fact_sheets_refs'), 'fact_sheets',
                               f"char_length(document_ref) <= 500 AND (approval_ref IS NULL OR (approval_ref ~ '{REF_RE}' AND char_length(approval_ref) <= 500))")

    op.create_table(
        'facts',
        sa.Column('id', sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column('fact_sheet_id', sa.BigInteger(), nullable=False),
        sa.Column('fact_key', sa.Text(), nullable=False),
        sa.Column('category', sa.Text(), nullable=False),
        sa.Column('label', sa.Text(), nullable=False),
        sa.Column('value', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint(f"category IN ({FACTUAL_SQL})", name=op.f('ck_facts_category')),
        sa.CheckConstraint("fact_key ~ '^[a-z0-9]+([._-][a-z0-9]+)*$' AND char_length(fact_key) <= 64 AND split_part(fact_key, '.', 1) = category AND strpos(fact_key, '.') > 0",
                           name=op.f('ck_facts_fact_key_format')),
        sa.CheckConstraint("btrim(label) <> '' AND char_length(label) <= 200 AND btrim(value) <> '' AND char_length(value) <= 1000",
                           name=op.f('ck_facts_text')),
        sa.ForeignKeyConstraint(['fact_sheet_id'], ['fact_sheets.id'], name=op.f('fk_facts_fact_sheet_id_fact_sheets')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_facts')),
        sa.UniqueConstraint('fact_sheet_id', 'fact_key', name=op.f('uq_facts_fact_sheet_id_fact_key')),
    )

    op.add_column('fact_confirmations', sa.Column('confirmed_by_role', sa.Text(), nullable=True))
    op.add_column('fact_confirmations', sa.Column('channel_ref', sa.Text(), nullable=True))
    op.create_check_constraint(op.f('ck_fact_confirmations_confirmed_by_role'), 'fact_confirmations',
                               "confirmed_by_role IS NULL OR confirmed_by_role IN ('owner', 'content_lead', 'client_approver')")
    op.create_check_constraint(op.f('ck_fact_confirmations_channel_ref'), 'fact_confirmations',
                               f"channel_ref IS NULL OR (channel_ref ~ '{REF_RE}' AND char_length(channel_ref) <= 500)")
    op.create_check_constraint(op.f('ck_fact_confirmations_value_length'), 'fact_confirmations',
                               "char_length(coalesce(value_before, '')) <= 1000 AND char_length(coalesce(value_after, '')) <= 1000")
    op.execute(RULES_SQL)


def downgrade() -> None:
    op.execute(DOWN_SQL)
    for ck in ('value_length', 'channel_ref', 'confirmed_by_role'):
        op.drop_constraint(op.f(f'ck_fact_confirmations_{ck}'), 'fact_confirmations', type_='check')
    op.drop_column('fact_confirmations', 'channel_ref')
    op.drop_column('fact_confirmations', 'confirmed_by_role')
    op.drop_table('facts')
    for ck in ('refs', 'approval_complete', 'approved_by_role'):
        op.drop_constraint(op.f(f'ck_fact_sheets_{ck}'), 'fact_sheets', type_='check')
    op.drop_constraint(op.f('fk_fact_sheets_approved_by_users'), 'fact_sheets', type_='foreignkey')
    op.drop_constraint(op.f('fk_fact_sheets_created_by_users'), 'fact_sheets', type_='foreignkey')
    for col in ('approval_ref', 'approved_by_role', 'approved_by', 'created_at', 'created_by'):
        op.drop_column('fact_sheets', col)
