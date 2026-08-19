from pathlib import Path
from quarries.storage import Store
from quarries.gematria import mispar_gadol

def test_saved_hebrew_words_round_trip(tmp_path):
    store = Store(tmp_path / "archive.qry")
    store.save_hebrew_word(42, "2026-08-18T00:00:00-04:00")
    assert int(store.list_saved_hebrew_words()[0]["word_id"]) == 42
    store.remove_hebrew_word(42)
    assert store.list_saved_hebrew_words() == []

def test_app_explains_lahiri_and_exports():
    text=(Path(__file__).parents[1]/"quarries"/"app.py").read_text()
    assert "Lahiri" in text and "ayanamsa" in text
    assert "calculates automatically" in text
    assert "Export CSV" in text
    assert "Save Word" in text
