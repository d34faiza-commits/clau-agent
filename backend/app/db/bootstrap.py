"""Siapkan database dan dua role terpisah (docs/security.md § 6: user aplikasi tanpa hak DDL).

- role migrasi (CLAU_DB_MIGRATOR_ROLE): pemilik schema, menjalankan Alembic.
- role aplikasi (CLAU_DB_APP_ROLE): hanya SELECT/INSERT/UPDATE/DELETE pada tabel; tidak bisa CREATE/ALTER/DROP.
  Hak pada tabel diberikan otomatis lewat ALTER DEFAULT PRIVILEGES; pengecualian (audit_log append-only)
  dicabut di migrasi.

Idempoten: aman dijalankan berulang. Password role selalu disetel ulang, jadi rotasi password = ubah .env
lalu jalankan lagi. Dipanggil oleh service `migrate` di docker-compose dengan akun admin Postgres; akun
admin tidak pernah diberikan ke service backend.

    python -m app.db.bootstrap        # baca env, lalu bootstrap
"""

from __future__ import annotations

import os

import psycopg
from psycopg import sql


def bootstrap(admin_url: str, database: str, migrator: tuple[str, str], app: tuple[str, str]) -> None:
    """admin_url: koneksi superuser ke database `postgres`. migrator/app: (nama role, password)."""
    (migrator_role, migrator_pw), (app_role, app_pw) = migrator, app
    for name, pw in (migrator, app):
        if not pw:
            raise SystemExit(f"password untuk role {name} kosong; isi .env (scripts/init-env.sh)")

    with psycopg.connect(admin_url, autocommit=True) as conn:
        for role, pw in ((migrator_role, migrator_pw), (app_role, app_pw)):
            exists = conn.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (role,)).fetchone()
            verb = "ALTER" if exists else "CREATE"
            conn.execute(
                sql.SQL(verb + " ROLE {} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOREPLICATION PASSWORD {}").format(
                    sql.Identifier(role), sql.Literal(pw)
                )
            )
        if not conn.execute("SELECT 1 FROM pg_database WHERE datname = %s", (database,)).fetchone():
            conn.execute(sql.SQL("CREATE DATABASE {} OWNER {} ENCODING 'UTF8' TEMPLATE template0").format(
                sql.Identifier(database), sql.Identifier(migrator_role)))
        conn.execute(sql.SQL("REVOKE ALL ON DATABASE {} FROM PUBLIC").format(sql.Identifier(database)))
        conn.execute(sql.SQL("GRANT CONNECT ON DATABASE {} TO {}").format(sql.Identifier(database), sql.Identifier(app_role)))

    db_url = psycopg.conninfo.make_conninfo(admin_url, dbname=database)
    with psycopg.connect(db_url, autocommit=True) as conn:
        ident = {"m": sql.Identifier(migrator_role), "a": sql.Identifier(app_role)}
        for stmt in (
            "ALTER SCHEMA public OWNER TO {m}",
            "REVOKE ALL ON SCHEMA public FROM PUBLIC",
            "GRANT USAGE ON SCHEMA public TO {a}",
            "ALTER DEFAULT PRIVILEGES FOR ROLE {m} IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO {a}",
            "ALTER DEFAULT PRIVILEGES FOR ROLE {m} IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO {a}",
        ):
            conn.execute(sql.SQL(stmt).format(**ident))


def main() -> None:
    env = os.environ
    bootstrap(
        admin_url=env["CLAU_DB_ADMIN_URL"],
        database=env.get("CLAU_DB_NAME", "clau"),
        migrator=(env.get("CLAU_DB_MIGRATOR_ROLE", "clau_migrator"), env.get("CLAU_DB_MIGRATOR_PASSWORD", "")),
        app=(env.get("CLAU_DB_APP_ROLE", "clau_app"), env.get("CLAU_DB_APP_PASSWORD", "")),
    )
    print("bootstrap database: OK")


if __name__ == "__main__":
    main()
