"""Model database CLAU AI sesuai kontrak core/shared/database-schema.md.

Aturan yang wajib (Constraint Wajib di kontrak) ditegakkan di database sendiri, bukan hanya di kode:
CHECK constraint di sini, dan trigger di migrasi 0001 untuk aturan yang melibatkan tabel lain.
Nilai enum diambil dari sumbernya: label evidence & kategori klaim & vertical dari
clau-ai-marketing/schemas/content-brief.schema.json, priority dari core/orchestrator/priority-engine.md,
level approval dari rule 08. Enum disimpan sebagai text + CHECK (bukan tipe ENUM Postgres) agar
penambahan nilai cukup satu migrasi kecil.
"""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    Integer,
    MetaData,
    SmallInteger,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import BYTEA, JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# Nama constraint/index deterministik: migrasi dan pesan error bisa merujuk nama yang sama.
NAMING = {
    "ix": "ix_%(table_name)s_%(column_0_N_name)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

EVIDENCE_LABELS = ("DATA FINAL", "ASSUMPTION", "CLIENT CONFIRMATION", "FIELD VERIFICATION", "RISK", "NEXT ACTION")
CLAIM_CATEGORIES = (
    "facility", "location", "price", "rating", "certification", "halal-dietary", "food-beverage",
    "treatment", "experience", "capacity", "safety", "license", "itinerary", "other",
)
VERTICALS = ("accommodation", "food-beverage", "spa-wellness", "experience", "wedding-event", "travel-tour")
PRIORITIES = ("Low", "Normal", "High", "Urgent")
LEVELS = ("L1", "L2", "L3")
MODES = ("NYATA", "SIMULASI")
QA_RESULTS = ("Pass", "Conditional", "Fail", "N/A")
QA_GATES = ("claim-verification", "content-review", "privacy-rights-review", "visual-ai-review", "publication-checklist")
APPROVAL_DECISIONS = ("Approved", "Revise", "Rejected")
ROLES = ("owner", "content_lead", "content_staff", "viewer", "client_approver")
AGENCY_ROLES = ("owner", "content_lead", "content_staff")
LOCALES = ("id", "en")
TIMEZONES = ("Asia/Jakarta", "Asia/Makassar", "Asia/Jayapura")
NOTIFICATION_CHANNELS = ("in_app", "email", "whatsapp")
FACT_DECISIONS = ("confirmed", "corrected")

CLIENT_CODE_RE = "^[A-Z0-9]{2,12}$"
SLUG_RE = "^[a-z0-9]+(-[a-z0-9]+)*$"


def one_of(column: str, values: tuple[str, ...]) -> str:
    quoted = ", ".join("'" + v.replace("'", "''") + "'" for v in values)
    return f"{column} IN ({quoted})"


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING)


def pk() -> Mapped[int]:
    return mapped_column(BigInteger, Identity(always=True), primary_key=True)


def created_at() -> Mapped[datetime]:
    return mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class Client(Base):
    __tablename__ = "clients"
    client_code: Mapped[str] = mapped_column(Text, primary_key=True)
    vertical: Mapped[str] = mapped_column(Text, nullable=False)
    business_type: Mapped[str] = mapped_column(Text, nullable=False)
    location_area: Mapped[str | None] = mapped_column(Text)
    approver_role: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = created_at()
    __table_args__ = (
        CheckConstraint(f"client_code ~ '{CLIENT_CODE_RE}'", name="client_code_format"),
        CheckConstraint(one_of("vertical", VERTICALS), name="vertical"),
    )


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = pk()
    display_name: Mapped[str] = mapped_column(Text, nullable=False)
    email: Mapped[str] = mapped_column(Text, nullable=False)
    locale: Mapped[str] = mapped_column(Text, nullable=False, server_default="id")
    timezone: Mapped[str] = mapped_column(Text, nullable=False, server_default="Asia/Makassar")
    salutation: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = created_at()
    # Login (migrasi 0002, app/auth). Password hanya hash Argon2id; null = akun belum/tidak bisa login.
    password_hash: Mapped[str | None] = mapped_column(Text)
    must_change_password: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    # Secret TOTP terenkripsi AES-GCM (kunci dari CLAU_SECRET_KEY), terikat ke id user.
    totp_secret_enc: Mapped[bytes | None] = mapped_column(BYTEA)
    totp_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    totp_last_counter: Mapped[int | None] = mapped_column(BigInteger)  # cegah kode yang sama dipakai ulang
    failed_logins: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    disabled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    __table_args__ = (
        CheckConstraint("password_hash IS NULL OR password_hash LIKE '$argon2id$%'", name="password_argon2id"),
        CheckConstraint("NOT totp_enabled OR totp_secret_enc IS NOT NULL", name="totp_has_secret"),
        CheckConstraint("failed_logins >= 0", name="failed_logins_positive"),
        CheckConstraint("email ~ '^[^@[:space:]]+@[^@[:space:]]+$'", name="email_format"),
        CheckConstraint(one_of("locale", LOCALES), name="locale"),
        CheckConstraint(one_of("timezone", TIMEZONES), name="timezone"),
        # Satu akun per email, tanpa membedakan huruf besar/kecil.
        Index("uq_users_email_lower", func.lower(text("email")), unique=True),
    )


class UserSession(Base):
    """Sesi login di server. Cookie hanya berisi token acak; database menyimpan SHA-256-nya, jadi kebocoran
    database tidak memberi sesi yang bisa dipakai. Token CSRF diturunkan dari token sesi (HMAC), tidak disimpan."""

    __tablename__ = "sessions"
    token_hash: Mapped[str] = mapped_column(Text, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    # false = password benar tetapi 2FA wajib belum diaktifkan: hanya endpoint akun yang boleh dipakai.
    mfa_ok: Mapped[bool] = mapped_column(Boolean, nullable=False)
    created_at: Mapped[datetime] = created_at()
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    __table_args__ = (
        CheckConstraint("token_hash ~ '^[0-9a-f]{64}$'", name="token_hash_sha256"),
        CheckConstraint("expires_at > created_at", name="expires_after_created"),
    )


class MfaRecoveryCode(Base):
    """Kode cadangan 2FA sekali pakai (HP hilang). Hanya HMAC-SHA256 kode yang disimpan; kode asli ditampilkan
    sekali saat dibuat. used_at terisi = sudah dipakai."""

    __tablename__ = "mfa_recovery_codes"
    id: Mapped[int] = pk()
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    code_hash: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = created_at()
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    __table_args__ = (
        UniqueConstraint("user_id", "code_hash"),
        CheckConstraint("code_hash ~ '^[0-9a-f]{64}$'", name="code_hash_sha256"),
    )


class Membership(Base):
    __tablename__ = "memberships"
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    scope: Mapped[str] = mapped_column(Text, primary_key=True)  # 'agency' atau client_code
    role: Mapped[str] = mapped_column(Text, nullable=False)
    max_level: Mapped[str] = mapped_column(Text, nullable=False)
    __table_args__ = (
        CheckConstraint(f"scope = 'agency' OR scope ~ '{CLIENT_CODE_RE}'", name="scope_format"),
        CheckConstraint(one_of("role", ROLES), name="role"),
        CheckConstraint(one_of("max_level", LEVELS), name="max_level"),
        # Peran agency hanya di scope agency; approver klien hanya di scope klien.
        CheckConstraint(f"NOT ({one_of('role', AGENCY_ROLES)}) OR scope = 'agency'", name="agency_role_scope"),
        CheckConstraint("role <> 'client_approver' OR scope <> 'agency'", name="client_approver_scope"),
    )


class FactSheet(Base):
    __tablename__ = "fact_sheets"
    id: Mapped[int] = pk()
    client_code: Mapped[str] = mapped_column(ForeignKey("clients.client_code"), nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    document_ref: Mapped[str] = mapped_column(Text, nullable=False)  # referensi opaque ke workspace client
    __table_args__ = (
        UniqueConstraint("client_code", "version"),
        CheckConstraint("version >= 1", name="version_positive"),
    )


class FactConfirmation(Base):
    __tablename__ = "fact_confirmations"
    id: Mapped[int] = pk()
    fact_sheet_id: Mapped[int] = mapped_column(ForeignKey("fact_sheets.id"), nullable=False, index=True)
    fact_key: Mapped[str] = mapped_column(Text, nullable=False)
    value_before: Mapped[str | None] = mapped_column(Text)
    value_after: Mapped[str | None] = mapped_column(Text)
    decision: Mapped[str] = mapped_column(Text, nullable=False)
    confirmed_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    confirmed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    __table_args__ = (CheckConstraint(one_of("decision", FACT_DECISIONS), name="decision"),)


class Brief(Base):
    __tablename__ = "briefs"
    brief_id: Mapped[str] = mapped_column(Text, primary_key=True)
    client_code: Mapped[str] = mapped_column(ForeignKey("clients.client_code"), nullable=False, index=True)
    schema_version: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="draft")
    __table_args__ = (
        # Format dari content-brief.schema.json: <CLIENTCODE>-<YYYYMM>-<NN>, dan prefiks = client_code.
        CheckConstraint("brief_id ~ '^[A-Z0-9]{2,12}-[0-9]{6}-[0-9]{2}$'", name="brief_id_format"),
        CheckConstraint("split_part(brief_id, '-', 1) = client_code", name="brief_id_client"),
        CheckConstraint("jsonb_typeof(payload) = 'object'", name="payload_object"),
    )


class Request(Base):
    __tablename__ = "requests"
    id: Mapped[int] = pk()
    client_code: Mapped[str] = mapped_column(ForeignKey("clients.client_code"), nullable=False, index=True)
    intent: Mapped[str] = mapped_column(Text, nullable=False)
    pillar: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    priority: Mapped[str] = mapped_column(Text, nullable=False, server_default="Normal")
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="open")
    requested_by_role: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = created_at()
    __table_args__ = (
        CheckConstraint(f"intent ~ '{SLUG_RE}'", name="intent_format"),
        CheckConstraint("pillar BETWEEN 1 AND 5", name="pillar_range"),
        CheckConstraint(one_of("priority", PRIORITIES), name="priority"),
    )


class Draft(Base):
    __tablename__ = "drafts"
    id: Mapped[int] = pk()
    request_id: Mapped[int] = mapped_column(ForeignKey("requests.id"), nullable=False, index=True)
    brief_id: Mapped[str | None] = mapped_column(ForeignKey("briefs.brief_id"), index=True)
    skill: Mapped[str] = mapped_column(Text, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    mode: Mapped[str] = mapped_column(Text, nullable=False)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)  # null = dibuat agent
    agent_id: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = created_at()
    __table_args__ = (
        UniqueConstraint("request_id", "version"),
        CheckConstraint("version >= 1", name="version_positive"),
        CheckConstraint(one_of("mode", MODES), name="mode"),
        CheckConstraint("created_by IS NOT NULL OR agent_id IS NOT NULL", name="has_author"),
        CheckConstraint(f"agent_id IS NULL OR agent_id ~ '{SLUG_RE}'", name="agent_id_format"),
    )


class Claim(Base):
    __tablename__ = "claims"
    id: Mapped[int] = pk()
    draft_id: Mapped[int] = mapped_column(ForeignKey("drafts.id"), nullable=False, index=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_label: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str | None] = mapped_column(Text)
    source_date: Mapped[date | None] = mapped_column(Date)
    implied: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    __table_args__ = (
        CheckConstraint(one_of("category", CLAIM_CATEGORIES), name="category"),
        CheckConstraint(one_of("evidence_label", EVIDENCE_LABELS), name="evidence_label"),
        # Constraint Wajib: DATA FINAL wajib punya sumber dan tanggal sumber.
        CheckConstraint(
            "evidence_label <> 'DATA FINAL' OR (coalesce(btrim(source), '') <> '' AND source_date IS NOT NULL)",
            name="data_final_sourced",
        ),
    )


class QARecord(Base):
    __tablename__ = "qa_records"
    id: Mapped[int] = pk()
    draft_id: Mapped[int] = mapped_column(ForeignKey("drafts.id"), nullable=False, index=True)
    gate: Mapped[str] = mapped_column(Text, nullable=False)
    result: Mapped[str] = mapped_column(Text, nullable=False)
    reviewer_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)  # null = agent
    reviewer_role: Mapped[str] = mapped_column(Text, nullable=False)
    independent: Mapped[bool] = mapped_column(Boolean, nullable=False)
    created_at: Mapped[datetime] = created_at()
    __table_args__ = (
        CheckConstraint(one_of("gate", QA_GATES), name="gate"),
        CheckConstraint(one_of("result", QA_RESULTS), name="result"),
        # Constraint Wajib: review oleh agent (reviewer_id null) tidak pernah independen.
        # Reviewer ≠ pembuat draft dicek trigger (butuh tabel drafts).
        CheckConstraint("NOT independent OR reviewer_id IS NOT NULL", name="independent_is_human"),
    )


class Approval(Base):
    __tablename__ = "approvals"
    id: Mapped[int] = pk()
    draft_id: Mapped[int] = mapped_column(ForeignKey("drafts.id"), nullable=False, index=True)  # versi yang disetujui
    level: Mapped[str] = mapped_column(Text, nullable=False)
    decision: Mapped[str] = mapped_column(Text, nullable=False)
    approver_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    approver_role: Mapped[str] = mapped_column(Text, nullable=False)
    channel_ref: Mapped[str | None] = mapped_column(Text)
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    mode: Mapped[str] = mapped_column(Text, nullable=False)
    __table_args__ = (
        CheckConstraint(one_of("level", LEVELS), name="level"),
        CheckConstraint(one_of("decision", APPROVAL_DECISIONS), name="decision"),
        CheckConstraint(one_of("mode", MODES), name="mode"),
        # Constraint Wajib: mode SIMULASI tidak pernah Approved.
        CheckConstraint("NOT (decision = 'Approved' AND mode = 'SIMULASI')", name="simulasi_not_approved"),
    )


class Publication(Base):
    __tablename__ = "publications"
    id: Mapped[int] = pk()
    draft_id: Mapped[int] = mapped_column(ForeignKey("drafts.id"), nullable=False, index=True)
    channel: Mapped[str] = mapped_column(Text, nullable=False)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    url_ref: Mapped[str | None] = mapped_column(Text)
    published_by_role: Mapped[str] = mapped_column(Text, nullable=False)


class ConsentRef(Base):
    __tablename__ = "consent_refs"
    id: Mapped[int] = pk()
    client_code: Mapped[str] = mapped_column(ForeignKey("clients.client_code"), nullable=False, index=True)
    consent_ref: Mapped[str] = mapped_column(Text, nullable=False)  # opaque, tanpa nama/foto
    scope: Mapped[str] = mapped_column(Text, nullable=False)
    valid_until: Mapped[date | None] = mapped_column(Date)


class Notification(Base):
    __tablename__ = "notifications"
    id: Mapped[int] = pk()
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    type: Mapped[str] = mapped_column(Text, nullable=False)
    object_ref: Mapped[str] = mapped_column(Text, nullable=False)
    channel: Mapped[str] = mapped_column(Text, nullable=False)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    __table_args__ = (CheckConstraint(one_of("channel", NOTIFICATION_CHANNELS), name="channel"),)


class AuditLog(Base):
    """Append-only: UPDATE/DELETE/TRUNCATE ditolak trigger, dan role aplikasi tidak punya hak itu."""

    __tablename__ = "audit_log"
    id: Mapped[int] = pk()
    actor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)  # null = system/agent
    action: Mapped[str] = mapped_column(Text, nullable=False)
    object_type: Mapped[str] = mapped_column(Text, nullable=False)
    object_id: Mapped[str] = mapped_column(Text, nullable=False)
    meta: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    created_at: Mapped[datetime] = created_at()
    __table_args__ = (Index("ix_audit_log_object", "object_type", "object_id"),)
