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
MAX_CLAIMS = 30  # sama dengan batas klaim per draft di API (DraftIn)


def log(msg: str) -> None:
    print(f"[clau-ai-worker] {msg}", flush=True)


def now() -> datetime:
    return datetime.now(timezone.utc)


def system_audit(db: Session, action: str, job: AiJob, **meta: object) -> None:
    db.add(AuditLog(actor_id=None, action=action, object_type="ai_job", object_id=str(job.id), meta={"agent_id": job.agent_id, **meta}))


def reap(db: Session, timeout_s: int) -> int:
    """Job running yang terlalu lama (worker mati) → antre lagi, atau failed bila percobaan habis. Worker lama yang
    ternyata masih hidup kehilangan kepemilikan (lease) dan tidak bisa menyimpan hasilnya lagi."""
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


def fail_queued(db: Session, code: str) -> int:
    """Tombol mati: job yang masih antre langsung gagal (tidak menunggu AI dinyalakan lagi)."""
    jobs = list(db.scalars(select(AiJob).where(AiJob.status == "queued").with_for_update(skip_locked=True)))
    for job in jobs:
        job.status, job.error_code, job.finished_at = "failed", code, now()
        system_audit(db, "ai_job.failed", job, code=code, attempt=job.attempts)
    db.commit()
    return len(jobs)


@dataclass(frozen=True)
class Lease:
    """Kepemilikan job oleh satu worker untuk satu percobaan. Hasil hanya disimpan bila lease masih berlaku."""

    job_id: int
    attempts: int
    worker: str


def claim(db: Session, worker_id: str) -> Lease | None:
    row = db.execute(text(
        "UPDATE ai_jobs SET status = 'running', attempts = attempts + 1, locked_at = now(), locked_by = :w "
        "WHERE id = (SELECT id FROM ai_jobs WHERE status = 'queued' AND run_after <= now() "
        "ORDER BY run_after, id FOR UPDATE SKIP LOCKED LIMIT 1) RETURNING id, attempts"
    ), {"w": worker_id[:100]}).first()
    db.commit()
    return Lease(row[0], row[1], worker_id[:100]) if row else None


def owned_job(db: Session, lease: Lease) -> AiJob | None:
    job = db.scalar(select(AiJob).where(AiJob.id == lease.job_id).with_for_update())
    if job is None or job.status != "running" or job.locked_by != lease.worker or job.attempts != lease.attempts:
        return None
    return job


def record_call(db: Session, job_id: int, provider: str, usage: Usage, prompt_version: str, latency_ms: int = 0) -> None:
    db.add(AiCall(
        job_id=job_id, provider=provider[:50], model=usage.model[:100], prompt_version=(prompt_version or "n/a")[:64],
        input_tokens=usage.input_tokens, output_tokens=usage.output_tokens, cache_read_tokens=usage.cache_read_tokens,
        cache_write_tokens=usage.cache_write_tokens, cost_micro_usd=usage.cost_micro_usd,
        stop_reason=(usage.stop_reason or None) and usage.stop_reason[:50],
        provider_request_id=(usage.provider_request_id or None) and usage.provider_request_id[:200], latency_ms=latency_ms,
    ))


def record_orphan_call(db: Session, lease: Lease, provider: str, usage: Usage | None, prompt_version: str) -> None:
    """Panggilan yang sudah dibayar tetap tercatat walau lease hilang (job diambil alih / dibatalkan)."""
    db.rollback()
    if usage is not None:
        record_call(db, lease.job_id, provider, usage, prompt_version)
        db.commit()


def fail(db: Session, lease: Lease, code: str, provider: str, usage: Usage | None = None, retry: bool = False,
         prompt_version: str = "") -> str:
    job = owned_job(db, lease)
    if job is None:
        record_orphan_call(db, lease, provider, usage, prompt_version)
        return "skipped"
    if usage is not None:
        record_call(db, job.id, provider, usage, prompt_version)
    if retry and job.attempts < job.max_attempts:
        delay = 30 * 2 ** (job.attempts - 1)  # 30 s, 60 s, 120 s ...
        job.status, job.run_after, job.locked_at, job.locked_by = "queued", now() + timedelta(seconds=delay), None, None
        system_audit(db, "ai_job.retry", job, code=code, attempt=job.attempts)
    else:
        job.status, job.error_code, job.finished_at = "failed", code, now()
        system_audit(db, "ai_job.failed", job, code=code, attempt=job.attempts)
    db.commit()
    return job.status


@dataclass
class Context:
    job_id: int
    agent_id: str
    intent: str
    client_code: str
    request_text: str
    facts: ClientFacts


def allowed(db: Session, job: AiJob, req: Request) -> str | None:
    """None = job boleh dikerjakan/disimpan; selain itu kode error. Dicek sebelum DAN sesudah panggilan model."""
    settings = ai_settings()
    client = db.get(Client, req.client_code)
    agent = agent_for_intent(job.intent)
    if not settings.enabled or job.intent not in settings.intents or agent is None or agent["status"] != "active":
        return "ai_disabled"
    if settings.provider == "fake" and not client.simulation:
        return "ai_disabled"  # provider tiruan tidak pernah menulis untuk klien nyata
    if req.status not in OPEN:
        return "request_closed"
    # Perkiraan biaya per job harus masih muat di batas global & klien (bukan sekadar "masih ada sisa").
    if budget_problem(db, req.client_code, max(settings.job_estimate_micro_usd, 1)) is not None:
        return "budget_exceeded"
    return None


def load_context(db: Session, lease: Lease) -> Context | str:
    job = owned_job(db, lease)
    if job is None:
        return "skipped"
    req = db.get(Request, job.request_id)
    problem = allowed(db, job, req)
    if problem:
        return problem
    facts = client_facts(db, req.client_code)
    if facts is None:  # fakta versi terbaru yang disetujui saat job dikerjakan (koreksi klien terbaru ikut)
        return "fact_sheet_missing"
    return Context(job.id, job.agent_id, job.intent, req.client_code, req.text, facts)


def clean(text_: str) -> str:
    return text_.replace("\x00", "")


def save_result(db: Session, lease: Lease, ctx: Context, gen: Generation, provider: str, prompt_version: str, latency_ms: int) -> int | str:
    """Simpan draft + klaim + QA + catatan panggilan dalam satu transaksi; kode error bila tidak boleh disimpan."""
    job = owned_job(db, lease)
    if job is None:
        return "skipped"
    req = db.scalar(select(Request).where(Request.id == job.request_id).with_for_update())
    problem = allowed(db, job, req)
    if problem == "budget_exceeded":
        problem = None  # panggilan sudah dibayar: hasilnya disimpan, job berikutnya yang ditolak
    if problem:
        return problem
    if len(gen.claims) > MAX_CLAIMS:
        return "invalid_output"  # tidak ada klaim (termasuk yang tidak berdasar) yang boleh terbuang diam-diam
    client = db.get(Client, req.client_code)
    agent = agent_for_intent(job.intent)
    checked = check_claims(gen.claims, ctx.facts)
    version = (db.scalar(select(func.max(Draft.version)).where(Draft.request_id == req.id)) or 0) + 1
    draft = Draft(
        request_id=req.id, fact_sheet_id=ctx.facts.sheet_id, skill=agent["skill"] or agent["prompt"] or agent["template"],
        version=version, content=clean(gen.content)[:10_000] or "(kosong)", mode="SIMULASI" if client.simulation else "NYATA",
        created_by=None, agent_id=job.agent_id,
    )
    db.add(draft)
    db.flush()  # trigger: draft agent NYATA hanya dari job running (ai_draft_without_job)
    db.add_all(Claim(draft_id=draft.id, text=c.text, category=c.category, evidence_label=c.evidence_label, source=c.source,
                     source_date=c.source_date, implied=c.implied, fact_key=c.fact_key) for c in checked)
    flagged = sum(not c.grounded for c in checked)
    db.add(QARecord(draft_id=draft.id, gate="claim-verification", result="Fail" if flagged else "Pass",
                    reviewer_id=None, reviewer_role="agent", independent=False))
    record_call(db, job.id, provider, gen.usage, prompt_version, latency_ms)
    req.status = "in_progress"
    # Fact sheet yang benar-benar dipakai (bisa lebih baru dari saat job dibuat).
    job.fact_sheet_id = ctx.facts.sheet_id
    job.status, job.draft_id, job.finished_at = "succeeded", draft.id, now()
    db.flush()  # trigger: draft hasil cocok dengan job (ai_job_draft_mismatch)
    db.add(AuditLog(actor_id=None, action="draft.create", object_type="draft", object_id=str(draft.id),
                    meta={"request_id": req.id, "version": version, "claims": len(checked), "flagged": flagged,
                          "mode": draft.mode, "agent_id": job.agent_id, "ai_job_id": job.id}))
    system_audit(db, "ai_job.succeeded", job, draft_id=draft.id, flagged=flagged)
    db.commit()
    return draft.id


def process(make: sessionmaker, provider, lease: Lease) -> str:
    name = getattr(provider, "name", "unknown")
    with make() as db:
        ctx = load_context(db, lease)
        if isinstance(ctx, str):
            return fail(db, lease, ctx, name) if ctx != "skipped" else ctx
        prompt = build_prompt(ctx.agent_id, ctx.intent, list(ctx.facts.facts.values()), ctx.request_text)
        db.rollback()  # lepas snapshot/kunci sebelum panggilan model yang bisa lama
    started = time.monotonic()
    try:
        gen = provider.generate(prompt)
    except ProviderFailure as e:
        log(f"job {lease.job_id}: provider gagal ({e.code})")
        with make() as db:
            return fail(db, lease, e.code, name, usage=e.usage, retry=e.retryable, prompt_version=prompt.prompt_version)
    except Exception as e:  # noqa: BLE001 — error tak terduga dari provider: kode tetap, tanpa detail ke API
        log(f"job {lease.job_id}: provider error {type(e).__name__}")
        with make() as db:
            return fail(db, lease, "provider_error", name, prompt_version=prompt.prompt_version)
    latency = int((time.monotonic() - started) * 1000)
    with make() as db:
        try:
            result = save_result(db, lease, ctx, gen, name, prompt.prompt_version, latency)
        except Exception as e:  # noqa: BLE001 — aturan database / nilai tak valid: job gagal jelas, biaya tetap dicatat
            db.rollback()
            code = "request_closed" if "request_closed" in str(getattr(e, "orig", e)) else "invalid_output"
            log(f"job {lease.job_id}: hasil ditolak ({code}, {type(e).__name__})")
            return fail(db, lease, code, name, usage=gen.usage, prompt_version=prompt.prompt_version)
        if isinstance(result, str):
            db.rollback()
            if result == "skipped":
                record_orphan_call(db, lease, name, gen.usage, prompt.prompt_version)
                return result
            return fail(db, lease, result, name, usage=gen.usage, prompt_version=prompt.prompt_version)
    return "succeeded"


def run_once(make: sessionmaker, provider, worker_id: str) -> str | None:
    settings = ai_settings()
    with make() as db:
        reap(db, settings.worker_timeout_s)
    if not settings.enabled:
        with make() as db:
            fail_queued(db, "ai_disabled")
        return None
    with make() as db:
        lease = claim(db, worker_id)
    if lease is None:
        return None
    status = process(make, provider, lease)
    log(f"job {lease.job_id}: {status}")
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
        try:
            provider = get_provider(settings.provider) if settings.enabled else None
            done = run_once(make, provider, worker_id)
        except Exception as e:  # noqa: BLE001 — database putus dsb.: tunggu lalu coba lagi, worker tidak mati
            log(f"putaran gagal: {type(e).__name__}")
            done = None
        if done is None:
            time.sleep(settings.poll_interval_s)
    log("berhenti")


if __name__ == "__main__":
    main()
