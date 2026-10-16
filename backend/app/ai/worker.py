"""Worker antrean AI: `python -m app.ai.worker` (service `worker` di docker compose).

Satu job per putaran:
1. Job yang macet (worker mati di tengah jalan) dikembalikan ke antrean, atau gagal `worker_timeout` bila jatah habis.
2. Ambil satu job `queued` dengan FOR UPDATE SKIP LOCKED (aman untuk banyak worker sekaligus).
3. Baca konteks (request, fakta klien yang dikonfirmasi, budget), lalu lepas transaksi: panggilan model bisa lama dan
   tidak boleh mengunci request.
4. Panggil provider. Gagal sementara = antre ulang dengan jeda bertambah; gagal lain = job `failed` dengan kode tetap.
5. Transaksi baru dengan request dikunci: cek ulang status, AI fact-check, simpan draft agent + klaim + QA otomatis +
   catatan panggilan (`ai_calls`, tanpa isi) + jejak audit, job `succeeded`.

Yang ditulis ke log hanya id job, status, dan kode; tidak pernah isi request, fakta, atau hasil.
"""

from __future__ import annotations

import os
import signal
import socket
import time
from dataclasses import dataclass
from pathlib import Path
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select, text, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.ai.budget import budget_problem
from app.ai.config import ai_settings
from app.ai.factcheck import ClientFacts, check_claims, client_facts
from app.ai.prompt import build_prompt
from app.ai.provider import Generation, ProviderFailure, Usage, get_provider
from app.db.models import AiCall, AiJob, AuditLog, Claim, Client, Draft, QARecord, Request
from app.registry import agent_for_intent

OPEN = ("open", "in_progress")
HEARTBEAT = "/tmp/clau-worker-alive"


def log(msg: str) -> None:
    print(f"[clau-ai-worker] {msg}", flush=True)


def now() -> datetime:
    return datetime.now(timezone.utc)


def system_audit(db: Session, action: str, job: AiJob, **meta: object) -> None:
    db.add(AuditLog(actor_id=None, action=action, object_type="ai_job", object_id=str(job.id), meta={"agent_id": job.agent_id, **meta}))


def reap(db: Session, timeout_s: int) -> int:
    """Job running yang terlalu lama (worker mati) → antre lagi, atau failed bila percobaan habis."""
    cutoff = now() - timedelta(seconds=timeout_s)
    stale = list(db.scalars(select(AiJob).where(AiJob.status == "running", AiJob.locked_at < cutoff).with_for_update(skip_locked=True)))
    for job in stale:
        if job.attempts < job.max_attempts:
            job.status, job.run_after, job.locked_at, job.locked_by = "queued", now(), None, None
        else:
            job.status, job.error_code, job.finished_at = "failed", "worker_timeout", now()
        system_audit(db, "ai_job.reaped", job, status=job.status)
    db.commit()
    return len(stale)


def claim(db: Session, worker_id: str) -> int | None:
    job_id = db.scalar(text(
        "UPDATE ai_jobs SET status = 'running', attempts = attempts + 1, locked_at = now(), locked_by = :w "
        "WHERE id = (SELECT id FROM ai_jobs WHERE status = 'queued' AND run_after <= now() "
        "ORDER BY run_after, id FOR UPDATE SKIP LOCKED LIMIT 1) RETURNING id"
    ), {"w": worker_id[:100]})
    db.commit()
    return job_id


def fail(db: Session, job_id: int, code: str, usage: Usage | None = None, retry: bool = False) -> str:
    job = db.scalar(select(AiJob).where(AiJob.id == job_id).with_for_update())
    if job is None or job.status != "running":
        db.rollback()
        return "skipped"
    if usage is not None:
        record_call(db, job, usage, "")
    if retry and job.attempts < job.max_attempts:
        delay = 30 * 2 ** (job.attempts - 1)  # 30 s, 60 s, 120 s ...
        job.status, job.run_after, job.locked_at, job.locked_by = "queued", now() + timedelta(seconds=delay), None, None
        system_audit(db, "ai_job.retry", job, code=code, attempt=job.attempts)
    else:
        job.status, job.error_code, job.finished_at = "failed", code, now()
        system_audit(db, "ai_job.failed", job, code=code, attempt=job.attempts)
    db.commit()
    return job.status


def record_call(db: Session, job: AiJob, usage: Usage, prompt_version: str, latency_ms: int = 0) -> None:
    db.add(AiCall(
        job_id=job.id, provider=ai_settings().provider, model=usage.model[:100], prompt_version=(prompt_version or "n/a")[:64],
        input_tokens=usage.input_tokens, output_tokens=usage.output_tokens, cache_read_tokens=usage.cache_read_tokens,
        cache_write_tokens=usage.cache_write_tokens, cost_micro_usd=usage.cost_micro_usd,
        stop_reason=(usage.stop_reason or None) and usage.stop_reason[:50],
        provider_request_id=(usage.provider_request_id or None) and usage.provider_request_id[:200], latency_ms=latency_ms,
    ))


@dataclass
class Context:
    job_id: int
    agent_id: str
    intent: str
    client_code: str
    request_text: str
    facts: ClientFacts


def load_context(db: Session, job_id: int) -> Context | str:
    """Konteks job, atau kode error bila job tidak boleh dikerjakan."""
    settings = ai_settings()
    job = db.get(AiJob, job_id)
    req = db.get(Request, job.request_id)
    client = db.get(Client, req.client_code)
    agent = agent_for_intent(job.intent)
    if not settings.enabled or job.intent not in settings.intents or agent is None or agent["status"] != "active":
        return "ai_disabled"
    if settings.provider == "fake" and not client.simulation:
        return "ai_disabled"  # provider tiruan tidak pernah menulis untuk klien nyata
    if req.status not in OPEN:
        return "request_closed"
    facts = client_facts(db, req.client_code)
    if facts is None:  # fakta versi terbaru yang disetujui saat job dikerjakan (koreksi klien terbaru ikut)
        return "fact_sheet_missing"
    # Perkiraan biaya sudah dicek saat job dibuat; di sini cukup: masih ada sisa batas (≥ 1 mikro-USD).
    if budget_problem(db, req.client_code, 1) is not None:
        return "budget_exceeded"
    return Context(job_id, job.agent_id, job.intent, req.client_code, req.text, facts)


def save_result(db: Session, ctx: Context, gen: Generation, prompt_version: str, latency_ms: int) -> int | str:
    """Simpan draft + klaim + QA + catatan panggilan; kode error bila request sudah berubah."""
    job = db.scalar(select(AiJob).where(AiJob.id == ctx.job_id).with_for_update())
    if job is None or job.status != "running":
        return "skipped"
    req = db.scalar(select(Request).where(Request.id == job.request_id).with_for_update())
    if req.status not in OPEN:
        return "request_closed"
    client = db.get(Client, req.client_code)
    agent = agent_for_intent(job.intent)
    checked = check_claims(gen.claims, ctx.facts)
    version = (db.scalar(select(func.max(Draft.version)).where(Draft.request_id == req.id)) or 0) + 1
    draft = Draft(
        request_id=req.id, fact_sheet_id=ctx.facts.sheet_id, skill=agent["skill"] or agent["prompt"] or agent["template"],
        version=version, content=gen.content[:10_000] or "(kosong)", mode="SIMULASI" if client.simulation else "NYATA",
        created_by=None, agent_id=job.agent_id,
    )
    db.add(draft)
    db.flush()  # trigger: draft agent NYATA hanya dari job running (ai_draft_without_job)
    db.add_all(Claim(draft_id=draft.id, text=c.text, category=c.category, evidence_label=c.evidence_label, source=c.source,
                     source_date=c.source_date, implied=c.implied, fact_key=c.fact_key) for c in checked[:30])
    flagged = sum(not c.grounded for c in checked)
    db.add(QARecord(draft_id=draft.id, gate="claim-verification", result="Fail" if flagged else "Pass",
                    reviewer_id=None, reviewer_role="agent", independent=False))
    record_call(db, job, gen.usage, prompt_version, latency_ms)
    req.status = "in_progress"
    job.status, job.draft_id, job.finished_at = "succeeded", draft.id, now()
    db.flush()  # trigger: draft hasil cocok dengan job (ai_job_draft_mismatch)
    db.add(AuditLog(actor_id=None, action="draft.create", object_type="draft", object_id=str(draft.id),
                    meta={"request_id": req.id, "version": version, "claims": len(checked), "flagged": flagged,
                          "mode": draft.mode, "agent_id": job.agent_id, "ai_job_id": job.id}))
    system_audit(db, "ai_job.succeeded", job, draft_id=draft.id, flagged=flagged)
    db.commit()
    return draft.id


def process(make: sessionmaker, provider, job_id: int) -> str:
    with make() as db:
        ctx = load_context(db, job_id)
        if isinstance(ctx, str):
            return fail(db, job_id, ctx)
        prompt = build_prompt(ctx.agent_id, ctx.intent, list(ctx.facts.facts.values()), ctx.request_text)
        db.rollback()  # lepas snapshot/kunci sebelum panggilan model yang bisa lama
    started = time.monotonic()
    try:
        gen = provider.generate(prompt)
    except ProviderFailure as e:
        log(f"job {job_id}: provider gagal ({e.code})")
        with make() as db:
            return fail(db, job_id, e.code, usage=e.usage, retry=e.retryable)
    except Exception as e:  # noqa: BLE001 — error tak terduga dari provider: kode tetap, tanpa detail ke API
        log(f"job {job_id}: provider error {type(e).__name__}")
        with make() as db:
            return fail(db, job_id, "provider_error")
    latency = int((time.monotonic() - started) * 1000)
    with make() as db:
        try:
            result = save_result(db, ctx, gen, prompt.prompt_version, latency)
        except IntegrityError as e:
            db.rollback()
            code = "request_closed" if "request_closed" in str(e.orig) else "invalid_output"
            log(f"job {job_id}: hasil ditolak database ({code})")
            return fail(db, job_id, code, usage=gen.usage)
        if isinstance(result, str):
            db.rollback()
            return fail(db, job_id, result, usage=gen.usage) if result != "skipped" else result
    return "succeeded"


def run_once(make: sessionmaker, provider, worker_id: str) -> str | None:
    settings = ai_settings()
    with make() as db:
        reap(db, settings.worker_timeout_s)
    with make() as db:
        job_id = claim(db, worker_id)
    if job_id is None:
        return None
    status = process(make, provider, job_id)
    log(f"job {job_id}: {status}")
    return status


def main() -> None:
    from app.db.session import session_factory

    make = session_factory()
    worker_id = os.environ.get("CLAU_AI_WORKER_ID") or f"{socket.gethostname()}-{os.getpid()}"
    stop = False

    def handle(*_: object) -> None:
        nonlocal stop
        stop = True

    signal.signal(signal.SIGTERM, handle)
    signal.signal(signal.SIGINT, handle)
    log(f"mulai ({worker_id})")
    while not stop:
        Path(HEARTBEAT).touch()  # healthcheck container: putaran masih berjalan
        settings = ai_settings()
        if not settings.enabled:
            time.sleep(settings.poll_interval_s)
            continue
        try:
            done = run_once(make, get_provider(settings.provider), worker_id)
        except Exception as e:  # noqa: BLE001 — database putus dsb.: tunggu lalu coba lagi, worker tidak mati
            log(f"putaran gagal: {type(e).__name__}")
            done = None
        if done is None:
            time.sleep(settings.poll_interval_s)
    log("berhenti")


if __name__ == "__main__":
    main()
