from quarries.hebrew_lexicon import HebrewLexicon, normalize_hebrew, strip_hebrew_marks


def test_explicit_vowel_removal_example():
    assert strip_hebrew_marks("שָׁלוֹם") == "שלום"
    assert normalize_hebrew("וּבָאָרֶץ") == "ובארץ"


def test_occurrences_are_complete_consonantal_segments():
    lex = HebrewLexicon()
    try:
        rows = lex.occurrences("אלהים", limit=5)
        assert rows
        for row in rows:
            segments = [s for s in normalize_hebrew(row["hebrew_norm"]).replace(" ", "/").split("/") if s]
            assert "אלהים" in segments
    finally:
        lex.close()
