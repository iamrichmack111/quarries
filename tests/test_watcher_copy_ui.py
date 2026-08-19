from pathlib import Path

def test_watcher_copy_binding_and_larger_history():
    app=(Path(__file__).parents[1]/"quarries"/"app.py").read_text()
    css=(Path(__file__).parents[1]/"quarries"/"styles.tcss").read_text()
    assert '("f8", "copy_watcher_response", "Copy Watcher")' in app
    assert "Copy Last Response [F8]" in app
    assert "def copy_last_response" in app
    assert "min-height: 18;" in css
    assert "width: 20;" in css
