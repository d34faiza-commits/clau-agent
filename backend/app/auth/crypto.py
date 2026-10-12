"""Primitif keamanan login: hash password (Argon2id), token sesi & CSRF, enkripsi secret TOTP, verifikasi TOTP.

Semua perbandingan rahasia memakai compare_digest (waktu konstan).
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import time

import pyotp
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

# Parameter Argon2id = rekomendasi RFC 9106 profil memori rendah (t=3, m=64 MiB, p=4), default argon2-cffi.
_hasher = PasswordHasher()
# Hash pembanding untuk email yang tidak terdaftar: waktu respons sama, jadi email tidak bisa ditebak.
_DUMMY_HASH = _hasher.hash(secrets.token_urlsafe(16))

MIN_PASSWORD = 12
MAX_PASSWORD = 128
MIN_SECRET_KEY = 32


class SecretKeyMissing(RuntimeError):
    """CLAU_SECRET_KEY kosong/terlalu pendek: fitur login ditolak (fail closed)."""


def check_secret_key(key: bytes) -> bytes:
    if len(key) < MIN_SECRET_KEY:
        raise SecretKeyMissing("CLAU_SECRET_KEY belum diatur atau kurang dari 32 karakter (scripts/init-env.sh)")
    return key


# --- Password -----------------------------------------------------------------------------------


def password_problem(password: str, email: str) -> str | None:
    """Kebijakan NIST SP 800-63B: panjang, bukan aturan komposisi. None = password boleh dipakai."""
    if len(password) < MIN_PASSWORD:
        return f"Password minimal {MIN_PASSWORD} karakter."
    if len(password) > MAX_PASSWORD:
        return f"Password maksimal {MAX_PASSWORD} karakter."
    local = email.split("@", 1)[0].lower()
    if len(local) >= 4 and local in password.lower():
        return "Password tidak boleh memuat nama email."
    if len(set(password)) < 5:
        return "Password terlalu mudah ditebak."
    return None


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str | None, password: str) -> bool:
    try:
        return _hasher.verify(password_hash or _DUMMY_HASH, password) and password_hash is not None
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def needs_rehash(password_hash: str) -> bool:
    return _hasher.check_needs_rehash(password_hash)


# --- Token sesi & CSRF --------------------------------------------------------------------------


def new_session_token() -> str:
    return secrets.token_urlsafe(32)


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def csrf_token(secret_key: bytes, session_token: str) -> str:
    """Diturunkan dari token sesi: tidak perlu disimpan, berganti setiap sesi baru."""
    digest = hmac.new(check_secret_key(secret_key), b"csrf:" + session_token.encode(), hashlib.sha256).digest()
    return base64.urlsafe_b64encode(digest).decode().rstrip("=")


def csrf_valid(secret_key: bytes, session_token: str, header: str | None) -> bool:
    return bool(header) and hmac.compare_digest(csrf_token(secret_key, session_token), header)


# --- TOTP (RFC 6238, 30 detik, 6 digit) ---------------------------------------------------------


def _totp_key(secret_key: bytes) -> bytes:
    return HKDF(algorithm=hashes.SHA256(), length=32, salt=b"clau-ai", info=b"totp-secret-v1").derive(check_secret_key(secret_key))


def encrypt_totp_secret(secret_key: bytes, user_id: int, secret: str) -> bytes:
    nonce = secrets.token_bytes(12)
    # Associated data = id user: secret milik user A tidak bisa disalin ke baris user B.
    return nonce + AESGCM(_totp_key(secret_key)).encrypt(nonce, secret.encode(), str(user_id).encode())


def decrypt_totp_secret(secret_key: bytes, user_id: int, blob: bytes) -> str:
    return AESGCM(_totp_key(secret_key)).decrypt(blob[:12], blob[12:], str(user_id).encode()).decode()


def new_totp_secret() -> str:
    return pyotp.random_base32()


def totp_uri(secret: str, email: str) -> str:
    return pyotp.TOTP(secret).provisioning_uri(name=email, issuer_name="CLAU AI")


def verify_totp(secret: str, code: str, last_counter: int | None, now: float | None = None) -> int | None:
    """Counter (jendela 30 detik) yang cocok, atau None. Toleransi ±1 jendela untuk jam HP yang meleset;
    counter ≤ last_counter ditolak agar kode yang sudah dipakai tidak bisa diputar ulang."""
    code = (code or "").strip().replace(" ", "")
    if not (len(code) == 6 and code.isdigit()):
        return None
    totp = pyotp.TOTP(secret)
    current = int((now if now is not None else time.time()) // totp.interval)
    for counter in (current - 1, current, current + 1):
        if hmac.compare_digest(totp.generate_otp(counter), code):
            if last_counter is not None and counter <= last_counter:
                return None
            return counter
    return None
