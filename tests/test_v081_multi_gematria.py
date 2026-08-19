from pathlib import Path
from quarries.gematria import (
    method_results, factorization_text, reduction_chain,
    mispar_hechrachi, mispar_gadol, mispar_siduri,
)

def test_408_structure():
    assert factorization_text(408) == "2^3 × 3 × 17"
    assert reduction_chain(408) == [408,12,3]

def test_basic_methods():
    assert mispar_hechrachi("שלום") == 376
    assert mispar_gadol("שלום") == 936
    assert mispar_siduri("אב") == 3
    rows=method_results("שלום")
    names={r["method"] for r in rows}
    assert "Mispar Shemi" in names
    assert "AtBash" in names
    assert "Reverse Avgad" in names
    assert len(rows) >= 19

def test_ui_export():
    text=(Path(__file__).parents[1]/"quarries"/"app.py").read_text()
    assert "Export Methods CSV" in text
    assert "ALL GEMATRIA METHODS" in text
    assert "number_explanation" in text
