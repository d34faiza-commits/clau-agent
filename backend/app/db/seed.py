"""Data contoh SIMULASI untuk kerja lokal: 4 klien fiktif (vertical fokus), masing-masing satu request
dan satu draft buatan agent berstatus SIMULASI dengan klaim berlabel ASSUMPTION.

Bukan data client nyata (CLAUDE.md): kode klien berawalan CTH (= "Contoh"), selaras pilot fiktif di
clau-ai-marketing/examples/. Idempoten: dijalankan berulang tidak menggandakan data.

    python -m app.db.seed          # memakai CLAU_DATABASE_URL (role aplikasi)
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.db.models import Claim, Client, Draft, Request, QARecord

SEED_ROLE = "seed-simulasi"

CLIENTS = [
    ("CTHVILLA", "accommodation", "villa", "Ubud (fiktif)", "caption", "draft-caption", "caption-writer",
     "SIMULASI — Pagi tenang di Villa Contoh: kolam pribadi menghadap sawah.", ("Kolam renang pribadi", "facility")),
    ("CTHCAFE", "food-beverage", "cafe", "Canggu (fiktif)", "caption", "draft-caption", "caption-writer",
     "SIMULASI — Kopi Contoh: menu sarapan baru setiap Senin.", ("Menu sarapan berganti tiap Senin", "food-beverage")),
    ("CTHWED", "wedding-event", "wedding venue", "Uluwatu (fiktif)", "caption", "draft-caption", "caption-writer",
     "SIMULASI — Venue Contoh: upacara di tepi tebing saat matahari terbenam.", ("Kapasitas 120 tamu", "capacity")),
    ("CTHTRIP", "travel-tour", "tour operator", "Labuan Bajo (fiktif)", "caption", "draft-caption", "caption-writer",
     "SIMULASI — Trip Contoh: 3 hari 2 malam keliling Komodo.", ("Itinerary 3 hari 2 malam", "itinerary")),
]


def seed(session: Session) -> int:
    """Kembalikan jumlah klien yang baru diisi request/draft-nya."""
    created = 0
    for code, vertical, business, area, intent, skill, agent, content, (claim_text, category) in CLIENTS:
        session.execute(
            insert(Client)
            .values(client_code=code, vertical=vertical, business_type=business, location_area=area, approver_role="owner")
            .on_conflict_do_nothing(index_elements=["client_code"])
        )
        exists = session.scalar(select(Request.id).where(Request.client_code == code, Request.requested_by_role == SEED_ROLE))
        if exists:
            continue
        request = Request(client_code=code, intent=intent, pillar=1, priority="Normal", status="open", requested_by_role=SEED_ROLE)
        session.add(request)
        session.flush()
        draft = Draft(request_id=request.id, skill=skill, version=1, content=content, mode="SIMULASI", agent_id=agent)
        session.add(draft)
        session.flush()
        session.add(Claim(draft_id=draft.id, text=claim_text, category=category, evidence_label="ASSUMPTION"))
        # Self-review agent: pre-check saja, tidak pernah independen (rule 08).
        session.add(QARecord(draft_id=draft.id, gate="claim-verification", result="Conditional", reviewer_role="agent", independent=False))
        created += 1
    return created


def main() -> None:
    from app.db.session import session_factory

    with session_factory().begin() as session:
        created = seed(session)
    print(f"seed SIMULASI: {created} klien baru diisi ({len(CLIENTS)} total)")


if __name__ == "__main__":
    main()
