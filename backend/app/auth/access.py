"""Aturan hak akses dari tabel memberships (core/shared/database-schema.md).

Semua keputusan akses dibuat di server dari data ini, tidak pernah dari UI. Klien (client_approver/viewer
dengan scope client_code) hanya melihat client_code miliknya; staf agency melihat semua klien.
"""

from __future__ import annotations

from collections.abc import Iterable

from app.db.models import Membership

LEVEL_ORDER = {"L1": 1, "L2": 2, "L3": 3}
AGENCY = "agency"


def agency_role(memberships: Iterable[Membership]) -> str | None:
    return next((m.role for m in memberships if m.scope == AGENCY), None)


def is_owner(memberships: Iterable[Membership]) -> bool:
    return agency_role(memberships) == "owner"


def mfa_required(memberships: Iterable[Membership]) -> bool:
    """2FA wajib untuk owner (keputusan owner 2026-10-12); diperluas ke content_lead di tahap berikutnya."""
    return is_owner(memberships)


def visible_client_codes(memberships: Iterable[Membership]) -> set[str] | None:
    """None = semua klien (staf agency). Set = hanya klien ini. Set kosong = tidak ada klien."""
    memberships = list(memberships)
    if agency_role(memberships) is not None:
        return None
    return {m.scope for m in memberships if m.scope != AGENCY}


def can_access_client(memberships: Iterable[Membership], client_code: str) -> bool:
    visible = visible_client_codes(memberships)
    return visible is None or client_code in visible


def max_level_for(memberships: Iterable[Membership], client_code: str) -> str | None:
    """Level approval tertinggi user untuk klien ini (scope klien diutamakan, lalu agency)."""
    memberships = list(memberships)
    for scope in (client_code, AGENCY):
        level = next((m.max_level for m in memberships if m.scope == scope), None)
        if level:
            return level
    return None


def can_approve(memberships: Iterable[Membership], client_code: str, level: str) -> bool:
    allowed = max_level_for(memberships, client_code)
    return allowed is not None and LEVEL_ORDER[allowed] >= LEVEL_ORDER[level]
