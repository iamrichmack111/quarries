from quarries.gematria import factorization_text, hebrew_letters
from quarries.research import enriched_methods


def test_factorization_uses_ascii_caret():
    assert factorization_text(276) == "2^2 × 3 × 23"
    assert "²" not in factorization_text(276)


def test_niqqud_is_ignored_for_gematria_input():
    assert hebrew_letters("שָׁלוֹם") == "שלום"


def test_enriched_methods_attach_reference_key_to_every_method():
    rows = enriched_methods("שלום", include_reference=True)
    assert len(rows) >= 19
    assert all("reference_hits" in row for row in rows)
    assert all("factorization" in row for row in rows)
