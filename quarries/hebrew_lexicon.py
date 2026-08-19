from __future__ import annotations

import re
import sqlite3
import unicodedata
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path

from .gematria import breakdown, mispar_gadol

LEXICON_PATH = Path(__file__).with_name("data") / "hebrew.db"


def normalize_latin(value: str) -> str:
    value = (value or "").replace("ʼ", "'").replace("ʻ", "'").replace("ᵉ", "e")
    value = unicodedata.normalize("NFKD", value)
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = value.encode("ascii", "ignore").decode("ascii")
    value = re.sub(r"[^a-zA-Z0-9]+", " ", value).lower()
    return re.sub(r"\s+", " ", value).strip()


def normalize_hebrew(value: str) -> str:
    value = unicodedata.normalize("NFD", value or "")
    value = "".join(
        ch for ch in value
        if not unicodedata.combining(ch) and ch not in "־׃"
    )
    return re.sub(r"\s+", " ", value).strip()


def _ratio(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio() * 100.0


@dataclass(frozen=True)
class LexiconStats:
    words: int
    verses: int
    word_notes: int


class HebrewLexicon:
    """Read-only Hebrew Fuzzy / Strong's reference database.

    This database is deliberately separate from the encrypted Quarries archive.
    The imported gloss/definitions/notes are treated as source data and never
    modified by Quarries.
    """

    def __init__(self, path: Path = LEXICON_PATH) -> None:
        self.path = path
        self.conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        self.conn.row_factory = sqlite3.Row

    def close(self) -> None:
        self.conn.close()

    def stats(self) -> LexiconStats:
        def count(table: str) -> int:
            return int(self.conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
        return LexiconStats(count("words"), count("verses"), count("word_notes"))

    def get_word(self, word_id: int):
        return self.conn.execute("SELECT * FROM words WHERE id=?", (word_id,)).fetchone()

    def search(self, raw: str, limit: int = 80):
        raw = (raw or "").strip()
        if not raw:
            return self.conn.execute(
                "SELECT * FROM words ORDER BY entry_no LIMIT ?", (limit,)
            ).fetchall()

        hebrew_q = normalize_hebrew(raw)
        latin_q = normalize_latin(raw)
        strong_q = raw.upper().replace(" ", "")
        if re.fullmatch(r"H\d+", strong_q):
            exact = self.conn.execute(
                "SELECT * FROM words WHERE upper(strong_id)=? LIMIT ?",
                (strong_q, limit),
            ).fetchall()
            if exact:
                return exact

        # Exact Hebrew/Strong's matches first. Hebrew normalization is done in
        # Python because the source DB preserves the original vocalized forms.
        rows = self.conn.execute("SELECT * FROM words ORDER BY entry_no").fetchall()
        scored: list[tuple[float, sqlite3.Row]] = []
        has_hebrew = any("\u0590" <= ch <= "\u05ff" for ch in raw)

        for row in rows:
            sid = (row["strong_id"] or "").upper()
            hebrew = normalize_hebrew(row["hebrew"] or "")
            lemma = normalize_hebrew(row["lemma"] or "")
            p = normalize_latin(row["pronunciation_norm"] or row["pronunciation"] or "")
            t = normalize_latin(row["transliteration_norm"] or row["transliteration"] or "")
            definitions = normalize_latin(row["definitions"] or "")
            notes = normalize_latin(row["notes"] or "")

            score = 0.0
            if strong_q == sid:
                score = 1000.0
            elif has_hebrew:
                if hebrew_q == hebrew or hebrew_q == lemma:
                    score = 950.0
                elif hebrew_q and (hebrew_q in hebrew or hebrew_q in lemma):
                    score = 800.0
                else:
                    score = max(_ratio(hebrew_q, hebrew), _ratio(hebrew_q, lemma))
            else:
                q = latin_q
                if not q:
                    continue
                if p.startswith(q): score += 140
                elif q in p: score += 100
                if t.startswith(q): score += 130
                elif q in t: score += 90
                if q in definitions: score += 55
                if q in notes: score += 20
                score += max(_ratio(q, p), _ratio(q, t))

            if score >= (55 if not has_hebrew else 42):
                scored.append((score, row))

        scored.sort(key=lambda pair: (-pair[0], pair[1]["entry_no"] or 999999))
        return [row for _, row in scored[:limit]]

    @staticmethod
    def format_word(row: sqlite3.Row) -> str:
        if row is None:
            return "No lexical entry selected."
        return (
            f"[b]{row['lemma'] or row['hebrew'] or '—'}[/b]\n\n"
            f"Strong's: {row['strong_id'] or '—'}\n"
            f"Hebrew: {row['hebrew'] or '—'}\n"
            f"Pronunciation: {row['pronunciation'] or '—'}\n"
            f"Transliteration: {row['transliteration'] or '—'}\n"
            f"Morphology: {row['morphology'] or '—'}\n"
            f"Language: {row['language'] or '—'}\n\n"
            f"[b]Hebrew Fuzzy gloss[/b]\n{row['gloss'] or '—'}\n\n"
            f"[b]Mispar Gadol — Hebrew attached to this gloss[/b]\n"
            f"Hebrew: {row['hebrew'] or row['lemma'] or '—'}\n"
            f"Value: {mispar_gadol(row['hebrew'] or row['lemma'] or '')}\n"
            f"Breakdown: {breakdown(row['hebrew'] or row['lemma'] or '')}\n\n"
            f"[b]Hebrew Fuzzy definitions — preserved[/b]\n{row['definitions'] or '—'}\n\n"
            f"[b]Lexicon / custom notes — preserved[/b]\n{row['notes'] or '—'}\n\n"
            "[dim]Lexical glosses are study aids; verse context and morphology determine translation.[/]"
        )
