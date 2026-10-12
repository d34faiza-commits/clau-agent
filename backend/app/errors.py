"""Error berbentuk kontrak {"error": {"code", "message"}} (core/shared/api-contracts.md)."""

from __future__ import annotations

import re

# Kode aturan dari trigger database (migrasi 0001) yang boleh diteruskan ke klien apa adanya.
DB_RULE_RE = re.compile(r"\b([a-z]+(?:_[a-z]+)+): ")
DB_RULES = {
    "qa_reviewer_is_author",
    "approval_mode_mismatch",
    "approval_needs_independent_review",
    "publication_without_approval",
    "draft_version_immutable",
    "audit_log_append_only",
}


class ApiError(Exception):
    def __init__(self, status_code: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status_code, self.code, self.message = status_code, code, message


def error_body(code: str, message: str) -> dict:
    return {"error": {"code": code, "message": message}}


def db_rule_code(message: str) -> str:
    """Pelanggaran aturan database -> kode aman untuk klien (tanpa nama tabel/kolom/nilai)."""
    m = DB_RULE_RE.search(message)
    return m.group(1) if m and m.group(1) in DB_RULES else "constraint_violation"
