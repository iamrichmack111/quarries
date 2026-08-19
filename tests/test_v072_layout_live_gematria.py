from pathlib import Path

def test_live_gematria_and_chart_watcher_removed():
    base=Path(__file__).parents[1]
    app=(base/"quarries"/"app.py").read_text()
    css=(base/"quarries"/"styles.tcss").read_text()
    assert '@on(Input.Changed, "#gematria-input")' in app
    assert "Paste or type Hebrew — calculates automatically" in app
    assert 'id="obs-watcher"' not in app
    assert "Send Chart to Watcher" not in app
    assert "#gematria-toolbar" in css and "height: 5;" in css
    assert "#hebrew-detail-pane" in css and "width: 47%;" in css
