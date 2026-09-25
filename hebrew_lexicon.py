from __future__ import annotations

import re
import sqlite3
import unicodedata
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path

from .gematria import breakdown, mispar_gadol, method_results, hebrew_numeral

LEXICON_PATH = Path(__file__).with_name("data") / "hebrew.db"


def normalize_latin(value: str) -> str:
    value = (value or "").replace("ʼ", "'").replace("ʻ", "'").replace("ᵉ", "e")
    value = unicodedata.normalize("NFKD", value)
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = value.encode("ascii", "ignore").decode("ascii")
    value = re.sub(r"[^a-zA-Z0-9]+", " ", value).lower()
    return re.sub(r"\s+", " ", value).strip()


def strip_hebrew_marks(value: str) -> str:
    """Remove Hebrew vowel points/cantillation while preserving consonantal letters.

    Gematria is calculated from letters, so combining Hebrew marks are intentionally
    excluded. The original pointed spelling is preserved elsewhere for display and
    lexical context.
    """
    value = unicodedata.normalize("NFD", value or "")
    return "".join(ch for ch in value if not unicodedata.combining(ch))


def normalize_hebrew(value: str) -> str:
    value = strip_hebrew_marks(value)
    value = "".join(ch for ch in value if ch not in "־׃")
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

    def gematria_matches(self, value: int, gloss: str = "", limit: int = 8):
        """Find lexicon entries with the same standard gematria, gloss-ranked locally."""
        q = normalize_latin(gloss)
        matches=[]
        for row in self.conn.execute("SELECT * FROM words ORDER BY entry_no"):
            heb=row["hebrew"] or row["lemma"] or ""
            # Dictionary number correspondence uses standard/non-final values.
            from .gematria import mispar_hechrachi
            if mispar_hechrachi(heb) != value:
                continue
            hay=normalize_latin(" ".join([row["gloss"] or "", row["definitions"] or "", row["transliteration"] or ""]))
            score=_ratio(q, hay) if q else 0.0
            if q and q in hay:
                score += 100.0
            matches.append((score,row))
        matches.sort(key=lambda x:(-x[0], x[1]["entry_no"] or 999999))
        return [row for _,row in matches[:limit]]

    def format_word(self, row: sqlite3.Row) -> str:
        if row is None:
            return "No lexical entry selected."
        heb=row['hebrew'] or row['lemma'] or ''
        methods=method_results(heb)
        method_lines=[]
        for item in methods:
            xform=f" → {item['transformed']}" if item.get('transformed') else ""
            method_lines.append(f"{item['method']} {item['hebrew_name']} = {item['value']}{xform}\n  {item['rule']}")
        standard=next((int(x['value']) for x in methods if x['method']=='Mispar Hechrachi'),0)
        matches=self.gematria_matches(standard, row['gloss'] or row['definitions'] or '', limit=6) if standard else []
        match_lines=[f"{m['strong_id'] or '—'}  {m['hebrew'] or m['lemma'] or '—'} — {(m['gloss'] or m['definitions'] or '—').splitlines()[0][:90]}" for m in matches if m['id'] != row['id']]
        extra=("\n".join(match_lines) if match_lines else "No other gloss-ranked Strong's matches at this exact standard value.")
        return (
            f"[b]{row['lemma'] or row['hebrew'] or '—'}[/b]\n\n"
            f"Strong's: {row['strong_id'] or '—'}\n"
            f"Hebrew: {row['hebrew'] or '—'}\n"
            f"Pronunciation: {row['pronunciation'] or '—'}\n"
            f"Transliteration: {row['transliteration'] or '—'}\n"
            f"Morphology: {row['morphology'] or '—'}\n"
            f"Language: {row['language'] or '—'}\n\n"
            f"[b]Hebrew Fuzzy gloss[/b]\n{row['gloss'] or '—'}\n\n"
            f"[b]Gematria — Hebrew attached to this gloss[/b]\n"
            f"Hebrew: {heb or '—'}\n"
            f"Standard value: {standard}  •  Hebrew numeral: {hebrew_numeral(standard)}\n"
            f"Mispar Gadol: {mispar_gadol(heb)}\n"
            f"Breakdown: {breakdown(heb)}\n\n"
            f"[b]ALL GEMATRIA METHODS ({len(methods)})[/b]\n" + "\n\n".join(method_lines) + "\n\n"
            f"[b]Same-value Hebrew entries — ranked against this gloss[/b]\n{extra}\n\n"
            f"[b]Hebrew Fuzzy definitions — preserved[/b]\n{row['definitions'] or '—'}\n\n"
            f"[b]Lexicon / custom notes — preserved[/b]\n{row['notes'] or '—'}\n\n"
            "[dim]Lexical glosses are study aids; verse context and morphology determine translation.[/]"
        )

    # ---- Tanakh / word-study integration ----
    def books(self):
        """Return Tanakh books in familiar canonical order."""
        rows=self.conn.execute(
            """SELECT book_code, book, MIN(id) AS first_id, MAX(chapter) AS chapters,
                      COUNT(*) AS verses
               FROM verses GROUP BY book_code, book"""
        ).fetchall()
        order=["Gen","Exod","Lev","Num","Deut","Josh","Judg","1Sam","2Sam","1Kgs","2Kgs",
               "Isa","Jer","Ezek","Hos","Joel","Amos","Obad","Jonah","Mic","Nah","Hab","Zeph","Hag","Zech","Mal",
               "Ps","Prov","Job","Song","Ruth","Lam","Eccl","Esth","Dan","Ezra","Neh","1Chr","2Chr"]
        rank={code:i for i,code in enumerate(order)}
        return sorted(rows,key=lambda r:(rank.get(r["book_code"],999),r["book"]))

    def chapters(self, book_code: str):
        return [int(r[0]) for r in self.conn.execute(
            "SELECT DISTINCT chapter FROM verses WHERE book_code=? ORDER BY chapter", (book_code,)
        ).fetchall()]

    def chapter(self, book_code: str, chapter: int):
        return self.conn.execute(
            """SELECT id, book, book_code, chapter, verse, reference, hebrew, hebrew_norm, english
               FROM verses WHERE book_code=? AND chapter=? ORDER BY verse""",
            (book_code, int(chapter)),
        ).fetchall()

    def verse(self, verse_id: int):
        return self.conn.execute("SELECT * FROM verses WHERE id=?", (int(verse_id),)).fetchone()

    @staticmethod
    def surface_candidates(surface: str) -> list[str]:
        """Generate conservative lookup forms for a pointed/segmented biblical token."""
        raw = normalize_hebrew(surface or "")
        raw = raw.strip("[](){}.,;:!?\"'׳״* ")
        forms: list[str] = []
        def add(x: str):
            x=(x or "").strip()
            if x and x not in forms: forms.append(x)
        add(raw)
        add(raw.replace("/", ""))
        parts=[p for p in raw.split("/") if p]
        if parts:
            add(parts[-1])
            if len(parts)>1: add("".join(parts))
        compact=raw.replace("/", "")
        # Common attached conjunction/article/preposition candidates.  These are
        # candidates only; callers display confidence rather than silently asserting a lemma.
        for n in (1,2):
            if len(compact)>n+1 and all(ch in "ובכלמהש" for ch in compact[:n]):
                add(compact[n:])
        return forms

    def resolve_surface(self, surface: str, limit: int = 5):
        """Rank Strong's candidates for a biblical surface form."""
        forms=self.surface_candidates(surface)
        seen: dict[int, tuple[float, sqlite3.Row, str]] = {}
        for idx, form in enumerate(forms):
            rows=self.search(form, limit=max(15, limit*3))
            for rank,row in enumerate(rows):
                target=normalize_hebrew(row["hebrew"] or row["lemma"] or "")
                lemma=normalize_hebrew(row["lemma"] or row["hebrew"] or "")
                ratio=max(_ratio(form,target),_ratio(form,lemma))
                exact = form in (target, lemma)
                score=(100.0 if exact else ratio) - idx*2.5 - rank*.15
                prev=seen.get(int(row["id"]))
                if prev is None or score>prev[0]: seen[int(row["id"])]=(score,row,form)
        ranked=sorted(seen.values(),key=lambda x:(-x[0],x[1]["entry_no"] or 999999))[:limit]
        return ranked

    def occurrences(self, lemma_or_surface: str, limit: int = 24):
        """Return verses containing the same normalized consonantal token/segment.

        OSHB verse text uses ``/`` to segment prefixes/suffixes.  Matching complete
        segments avoids the false positives caused by substring matching (for
        example, a short lemma accidentally occurring inside a different word).
        These are textual consonantal-form occurrences, not a claim that every hit
        has the same lexical sense in context.
        """
        q=normalize_hebrew(lemma_or_surface or "").replace("/", "")
        if not q:return []
        rows=[]
        for row in self.conn.execute(
            "SELECT id,book,book_code,chapter,verse,reference,hebrew,hebrew_norm,english FROM verses ORDER BY id"
        ):
            hay=normalize_hebrew(row["hebrew_norm"] or "")
            segments=[seg for seg in re.split(r"[\s/]+", hay) if seg]
            if q in segments:
                rows.append(row)
                if len(rows)>=limit:break
        return rows
