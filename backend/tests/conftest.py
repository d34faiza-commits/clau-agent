"""Fixture database untuk test yang butuh PostgreSQL sungguhan.

CLAU_TEST_DB_ADMIN_URL = koneksi superuser ke database `postgres`, mis.
postgresql://postgres:<pw>@127.0.0.1:5432/postgres. Setiap sesi test membuat database dan role sendiri
(nama acak), menjalankan bootstrap + migrasi, lalu menghapus semuanya.

Tanpa variabel itu test database dilewati, kecuali CLAU_REQUIRE_DB_TESTS=1 (diset di CI) yang
membuatnya gagal: CI tidak boleh hijau tanpa benar-benar menguji database.
"""

from __future__ import annotations

import os
import secrets
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1]


def admin_url_or_skip() -> str:
    url = os.environ.get("CLAU_TEST_DB_ADMIN_URL", "")
    if not url:
        if os.environ.get("CLAU_REQUIRE_DB_TESTS") == "1":
            pytest.fail("CLAU_REQUIRE_DB_TESTS=1 tetapi CLAU_TEST_DB_ADMIN_URL tidak diset")
        pytest.skip("CLAU_TEST_DB_ADMIN_URL tidak diset (test database dilewati)")
    return url


def sqlalchemy_url(conninfo: str) -> str:
    """postgresql://... -> postgresql+psycopg://... (driver psycopg 3)."""
    import psycopg

    p = psycopg.conninfo.conninfo_to_dict(conninfo)
    return f"postgresql+psycopg://{p['user']}:{p['password']}@{p.get('host', '127.0.0.1')}:{p.get('port', 5432)}/{p['dbname']}"


class TempDatabase:
    """Database + role migrasi + role aplikasi sekali pakai, sudah di-bootstrap dan dimigrasi ke head."""

    def __init__(self, admin_url: str) -> None:
        import psycopg

        from app.db.bootstrap import bootstrap

        tag = secrets.token_hex(4)
        self.admin_url = admin_url
        self.name = f"clau_test_{tag}"
        self.migrator = (f"clau_test_migrator_{tag}", secrets.token_urlsafe(16))
        self.app = (f"clau_test_app_{tag}", secrets.token_urlsafe(16))
        bootstrap(admin_url, self.name, self.migrator, self.app)
        base = psycopg.conninfo.conninfo_to_dict(admin_url)
        self.migrator_conninfo = psycopg.conninfo.make_conninfo(admin_url, dbname=self.name, user=self.migrator[0], password=self.migrator[1])
        self.app_conninfo = psycopg.conninfo.make_conninfo(admin_url, dbname=self.name, user=self.app[0], password=self.app[1])
        self.host = base.get("host", "127.0.0.1")

    def alembic(self, command: str, target: str) -> None:
        from alembic import command as alembic_command
        from alembic.config import Config

        cfg = Config(str(BACKEND / "alembic.ini"))
        cfg.attributes["url"] = sqlalchemy_url(self.migrator_conninfo)
        getattr(alembic_command, command)(cfg, target)

    def drop(self) -> None:
        import psycopg
        from psycopg import sql

        with psycopg.connect(self.admin_url, autocommit=True) as conn:
            conn.execute(sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(sql.Identifier(self.name)))
            for role, _ in (self.app, self.migrator):
                conn.execute(sql.SQL("DROP ROLE IF EXISTS {}").format(sql.Identifier(role)))


@pytest.fixture(scope="session")
def database():
    db = TempDatabase(admin_url_or_skip())
    try:
        db.alembic("upgrade", "head")
        yield db
    finally:
        db.drop()


@pytest.fixture()
def app_conn(database):
    """Koneksi role aplikasi; setiap test di-rollback agar data antar test tidak bercampur."""
    import psycopg

    with psycopg.connect(database.app_conninfo) as conn:
        yield conn
        conn.rollback()
