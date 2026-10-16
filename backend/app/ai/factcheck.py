"""Fakta klien yang berlaku + AI fact-check (kontrak core api-contracts § AI Menulis Draft).

Fakta yang berlaku = fact sheet versi terbaru yang DISETUJUI klien; nilainya = koreksi terakhir klien bila ada.
Fact-check deterministik di worker (model tidak menentukan label bukti):
- klaim faktual dengan fact_key yang ada di fakta itu, dan (untuk fakta bernilai teks/angka) nilainya muncul di teks
  klaim → DATA FINAL (sumber = fact sheet, tanggal = jawaban klien WITA);
- klaim faktual tanpa fakta yang cocok → RISK dengan kunci itu, sehingga approval terkunci (facts_unconfirmed);
- klaim experience/other → ASSUMPTION; kategori yang tidak dikenal = ditandai (tidak pernah dianggap aman).
Fact-check hanya melihat klaim yang DILAPORKAN model. Karena itu draft agent untuk klien NYATA selalu butuh review
independen manusia (minimal L2, migrasi 0006) yang membaca isinya.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.provider import ClaimOut, FactForPrompt
from app.db.models import CLAIM_CATEGORIES, FACT_KEY_RE, FACTUAL_CATEGORIES, Fact, FactConfirmation, FactSheet

KEY_RE = re.compile(FACT_KEY_RE)
WITA = timezone(timedelta(hours=8))
# Nilai fakta "ya/tidak" (fasilitas ada/tidak) tidak bisa dicocokkan ke teks klaim; nilai lain (angka, nama, jarak)
# harus muncul di klaim supaya klaim berlabel DATA FINAL.
YES_NO = {"ya", "yes", "ada", "tersedia", "true", "tidak", "no", "tidak ada", "false"}


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
            answered[a.fact_key] = a.confirmed_at.astimezone(WITA).date()
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


def norm(text: str) -> str:
    return " ".join(re.sub(r"[^\w]+", " ", text.casefold()).split())


def value_in_claim(value: str, claim_text: str) -> bool:
    v = norm(value)
    return v in YES_NO or (bool(v) and v in norm(claim_text))


def check_claims(claims: tuple[ClaimOut, ...], cf: ClientFacts) -> list[CheckedClaim]:
    out: list[CheckedClaim] = []
    for c in claims:
        text = c.text.replace("\x00", "").strip()[:300] or "(klaim kosong)"
        key = (c.fact_key or "").replace("\x00", "").strip()
        category = (c.category or "").strip().lower()
        if category not in CLAIM_CATEGORIES:
            # Kategori tak dikenal (mis. "Facility", "amenity"): pakai awalan fact_key bila faktual, selain itu tandai.
            prefix = key.split(".", 1)[0]
            category = prefix if prefix in FACTUAL_CATEGORIES else ""
        if not category:  # kunci penanda: tidak ada di fact sheet → approval terkunci facts_unconfirmed
            out.append(CheckedClaim(text, "other", "RISK", "other.tanpa-kategori", None, None, c.implied, False))
            continue
        if category not in FACTUAL_CATEGORIES:
            out.append(CheckedClaim(text, category, "ASSUMPTION", None, None, None, c.implied, True))
            continue
        fact = cf.facts.get(key)
        if fact is not None and fact.category == category and value_in_claim(fact.value, text):
            out.append(CheckedClaim(
                text, category, "DATA FINAL", key, f"fact-sheet {cf.client_code} v{cf.version}",
                cf.answered_on[key], c.implied, True,
            ))
            continue
        # Tidak berdasar: kunci dari model dipakai bila formatnya sah dan sesuai kategori (reviewer melihat apa yang
        # diklaim), selain itu kunci penanda. Kunci RISK yang ada di fact sheet tetap lolos facts_unconfirmed di database,
        # jadi isi klaim yang tidak cocok dengan nilainya diberi kunci penanda agar approval tetap terkunci.
        if fact is not None or not (KEY_RE.match(key) and len(key) <= 64 and key.split(".", 1)[0] == category and "." in key):
            key = f"{category}.tanpa-fakta"
        out.append(CheckedClaim(text, category, "RISK", key, None, None, c.implied, False))
    return out
