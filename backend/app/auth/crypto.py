"""Primitif keamanan login: hash password (Argon2id), token sesi & CSRF, enkripsi secret TOTP, verifikasi TOTP.

Semua perbandingan rahasia memakai compare_digest (waktu konstan).
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import os
import re
import secrets
import threading
import time
from pathlib import Path

import pyotp
import segno
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

# Parameter Argon2id = rekomendasi RFC 9106 profil memori rendah (t=3, m=64 MiB, p=4), default argon2-cffi.
_hasher = PasswordHasher()
# Satu hash Argon2id memakai 64 MiB. Batasi yang berjalan bersamaan agar banjir request login tidak
# menghabiskan memori container (mem_limit 512m); request lain menunggu giliran.
_HASH_SLOTS = threading.BoundedSemaphore(int(os.environ.get("CLAU_HASH_CONCURRENCY") or 3))
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


# Kata dasar password yang paling sering dipakai/ditebak (daftar lokal, tanpa layanan luar). Password
# yang huruf-hurufnya hanya kata ini (mis. "Password2026!!", "bismillah12345") ditolak.
_COMMON_BASES = frozenset(
    line.strip() for line in (Path(__file__).with_name("common_passwords.txt")).read_text(encoding="utf-8").splitlines()
    if line.strip() and not line.startswith("#")
)
_SEQUENCES = ("0123456789", "1234567890", "9876543210", "qwertyuiop", "asdfghjkl", "zxcvbnm", "abcdefghijklmnopqrstuvwxyz")


def password_problem(password: str, email: str) -> str | None:
    """Kebijakan NIST SP 800-63B: panjang + tolak password umum, tanpa aturan komposisi. None = boleh."""
    if len(password) < MIN_PASSWORD:
        return f"Password minimal {MIN_PASSWORD} karakter."
    if len(password) > MAX_PASSWORD:
        return f"Password maksimal {MAX_PASSWORD} karakter."
    lower = password.lower()
    local = email.split("@", 1)[0].lower()
    if len(local) >= 4 and local in lower:
        return "Password tidak boleh memuat nama email."
    if len(set(password)) < 5:
        return "Password terlalu mudah ditebak."
    letters = re.sub(r"[^a-z]", "", lower)
    if letters in _COMMON_BASES or any(len(set(letters)) and letters == base * (len(letters) // len(base)) for base in _COMMON_BASES):
        return "Password terlalu umum. Pakai gabungan beberapa kata yang tidak berhubungan."
    stripped = re.sub(r"[^a-z0-9]", "", lower)
    if any(stripped in seq * 2 for seq in _SEQUENCES) or stripped.isdigit():
        return "Password terlalu mudah ditebak (urutan angka/huruf)."
    return None


def hash_password(password: str) -> str:
    with _HASH_SLOTS:
        return _hasher.hash(password)


def verify_password(password_hash: str | None, password: str) -> bool:
    """Selalu menjalankan Argon2 (hash pembanding bila akun tidak ada) agar waktu respons sama."""
    try:
        with _HASH_SLOTS:
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
    # compare_digest menolak str non-ASCII dengan TypeError: bandingkan sebagai bytes.
    return bool(header) and hmac.compare_digest(csrf_token(secret_key, session_token).encode(), header.encode())


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


def totp_qr(uri: str) -> str:
    """QR code (data URI SVG) untuk dipindai aplikasi authenticator; dibuat di server, tanpa layanan luar."""
    return segno.make(uri, error="m").svg_data_uri(scale=5, border=2)


# --- Kode cadangan 2FA ----------------------------------------------------------------------------

RECOVERY_COUNT = 10
_RECOVERY_ALPHABET = "abcdefghjkmnpqrstuvwxyz23456789"  # tanpa i, l, o, 0, 1 (mudah tertukar)


def new_recovery_codes() -> list[str]:
    """10 kode sekali pakai, masing-masing ~49 bit acak, format abcde-fghij."""
    codes = []
    for _ in range(RECOVERY_COUNT):
        raw = "".join(secrets.choice(_RECOVERY_ALPHABET) for _ in range(10))
        codes.append(f"{raw[:5]}-{raw[5:]}")
    return codes


def normalize_recovery(code: str) -> str:
    return re.sub(r"[\s-]", "", (code or "").lower())


def recovery_hash(secret_key: bytes, user_id: int, code: str) -> str:
    """HMAC (bukan Argon2): kode sudah acak tinggi entropi, dan login tidak perlu 10 hash Argon2."""
    msg = f"recovery:{user_id}:{normalize_recovery(code)}".encode()
    return hmac.new(check_secret_key(secret_key), msg, hashlib.sha256).hexdigest()


def verify_totp(secret: str, code: str, last_counter: int | None, now: float | None = None) -> int | None:
    """Counter (jendela 30 detik) yang cocok, atau None. Toleransi ±1 jendela untuk jam HP yang meleset;
    counter ≤ last_counter ditolak agar kode yang sudah dipakai tidak bisa diputar ulang."""
    code = (code or "").strip().replace(" ", "")
    # isascii(): str.isdigit() juga menerima digit non-ASCII (mis. １２３４５６), yang membuat compare_digest error.
    if not (len(code) == 6 and code.isascii() and code.isdigit()):
        return None
    totp = pyotp.TOTP(secret)
    current = int((now if now is not None else time.time()) // totp.interval)
    for counter in (current - 1, current, current + 1):
        if hmac.compare_digest(totp.generate_otp(counter), code):
            if last_counter is not None and counter <= last_counter:
                return None
            return counter
    return None
