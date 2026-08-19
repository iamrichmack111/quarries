from pathlib import Path
from quarries.observatory import SIGN_FACTS_BLOCK

def test_immutable_sign_facts():
    assert "Aries = Fire / Cardinal / Yang" in SIGN_FACTS_BLOCK
    assert "Scorpio = Water / Fixed / Yin" in SIGN_FACTS_BLOCK

def test_hebrew_gloss_and_gematria_visible_in_reference():
    text=(Path(__file__).parents[1]/"quarries"/"app.py").read_text()
    assert "PRESERVED CUSTOM GLOSS" in text
    assert "MISPAR GADOL" in text
    assert "preview=preview" in text
    assert "Always include the preserved custom gloss" in text
