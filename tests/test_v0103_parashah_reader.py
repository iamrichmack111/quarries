from quarries.parashah import _clean_hebrew_fragment, _verse_refs


def test_parashah_cleaner_decodes_nbsp_entities():
    raw = "האזינו&nbsp;&nbsp;השמים\u00a0ואדברה"
    assert _clean_hebrew_fragment(raw) == "האזינו השמים ואדברה"


def test_parashah_cleaner_strips_markup():
    assert _clean_hebrew_fragment("<b>שלום</b>&nbsp;עולם") == "שלום עולם"


def test_simple_torah_range_generates_verse_refs():
    refs = _verse_refs("Deuteronomy 32:1-3", 3)
    assert refs == ["Deuteronomy 32:1", "Deuteronomy 32:2", "Deuteronomy 32:3"]
