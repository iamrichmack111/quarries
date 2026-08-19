from pathlib import Path

def test_gematria_enter_and_reference_validator():
    app=(Path(__file__).parents[1]/"quarries"/"app.py").read_text()
    assert '@on(Input.Submitted, "#gematria-input")' in app
    assert "def validate_reference_reply" in app
    assert "VALIDATION FAILURE" in app
    assert "generated interpretation was withheld" in app
    assert "The preserved custom gloss is missing." in app
