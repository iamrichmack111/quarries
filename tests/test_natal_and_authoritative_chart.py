from pathlib import Path
from quarries.observatory import _dignity, HOUSE_DOMAINS

def test_traditional_dignity_guardrails():
    assert _dignity("Jupiter", "Leo") == "Peregrine"
    assert _dignity("Saturn", "Aries") == "Fall"
    assert _dignity("Moon", "Scorpio") == "Fall"
    assert _dignity("Sun", "Leo") == "Domicile"

def test_house_domains():
    assert "self" in HOUSE_DOMAINS[1]
    assert "career" in HOUSE_DOMAINS[10]

def test_natal_ui_and_watcher_rules():
    text=(Path(__file__).parents[1]/"quarries"/"app.py").read_text()
    assert "Natal / Birth Chart" in text
    assert "Birth date YYYY-MM-DD" in text
    assert "Birth time HH:MM" in text
