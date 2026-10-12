"""Alembic env: memakai role migrasi (pemilik schema), bukan role aplikasi."""

from __future__ import annotations

import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool

from app.db.models import Base

target_metadata = Base.metadata

if context.config.config_file_name:
    # Log "Running upgrade ..." ke stderr; logger lain (pytest, uvicorn) tidak dimatikan.
    fileConfig(context.config.config_file_name, disable_existing_loggers=False)


def database_url() -> str:
    url = context.config.attributes.get("url") or os.environ.get("CLAU_MIGRATION_DATABASE_URL", "")
    if not url:
        raise SystemExit("CLAU_MIGRATION_DATABASE_URL belum diatur (lihat .env.example)")
    return url


def run_migrations_offline() -> None:
    context.configure(url=database_url(), target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    engine = create_engine(database_url(), poolclass=pool.NullPool)
    with engine.connect() as connection:
        # Satu transaksi per migrasi: gagal di tengah = tidak ada perubahan setengah jadi.
        context.configure(connection=connection, target_metadata=target_metadata, transaction_per_migration=True)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
