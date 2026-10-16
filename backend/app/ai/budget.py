"""Batas biaya AI per bulan (WITA). Fail closed: tanpa batas `global` bulan berjalan, AI ditolak."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import AiBudget, AiCall, AiJob, Request

WITA = timezone(timedelta(hours=8))


def month_start(day: date | None = None) -> date:
    d = day or datetime.now(WITA).date()
    return d.replace(day=1)


def month_bounds(month: date) -> tuple[datetime, datetime]:
    start = datetime(month.year, month.month, 1, tzinfo=WITA)
    nxt = datetime(month.year + (month.month == 12), month.month % 12 + 1, 1, tzinfo=WITA)
    return start, nxt


def spent(db: Session, month: date, client_code: str | None = None) -> int:
    start, end = month_bounds(month)
    stmt = select(func.coalesce(func.sum(AiCall.cost_micro_usd), 0)).where(AiCall.created_at >= start, AiCall.created_at < end)
    if client_code is not None:
        stmt = stmt.join(AiJob, AiJob.id == AiCall.job_id).join(Request, Request.id == AiJob.request_id).where(Request.client_code == client_code)
    return int(db.scalar(stmt))


def budget_problem(db: Session, client_code: str, estimate: int, month: date | None = None) -> str | None:
    """None = boleh; selain itu kode: `ai_budget_missing` / `ai_budget_exceeded`."""
    month = month or month_start()
    glob = db.get(AiBudget, ("global", month))
    if glob is None:
        return "ai_budget_missing"
    if spent(db, month) + estimate > glob.limit_micro_usd:
        return "ai_budget_exceeded"
    per_client = db.get(AiBudget, (client_code, month))
    if per_client is not None and spent(db, month, client_code) + estimate > per_client.limit_micro_usd:
        return "ai_budget_exceeded"
    return None
