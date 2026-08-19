from __future__ import annotations
import unicodedata

# Mispar Gadol: final letters receive their extended values.
VALUES = {
    "א":1,"ב":2,"ג":3,"ד":4,"ה":5,"ו":6,"ז":7,"ח":8,"ט":9,
    "י":10,"כ":20,"ל":30,"מ":40,"נ":50,"ס":60,"ע":70,"פ":80,"צ":90,
    "ק":100,"ר":200,"ש":300,"ת":400,
    "ך":500,"ם":600,"ן":700,"ף":800,"ץ":900,
}

def hebrew_letters(text: str) -> str:
    text = unicodedata.normalize("NFD", text or "")
    return "".join(ch for ch in text if ch in VALUES)

def mispar_gadol(text: str) -> int:
    return sum(VALUES.get(ch, 0) for ch in hebrew_letters(text))

def breakdown(text: str) -> str:
    letters = hebrew_letters(text)
    if not letters:
        return "—"
    return " + ".join(f"{ch}({VALUES[ch]})" for ch in letters) + f" = {mispar_gadol(letters)}"
