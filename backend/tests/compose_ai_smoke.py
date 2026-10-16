"""Smoke test antrean AI di docker compose (CI job `docker`): container backend → database → container worker.

Dijalankan di dalam container backend (role aplikasi, tanpa akses admin):
    docker compose exec -T backend python - < backend/tests/compose_ai_smoke.py
Membuat data SIMULASI saja (klien CTHAI), memasukkan satu job AI, lalu menunggu worker (CLAU_AI_ENABLED=1,
provider tiruan) menyelesaikannya: draft agent + klaim DATA FINAL dari fact sheet + QA otomatis + catatan biaya.
Kode keluar 0 = lulus.
"""

import sys
import time

from sqlalchemy import func, select

from app.ai.budget import month_start
from app.db.models import (
    AiBudget, AiCall, AiJob, Claim, Client, Draft, Fact, FactConfirmation, FactSheet, Membership, QARecord, Request, User,
)
from app.db.session import session_factory

make = session_factory()
tag = str(int(time.time()))
with make() as s, s.begin():
    if s.get(Client, "CTHAI") is None:
        s.add(Client(client_code="CTHAI", vertical="accommodation", business_type="villa", approver_role="owner", simulation=True))
    lead = User(display_name="Lead Smoke", email=f"lead-{tag}@contoh.test")
    approver = User(display_name="Approver Smoke", email=f"approver-{tag}@contoh.test")
    s.add_all([lead, approver])
    s.flush()
    s.add_all([Membership(user_id=lead.id, scope="agency", role="content_lead", max_level="L3"),
               Membership(user_id=approver.id, scope="CTHAI", role="client_approver", max_level="L2")])
    s.flush()
    version = (s.scalar(select(func.max(FactSheet.version)).where(FactSheet.client_code == "CTHAI")) or 0) + 1
    sheet = FactSheet(client_code="CTHAI", version=version, document_ref="workspace://smoke", created_by=lead.id)
    s.add(sheet)
    s.flush()
    s.add(Fact(fact_sheet_id=sheet.id, fact_key="facility.pool-private", category="facility", label="Kolam pribadi", value="ya"))
    s.flush()
    s.add(FactConfirmation(fact_sheet_id=sheet.id, fact_key="facility.pool-private", decision="confirmed",
                           confirmed_by=approver.id, confirmed_by_role="client_approver"))
    s.flush()
    sheet.approved_at, sheet.approved_by, sheet.approved_by_role = func.now(), approver.id, "client_approver"
    req = Request(client_code="CTHAI", intent="caption", pillar=1, approval_min="L1", text="Caption pagi [uji:klaim-tanpa-fakta]",
                  requested_by=lead.id, requested_by_role="content_lead")
    s.add(req)
    s.flush()
    if s.get(AiBudget, ("global", month_start())) is None:
        s.add(AiBudget(scope="global", month=month_start(), limit_micro_usd=1_000_000, updated_by=lead.id))
    job = AiJob(request_id=req.id, agent_id="caption-writer", intent="caption", fact_sheet_id=sheet.id, requested_by=lead.id)
    s.add(job)
    s.flush()
    job_id = job.id

deadline = time.time() + 90
while time.time() < deadline:
    with make() as s:
        job = s.get(AiJob, job_id)
        if job.status in ("succeeded", "failed", "cancelled"):
            break
    time.sleep(2)

with make() as s:
    job = s.get(AiJob, job_id)
    print(f"job {job.id}: {job.status} {job.error_code or ''} attempts={job.attempts}")
    if job.status != "succeeded":
        sys.exit(1)
    draft = s.get(Draft, job.draft_id)
    claims = {c.fact_key: c.evidence_label for c in s.scalars(select(Claim).where(Claim.draft_id == draft.id))}
    qa = [q.result for q in s.scalars(select(QARecord).where(QARecord.draft_id == draft.id))]
    calls = s.scalar(select(func.count()).select_from(AiCall).where(AiCall.job_id == job.id))
    print(f"draft {draft.id}: agent={draft.agent_id} mode={draft.mode} claims={claims} qa={qa} calls={calls}")
    ok = (draft.created_by is None and draft.mode == "SIMULASI" and claims.get("facility.pool-private") == "DATA FINAL"
          and claims.get("facility.pantai-pribadi") == "RISK" and qa == ["Fail"] and calls == 1)
    sys.exit(0 if ok else 1)
