from pathlib import Path

def test_reference_model_split():
    base=Path(__file__).parents[1]
    oll=(base/"quarries"/"ollama_client.py").read_text()
    app=(base/"quarries"/"app.py").read_text()
    assert 'REFERENCE_MODEL = "gemma3:4b"' in oll
    assert "model=selected_model" in app
    assert 'REFERENCE_MODEL if mode in ("current", "current_similar")' in app

def test_independent_locks_restored():
    app=(Path(__file__).parents[1]/"quarries"/"app.py").read_text()
    assert "unlock_session_keys" not in app
    assert "remember_session_key" not in app
    assert 'yield Button("Lock All"' in app
    assert "self.app.archive_key = None" in app
    assert "self.app.chat_key = None" in app
