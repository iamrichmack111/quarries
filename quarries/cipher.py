from __future__ import annotations

"""
Quarries Alphabet v1.0

This is a deterministic English-to-Hebrew-letter substitution system.
It is not Hebrew translation and it is not phonetic inference.

Longest-match rules are applied first:
    th -> ת
    sh -> ש
    ch -> ח

Then each remaining English letter is substituted directly.
The original English remains encrypted in SQLite and is the authoritative source.
"""

ALPHABET_VERSION = "1.0"

DIGRAPHS: tuple[tuple[str, str], ...] = (
    ("th", "ת"),
    ("sh", "ש"),
    ("ch", "ח"),
)

LETTERS: dict[str, str] = {
    "a": "א",
    "b": "ב",
    "c": "כ",
    "d": "ד",
    "e": "ה",
    "f": "ו",
    "g": "ג",
    "h": "ה",
    "i": "י",
    "j": "ג׳",
    "k": "ך",
    "l": "ל",
    "m": "מ",
    "n": "נ",
    "o": "ו",
    "p": "פ",
    "q": "ק",
    "r": "ר",
    "s": "ס",
    "t": "ט",
    "u": "ו",
    "v": "ב",
    "w": "ו",
    "x": "צ",
    "y": "י",
    "z": "ז",
}


def encode_exact(text: str) -> str:
    """Encode English with Quarries Alphabet v1.0."""
    lower = text.lower()
    output: list[str] = []
    index = 0

    while index < len(text):
        matched = False

        # Digraphs must be matched before individual letters.
        for source, target in DIGRAPHS:
            if lower.startswith(source, index):
                output.append(target)
                index += len(source)
                matched = True
                break

        if matched:
            continue

        character = text[index]
        mapped = LETTERS.get(character.lower())

        # Preserve spaces, punctuation, digits, and unsupported Unicode exactly.
        output.append(mapped if mapped is not None else character)
        index += 1

    return "".join(output)


def group_345_rtl(encoded: str) -> str:
    """
    Create the Hebrew-only visual layer.

    Spaces, punctuation, digits, and non-Hebrew characters are omitted from the
    grouped view. Groups are built from the right in repeating sizes 3, 4, 5.
    """
    letters = "".join(
        character
        for character in encoded
        if "\u0590" <= character <= "\u05ff"
    )

    if not letters:
        return ""

    sizes = (3, 4, 5)
    groups: list[str] = []
    cursor = len(letters)
    pattern_index = 0

    while cursor > 0:
        size = sizes[pattern_index % len(sizes)]
        start = max(0, cursor - size)
        groups.append(letters[start:cursor])
        cursor = start
        pattern_index += 1

    # Right-to-left mark keeps the first generated group on the right.
    return "\u200f" + "  ".join(groups)


def normal_hebrew_view(text: str) -> str:
    """Return the ungrouped encoded text for verification."""
    return "\u200f" + encode_exact(text)
