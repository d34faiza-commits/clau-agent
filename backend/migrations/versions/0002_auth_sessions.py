"""Login: kolom autentikasi di users + tabel sessions (Tahap 1 PR 2, docs/security.md § 6).

Password hanya hash Argon2id (CHECK), secret TOTP terenkripsi, sesi disimpan sebagai SHA-256 token.

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-12
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = '0002'
down_revision = '0001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('sessions',
    sa.Column('token_hash', sa.Text(), nullable=False),
    sa.Column('user_id', sa.BigInteger(), nullable=False),
    sa.Column('mfa_ok', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('last_seen_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
    sa.CheckConstraint("token_hash ~ '^[0-9a-f]{64}$'", name=op.f('ck_sessions_token_hash_sha256')),
    sa.CheckConstraint('expires_at > created_at', name=op.f('ck_sessions_expires_after_created')),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_sessions_user_id_users')),
    sa.PrimaryKeyConstraint('token_hash', name=op.f('pk_sessions'))
    )
    op.create_index(op.f('ix_sessions_user_id'), 'sessions', ['user_id'], unique=False)
    op.add_column('users', sa.Column('password_hash', sa.Text(), nullable=True))
    op.add_column('users', sa.Column('must_change_password', sa.Boolean(), server_default='false', nullable=False))
    op.add_column('users', sa.Column('totp_secret_enc', postgresql.BYTEA(), nullable=True))
    op.add_column('users', sa.Column('totp_enabled', sa.Boolean(), server_default='false', nullable=False))
    op.add_column('users', sa.Column('totp_last_counter', sa.BigInteger(), nullable=True))
    op.add_column('users', sa.Column('failed_logins', sa.Integer(), server_default='0', nullable=False))
    op.add_column('users', sa.Column('locked_until', sa.DateTime(timezone=True), nullable=True))
    op.add_column('users', sa.Column('disabled_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('users', sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True))
    op.create_check_constraint(op.f('ck_users_password_argon2id'), 'users', "password_hash IS NULL OR password_hash LIKE '$argon2id$%'")
    op.create_check_constraint(op.f('ck_users_totp_has_secret'), 'users', 'NOT totp_enabled OR totp_secret_enc IS NOT NULL')
    op.create_check_constraint(op.f('ck_users_failed_logins_positive'), 'users', 'failed_logins >= 0')


def downgrade() -> None:
    op.drop_constraint(op.f('ck_users_failed_logins_positive'), 'users', type_='check')
    op.drop_constraint(op.f('ck_users_totp_has_secret'), 'users', type_='check')
    op.drop_constraint(op.f('ck_users_password_argon2id'), 'users', type_='check')
    op.drop_column('users', 'last_login_at')
    op.drop_column('users', 'disabled_at')
    op.drop_column('users', 'locked_until')
    op.drop_column('users', 'failed_logins')
    op.drop_column('users', 'totp_last_counter')
    op.drop_column('users', 'totp_enabled')
    op.drop_column('users', 'totp_secret_enc')
    op.drop_column('users', 'must_change_password')
    op.drop_column('users', 'password_hash')
    op.drop_index(op.f('ix_sessions_user_id'), table_name='sessions')
    op.drop_table('sessions')
