from pathlib import Path

def test_reference_context_flow_is_visible_and_guarded():
    text=(Path(__file__).parents[1]/"quarries"/"app.py").read_text()
    assert "watcher-reference-context" in text
    assert "Watcher is locked. Unlock The Watcher first" in text
    assert 'memory.value = "current"' in text
    assert 'tabs.active = "watcher-tab"' in text
    assert "clear_reference_context" in text
    assert "Reference Context is intentionally session-only" in text
