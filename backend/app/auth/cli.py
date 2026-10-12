"""Perintah admin server (tanpa endpoint publik). Memakai CLAU_DATABASE_URL (role aplikasi).

    python -m app.auth.cli create-owner --email owner@contoh.id --name "Nama Owner"
    python -m app.auth.cli reset-mfa --email user@contoh.id      # HP hilang: 2FA diatur ulang saat login berikut

Password dibaca dari prompt tersembunyi (atau CLAU_BOOTSTRAP_PASSWORD untuk otomasi), tidak pernah dari argumen
command line (bisa terbaca di riwayat shell / daftar proses).
"""

from __future__ import annotations

import argparse
import getpass
import os
import sys

from sqlalchemy.orm import Session

from app.auth import crypto
from app.auth.routes import audit, find_user, owner_exists, revoke_sessions
from app.db.models import Membership, User


def read_password(email: str) -> str:
    password = os.environ.get("CLAU_BOOTSTRAP_PASSWORD") or ""
    if not password:
        password = getpass.getpass("Password owner (min. 12 karakter): ")
        if password != getpass.getpass("Ulangi password: "):
            sys.exit("Password tidak sama.")
    if problem := crypto.password_problem(password, email):
        sys.exit(problem)
    return password


def create_owner(db: Session, email: str, name: str, password: str) -> User:
    if owner_exists(db):
        sys.exit("Owner sudah ada. Owner berikutnya dibuat dari aplikasi (POST /users) oleh owner yang ada.")
    if find_user(db, email):
        sys.exit("Email sudah dipakai.")
    user = User(display_name=name, email=email, password_hash=crypto.hash_password(password))
    db.add(user)
    db.flush()
    db.add(Membership(user_id=user.id, scope="agency", role="owner", max_level="L3"))
    audit(db, None, "owner_bootstrapped", "user", user.id, via="cli")
    return user


def reset_mfa(db: Session, email: str) -> User:
    user = find_user(db, email)
    if user is None:
        sys.exit("User tidak ditemukan.")
    user.totp_enabled, user.totp_secret_enc, user.totp_last_counter = False, None, None
    revoke_sessions(db, user.id)
    audit(db, None, "mfa_reset", "user", user.id, via="cli")
    return user


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="python -m app.auth.cli")
    sub = parser.add_subparsers(dest="command", required=True)
    owner = sub.add_parser("create-owner", help="buat owner pertama (sekali)")
    owner.add_argument("--email", required=True)
    owner.add_argument("--name", required=True)
    reset = sub.add_parser("reset-mfa", help="nonaktifkan 2FA user (HP hilang); wajib diatur ulang saat login")
    reset.add_argument("--email", required=True)
    args = parser.parse_args(argv)

    from app.db.session import session_factory

    with session_factory().begin() as db:
        if args.command == "create-owner":
            user = create_owner(db, args.email.strip(), args.name.strip(), read_password(args.email))
            print(f"owner dibuat: {user.email} (2FA wajib diaktifkan saat login pertama)")
        else:
            user = reset_mfa(db, args.email.strip())
            print(f"2FA direset untuk {user.email}; semua sesinya diputus")


if __name__ == "__main__":
    main()
