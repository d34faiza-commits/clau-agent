"""Kode cadangan 2FA (tabel mfa_recovery_codes) + index sessions.expires_at untuk pembersihan sesi.

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-13
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = '0003'
down_revision = '0002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('mfa_recovery_codes',
    sa.Column('id', sa.BigInteger(), sa.Identity(always=True), nullable=False),
    sa.Column('user_id', sa.BigInteger(), nullable=False),
    sa.Column('code_hash', sa.Text(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('used_at', sa.DateTime(timezone=True), nullable=True),
    sa.CheckConstraint("code_hash ~ '^[0-9a-f]{64}$'", name=op.f('ck_mfa_recovery_codes_code_hash_sha256')),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_mfa_recovery_codes_user_id_users')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_mfa_recovery_codes')),
    sa.UniqueConstraint('user_id', 'code_hash', name=op.f('uq_mfa_recovery_codes_user_id_code_hash'))
    )
    op.create_index(op.f('ix_mfa_recovery_codes_user_id'), 'mfa_recovery_codes', ['user_id'], unique=False)
    op.create_index(op.f('ix_sessions_expires_at'), 'sessions', ['expires_at'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_sessions_expires_at'), table_name='sessions')
    op.drop_index(op.f('ix_mfa_recovery_codes_user_id'), table_name='mfa_recovery_codes')
    op.drop_table('mfa_recovery_codes')
