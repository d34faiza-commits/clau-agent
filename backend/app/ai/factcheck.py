"""Fakta klien yang berlaku + AI fact-check (kontrak core api-contracts § AI Menulis Draft).

Fakta yang berlaku = fact sheet versi terbaru yang DISETUJUI klien; nilainya = koreksi terakhir klien bila ada.
Fact-check deterministik di worker (model tidak menentukan label bukti):
- klaim faktual dengan fact_key yang ada di fakta itu → DATA FINAL (sumber = fact sheet, tanggal = jawaban klien);
- klaim faktual tanpa fact_key yang berdasar → RISK dengan kunci itu, sehingga approval terkunci (facts_unconfirmed);
- klaim experience/other → ASSUMPTION.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.provider import ClaimOut, FactForPrompt
from app.db.models import CLAIM_CATEGORIES, FACT_KEY_RE, FACTUAL_CATEGORIES, Fact, FactConfirmation, FactSheet

KEY_RE = re.compile(FACT_KEY_RE)


@dataclass(frozen=True)
class ClientFacts:
    # Nilai biasa, bukan objek ORM: dipakai worker setelah sesi database ditutup (panggilan model di luar transaksi).
    sheet_id: int
    client_code: str
    version: int
    facts: dict[str, FactForPrompt]
    answered_on: dict[str, date]


def latest_approved_sheet(db: Session, client_code: str) -> FactSheet | None:
    return db.scalar(
        select(FactSheet).where(FactSheet.client_code == client_code, FactSheet.approved_at.is_not(None))
        .order_by(FactSheet.version.desc()).limit(1)
    )


def client_facts(db: Session, client_code: str) -> ClientFacts | None:
    sheet = latest_approved_sheet(db, client_code)
    if sheet is None:
        return None
    facts = {f.fact_key: f for f in db.scalars(select(Fact).where(Fact.fact_sheet_id == sheet.id))}
    answers = db.scalars(
        select(FactConfirmation).where(FactConfirmation.fact_sheet_id == sheet.id)
        .order_by(FactConfirmation.confirmed_at, FactConfirmation.id)
    )
    value: dict[str, str] = {}
    answered: dict[str, date] = {}
    for a in answers:  # jawaban terakhir per fakta yang berlaku (kontrak 0.8.0)
        if a.fact_key in facts:
            value[a.fact_key] = a.value_after if a.decision == "corrected" and a.value_after else facts[a.fact_key].value
            answered[a.fact_key] = a.confirmed_at.date()
    confirmed = {
        key: FactForPrompt(fact_key=key, category=f.category, label=f.label, value=value[key])
        for key, f in facts.items() if key in value
    }
    return ClientFacts(sheet_id=sheet.id, client_code=sheet.client_code, version=sheet.version, facts=confirmed, answered_on=answered)


@dataclass(frozen=True)
class CheckedClaim:
    text: str
    category: str
    evidence_label: str
    fact_key: str | None
    source: str | None
    source_date: date | None
    implied: bool
    grounded: bool


def check_claims(claims: tuple[ClaimOut, ...], cf: ClientFacts) -> list[CheckedClaim]:
    out: list[CheckedClaim] = []
    for c in claims:
        category = c.category if c.category in CLAIM_CATEGORIES else "other"
        text = c.text.strip()[:300] or "(klaim kosong)"
        if category not in FACTUAL_CATEGORIES:
            out.append(CheckedClaim(text, category, "ASSUMPTION", None, None, None, c.implied, True))
            continue
        key = (c.fact_key or "").strip()
        if key in cf.facts and cf.facts[key].category == category:
            out.append(CheckedClaim(
                text, category, "DATA FINAL", key, f"fact-sheet {cf.client_code} v{cf.version}",
                cf.answered_on[key], c.implied, True,
            ))
            continue
        # Tidak berdasar: kunci dari model dipakai bila formatnya sah dan sesuai kategori (reviewer melihat apa yang
        # diklaim), selain itu kunci penanda. Kunci ini tidak ada di fact sheet → approval terkunci facts_unconfirmed.
        if not (KEY_RE.match(key) and len(key) <= 64 and key.split(".", 1)[0] == category and "." in key):
            key = f"{category}.tanpa-fakta"
        out.append(CheckedClaim(text, category, "RISK", key, None, None, c.implied, False))
    return out
