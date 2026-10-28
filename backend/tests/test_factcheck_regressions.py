"""Regression cases from the hospitality readiness audit; no model or client data."""
from datetime import date

import pytest

from app.ai.factcheck import ClientFacts, check_claims, fact_matches_claim, value_in_claim
from app.ai.provider import ClaimOut, FactForPrompt


@pytest.mark.parametrize("value,claim", [
    ("tidak", "Kolam renang pribadi tersedia"),
    ("false", "Private pool available"),
    ("ya", "Pantai pribadi"),
    ("2", "Kapasitas 20 tamu"),
    ("2 tamu", "Kapasitas 12 tamu"),
    ("1.5", "15"),
    ("-2", "2"),
    ("Ubud", "Bukan di Ubud"),
    ("Rp 500.000, belum termasuk pajak", "Rp 500.000"),
    ("", ""),
])
def test_substring_boolean_negation_and_dropped_conditions_are_not_evidence(value, claim):
    assert not value_in_claim(value, claim)


def test_boolean_requires_exact_subject_and_value():
    fact = FactForPrompt("facility.pool", "facility", "Kolam pribadi", "tidak")
    assert fact_matches_claim(fact, "Kolam pribadi: tidak")
    for claim in ("Kolam pribadi: ya", "Pantai pribadi: tidak", "tidak", "Kolam pribadi tersedia"):
        assert not fact_matches_claim(fact, claim)


def test_ambiguous_or_misclassified_claim_never_becomes_grounded():
    fact = FactForPrompt("capacity.guests", "capacity", "Kapasitas", "2 tamu")
    cf = ClientFacts(1, "CONTOH", 1, {fact.fact_key: fact}, {fact.fact_key: date(2026, 10, 28)})
    checked = check_claims((
        ClaimOut("Kapasitas 12 tamu", "capacity", fact.fact_key),
        ClaimOut("Kapasitas 12 tamu", "experience", fact.fact_key),
        ClaimOut("Kapasitas: 2 tamu", "capacity", fact.fact_key),
    ), cf)
    assert [c.grounded for c in checked] == [False, False, True]
    assert checked[0].fact_key == "capacity.tanpa-fakta"


@pytest.mark.parametrize("text", ["", " " * 10, "x" * 301])
def test_claims_are_never_silently_truncated(text):
    with pytest.raises(ValueError, match="invalid_output"):
        check_claims((ClaimOut(text, "experience"),), ClientFacts(1, "CONTOH", 1, {}, {}))
