from quarries.torahcalc_reference import TorahCalcReference
from pathlib import Path

def test_number_lookup_and_methods():
    ref=TorahCalcReference()
    rows=ref.lookup_value(73)
    assert rows
    assert all(int(r["value"]) == 73 for r in rows)
    assert ref.methods()
    ref.close()

def test_concept_search_and_related():
    ref=TorahCalcReference()
    rows=ref.search_text("wisdom")
    assert rows
    related=ref.related(int(rows[0]["id"]),limit=3)
    assert isinstance(related,list)
    ref.close()

def test_ui_has_gematria_dictionary_tab():
    text=(Path(__file__).parents[1]/"quarries"/"app.py").read_text()
    assert 'TabPane("Gematria Dictionary"' in text
    assert 'placeholder="Enter a number, e.g. 73"' in text
    assert "RELATED CONCEPTS" in text
