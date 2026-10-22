"""Penanda isi konten & level approval otomatis (TASK-032, kontrak core 0.10.0).

Rule 08 menetapkan level approval dari isi konten. Draft membawa penanda (`draft_flags`); level minimum draft =
tertinggi dari aturan lama (approval_min, klaim fact_key, draft agent NYATA), level penanda aktif, dan untuk
`localize` level minimum draft asal (`requests.source_draft_id`).

Aturan (pesan berawalan kode aturan, SQLSTATE 23514, seperti 0001/0004–0006):
- review_rating_required / source_draft_required / source_draft_invalid: request `review-reply` wajib rating 1–5,
  `localize` wajib draft asal milik klien yang sama; keduanya tidak bisa diubah setelah request dibuat.
- Jaring pengaman: setiap draft baru otomatis mendapat penanda sumber `server` (kata kunci harga & agama/adat di isi
  draft, rating review ≤ 3, intent ota-listing). Fungsi `clau_auto_flags` = satu-satunya daftar kata kunci.
- Versi draft baru mewarisi penanda aktif non-server versi sebelumnya (juga draft dari worker AI).
- flag_not_removable: penanda `server` tidak bisa dihapus. Penanda lain dihapus sekali (hanya kolom removed_*),
  oleh owner/content_lead agency, dengan alasan; perubahan lain / DELETE → decision_record_append_only.
- request_closed: tidak ada penanda baru untuk request yang sudah selesai.
- approval_level_too_low memakai `clau_draft_min_level` baru (alasan per aturan: `clau_draft_level_reasons`).

Data lama: draft yang sudah ada diberi penanda `server` dari jaring pengaman yang sama (hanya menaikkan level).

Revision ID: 0007
Revises: 0006
Create Date: 2026-10-22
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = '0007'
down_revision = '0006'
branch_labels = None
depends_on = None

FLAGS = ("price_promo", "people", "ota_listing", "negative_review", "paid_ads", "influencer", "religion_culture", "crisis")
SOURCES = ("author", "server", "staff", "qa")


def sql_list(values: tuple[str, ...]) -> str:
    return ", ".join(f"'{v}'" for v in values)


RULES_SQL = r"""
-- Level per penanda (Rule 08; kontrak core § Penanda Isi Konten).
CREATE FUNCTION clau_flag_level(flag text) RETURNS text LANGUAGE sql IMMUTABLE AS $$
  SELECT CASE WHEN flag IN ('price_promo', 'people', 'ota_listing') THEN 'L2' ELSE 'L3' END
$$;

-- Jaring pengaman server. Kata umum di konten wedding ("upacara", "sakral") sengaja tidak dipakai: terlalu sering salah
-- tangkap untuk vertical fokus wedding; topik agama/adat lain ditandai manusia (religion_culture). Kata dicocokkan tanpa beda huruf besar/kecil dan per kata utuh (\m … \M). Salah tangkap
-- hanya menaikkan level (arah aman); perubahan daftar = migrasi baru + test.
CREATE FUNCTION clau_auto_flags(content text, intent text, review_rating smallint) RETURNS SETOF text
  LANGUAGE plpgsql IMMUTABLE AS $$
BEGIN
  IF content ~* '\m(rp|idr)\.?\s?\d' OR content ~* '\d\s?%' OR content ~* '\m(harga|diskon|promo|discount|price|rate)\M'
     OR content ~* '\m(paket|package)\s+\S*\d' THEN
    RETURN NEXT 'price_promo';
  END IF;
  IF content ~* '\m(pura|masjid|gereja|vihara|klenteng|nyepi|galungan|kuningan|ramadan|lebaran|idul|natal|imlek|waisak|ngaben|melasti|ogoh-ogoh)\M' THEN
    RETURN NEXT 'religion_culture';
  END IF;
  IF intent = 'review-reply' AND review_rating IS NOT NULL AND review_rating <= 3 THEN
    RETURN NEXT 'negative_review';
  END IF;
  IF intent = 'ota-listing' THEN
    RETURN NEXT 'ota_listing';
  END IF;
END $$;

-- Request: rating wajib untuk review-reply, draft asal wajib untuk localize (klien sama); tidak bisa diubah.
CREATE FUNCTION clau_request_flag_rules() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF TG_OP = 'UPDATE' THEN
    IF (NEW.review_rating, NEW.source_draft_id) IS DISTINCT FROM (OLD.review_rating, OLD.source_draft_id) THEN
      RAISE EXCEPTION 'decision_record_append_only: rating review dan draft asal request tidak bisa diubah'
        USING ERRCODE = 'check_violation';
    END IF;
    RETURN NEW;
  END IF;
  IF NEW.intent = 'review-reply' AND NEW.review_rating IS NULL THEN
    RAISE EXCEPTION 'review_rating_required: request review-reply wajib rating review 1–5' USING ERRCODE = 'check_violation';
  END IF;
  IF NEW.intent = 'localize' AND NEW.source_draft_id IS NULL THEN
    RAISE EXCEPTION 'source_draft_required: request localize wajib menunjuk draft asal' USING ERRCODE = 'check_violation';
  END IF;
  IF NEW.source_draft_id IS NOT NULL AND NOT EXISTS (
       SELECT 1 FROM drafts d JOIN requests r ON r.id = d.request_id
       WHERE d.id = NEW.source_draft_id AND r.client_code = NEW.client_code) THEN
    RAISE EXCEPTION 'source_draft_invalid: draft asal tidak ada atau milik klien lain' USING ERRCODE = 'check_violation';
  END IF;
  RETURN NEW;
END $$;
CREATE TRIGGER trg_requests_flag_rules BEFORE INSERT OR UPDATE ON requests
  FOR EACH ROW EXECUTE FUNCTION clau_request_flag_rules();

-- Setiap draft baru (dari API maupun worker AI) langsung mendapat penanda server, lalu mewarisi penanda aktif
-- non-server versi sebelumnya (sumber & penambah sama): versi baru tidak bisa menurunkan level diam-diam.
CREATE FUNCTION clau_draft_auto_flags() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE req requests%ROWTYPE;
BEGIN
  SELECT * INTO req FROM requests WHERE id = NEW.request_id;
  INSERT INTO draft_flags (draft_id, flag, source)
    SELECT NEW.id, f, 'server' FROM clau_auto_flags(NEW.content, req.intent, req.review_rating) AS f;
  INSERT INTO draft_flags (draft_id, flag, source, added_by)
    SELECT NEW.id, p.flag, p.source, p.added_by
    FROM draft_flags p JOIN drafts prev ON prev.id = p.draft_id
    WHERE prev.request_id = NEW.request_id AND prev.version = NEW.version - 1
      AND p.removed_at IS NULL AND p.source <> 'server'
      AND NOT EXISTS (SELECT 1 FROM draft_flags x WHERE x.draft_id = NEW.id AND x.flag = p.flag AND x.removed_at IS NULL)
    ORDER BY p.id;
  RETURN NEW;
END $$;
CREATE TRIGGER trg_drafts_auto_flags AFTER INSERT ON drafts FOR EACH ROW EXECUTE FUNCTION clau_draft_auto_flags();

-- Penanda: baru hanya untuk request yang masih terbuka; hapus = isi removed_* sekali oleh owner/content_lead agency
-- dengan alasan; penanda server tidak bisa dihapus; selain itu append-only.
CREATE FUNCTION clau_draft_flag_rules() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE req requests%ROWTYPE;
BEGIN
  IF TG_OP = 'DELETE' THEN
    RAISE EXCEPTION 'decision_record_append_only: penanda draft tidak bisa dihapus; isi alasan penghapusan'
      USING ERRCODE = 'check_violation';
  END IF;
  SELECT r.* INTO req FROM drafts d JOIN requests r ON r.id = d.request_id
    WHERE d.id = (CASE WHEN TG_OP = 'INSERT' THEN NEW.draft_id ELSE OLD.draft_id END);
  PERFORM clau_request_open(req);
  IF TG_OP = 'INSERT' THEN
    IF NEW.removed_at IS NOT NULL OR NEW.removed_by IS NOT NULL OR NEW.removed_reason IS NOT NULL THEN
      RAISE EXCEPTION 'decision_record_append_only: penanda baru tidak boleh langsung terhapus' USING ERRCODE = 'check_violation';
    END IF;
    RETURN NEW;
  END IF;
  IF (NEW.id, NEW.draft_id, NEW.flag, NEW.source, NEW.added_by, NEW.added_at)
       IS DISTINCT FROM (OLD.id, OLD.draft_id, OLD.flag, OLD.source, OLD.added_by, OLD.added_at)
     OR OLD.removed_at IS NOT NULL THEN
    RAISE EXCEPTION 'decision_record_append_only: penanda draft hanya bisa dihapus sekali, tidak diubah'
      USING ERRCODE = 'check_violation';
  END IF;
  IF OLD.source = 'server' THEN
    RAISE EXCEPTION 'flag_not_removable: penanda dari jaring pengaman server tidak bisa dihapus; buat draft versi baru'
      USING ERRCODE = 'check_violation';
  END IF;
  IF NOT (clau_has_role(NEW.removed_by, 'agency', 'owner') OR clau_has_role(NEW.removed_by, 'agency', 'content_lead')) THEN
    RAISE EXCEPTION 'approval_role_mismatch: penanda hanya bisa dihapus owner/content lead' USING ERRCODE = 'check_violation';
  END IF;
  RETURN NEW;
END $$;
CREATE TRIGGER trg_draft_flags_rules BEFORE INSERT OR UPDATE OR DELETE ON draft_flags
  FOR EACH ROW EXECUTE FUNCTION clau_draft_flag_rules();

-- Alasan level minimum (satu baris per aturan yang menaikkan level). Level minimum = level tertinggi di sini.
CREATE FUNCTION clau_draft_level_reasons(d drafts, req requests) RETURNS TABLE (rule text, level text)
  LANGUAGE plpgsql STABLE AS $$
DECLARE src drafts%ROWTYPE; src_req requests%ROWTYPE;
BEGIN
  rule := 'intent:' || req.intent; level := req.approval_min; RETURN NEXT;
  IF EXISTS (SELECT 1 FROM claims WHERE draft_id = d.id AND fact_key IS NOT NULL) THEN
    rule := 'fact_claims'; level := 'L2'; RETURN NEXT;
  END IF;
  IF d.created_by IS NULL AND d.mode = 'NYATA' THEN
    rule := 'agent_draft'; level := 'L2'; RETURN NEXT;
  END IF;
  RETURN QUERY SELECT 'flag:' || f.flag, clau_flag_level(f.flag)
    FROM draft_flags f WHERE f.draft_id = d.id AND f.removed_at IS NULL ORDER BY f.id;
  IF req.source_draft_id IS NOT NULL THEN
    SELECT * INTO src FROM drafts WHERE id = req.source_draft_id;
    SELECT * INTO src_req FROM requests WHERE id = src.request_id;
    rule := 'source_draft:' || src.id; level := clau_draft_min_level(src, src_req); RETURN NEXT;
  END IF;
END $$;

CREATE OR REPLACE FUNCTION clau_draft_min_level(d drafts, req requests) RETURNS text LANGUAGE sql STABLE AS $$
  SELECT max(r.level) FROM clau_draft_level_reasons(d, req) AS r
$$;

-- Data lama: draft yang sudah ada mendapat penanda server yang sama (trigger dimatikan sesaat: request lama yang
-- sudah selesai tetap boleh diberi penanda hasil migrasi).
ALTER TABLE draft_flags DISABLE TRIGGER trg_draft_flags_rules;
INSERT INTO draft_flags (draft_id, flag, source)
  SELECT d.id, f, 'server' FROM drafts d JOIN requests r ON r.id = d.request_id,
    LATERAL clau_auto_flags(d.content, r.intent, r.review_rating) AS f;
ALTER TABLE draft_flags ENABLE TRIGGER trg_draft_flags_rules;

-- Seperti ai_jobs: penanda tidak pernah dihapus (hak DELETE/TRUNCATE dicabut dari role selain pemilik).
DO $$
DECLARE r record;
BEGIN
  FOR r IN SELECT DISTINCT grantee FROM information_schema.role_table_grants
           WHERE table_schema = 'public' AND table_name = 'draft_flags'
             AND privilege_type IN ('DELETE', 'TRUNCATE') AND grantee <> current_user
  LOOP
    EXECUTE format('REVOKE DELETE, TRUNCATE ON draft_flags FROM %I', r.grantee);
  END LOOP;
END $$;
"""

DOWN_SQL = """
-- Kembalikan level minimum 0006.
DROP FUNCTION IF EXISTS clau_draft_min_level(drafts, requests);
DROP FUNCTION IF EXISTS clau_draft_level_reasons(drafts, requests);
CREATE FUNCTION clau_draft_min_level(d drafts, req requests) RETURNS text LANGUAGE plpgsql STABLE AS $$
BEGIN
  IF req.approval_min = 'L1' AND (
       EXISTS (SELECT 1 FROM claims WHERE draft_id = d.id AND fact_key IS NOT NULL)
       OR (d.created_by IS NULL AND d.mode = 'NYATA')) THEN
    RETURN 'L2';
  END IF;
  RETURN req.approval_min;
END $$;
DROP TRIGGER IF EXISTS trg_drafts_auto_flags ON drafts;
DROP FUNCTION IF EXISTS clau_draft_auto_flags();
DROP TRIGGER IF EXISTS trg_requests_flag_rules ON requests;
DROP FUNCTION IF EXISTS clau_request_flag_rules();
DROP FUNCTION IF EXISTS clau_auto_flags(text, text, smallint);
DROP FUNCTION IF EXISTS clau_flag_level(text);
DROP FUNCTION IF EXISTS clau_draft_flag_rules() CASCADE;
"""


def upgrade() -> None:
    op.add_column('requests', sa.Column('review_rating', sa.SmallInteger(), nullable=True))
    op.add_column('requests', sa.Column('source_draft_id', sa.BigInteger(), nullable=True))
    op.create_check_constraint(op.f('ck_requests_review_rating_range'), 'requests',
                               'review_rating IS NULL OR review_rating BETWEEN 1 AND 5')
    op.create_foreign_key(op.f('fk_requests_source_draft_id_drafts'), 'requests', 'drafts', ['source_draft_id'], ['id'])
    op.create_index(op.f('ix_requests_source_draft_id'), 'requests', ['source_draft_id'])
    op.create_table(
        'draft_flags',
        sa.Column('id', sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column('draft_id', sa.BigInteger(), nullable=False),
        sa.Column('flag', sa.Text(), nullable=False),
        sa.Column('source', sa.Text(), nullable=False),
        sa.Column('added_by', sa.BigInteger(), nullable=True),
        sa.Column('added_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('removed_by', sa.BigInteger(), nullable=True),
        sa.Column('removed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('removed_reason', sa.Text(), nullable=True),
        sa.CheckConstraint(f"flag IN ({sql_list(FLAGS)})", name=op.f('ck_draft_flags_flag')),
        sa.CheckConstraint(f"source IN ({sql_list(SOURCES)})", name=op.f('ck_draft_flags_source')),
        sa.CheckConstraint(
            "(removed_at IS NULL AND removed_by IS NULL AND removed_reason IS NULL)"
            " OR (removed_at IS NOT NULL AND removed_by IS NOT NULL AND char_length(removed_reason) BETWEEN 10 AND 500)",
            name=op.f('ck_draft_flags_removed_fields')),
        sa.CheckConstraint("source IN ('server', 'author') OR added_by IS NOT NULL", name=op.f('ck_draft_flags_added_by')),
        sa.ForeignKeyConstraint(['draft_id'], ['drafts.id'], name=op.f('fk_draft_flags_draft_id_drafts')),
        sa.ForeignKeyConstraint(['added_by'], ['users.id'], name=op.f('fk_draft_flags_added_by_users')),
        sa.ForeignKeyConstraint(['removed_by'], ['users.id'], name=op.f('fk_draft_flags_removed_by_users')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_draft_flags')),
    )
    op.create_index(op.f('ix_draft_flags_draft_id'), 'draft_flags', ['draft_id'])
    op.create_index(op.f('ix_draft_flags_added_by'), 'draft_flags', ['added_by'])
    op.create_index(op.f('ix_draft_flags_removed_by'), 'draft_flags', ['removed_by'])
    op.create_index('uq_draft_flags_active', 'draft_flags', ['draft_id', 'flag'], unique=True,
                    postgresql_where=sa.text('removed_at IS NULL'))
    op.execute(RULES_SQL)


def downgrade() -> None:
    op.execute(DOWN_SQL)
    op.drop_index('uq_draft_flags_active', table_name='draft_flags')
    op.drop_index(op.f('ix_draft_flags_removed_by'), table_name='draft_flags')
    op.drop_index(op.f('ix_draft_flags_added_by'), table_name='draft_flags')
    op.drop_index(op.f('ix_draft_flags_draft_id'), table_name='draft_flags')
    op.drop_table('draft_flags')
    op.drop_index(op.f('ix_requests_source_draft_id'), table_name='requests')
    op.drop_constraint(op.f('fk_requests_source_draft_id_drafts'), 'requests', type_='foreignkey')
    op.drop_constraint(op.f('ck_requests_review_rating_range'), 'requests', type_='check')
    op.drop_column('requests', 'source_draft_id')
    op.drop_column('requests', 'review_rating')
