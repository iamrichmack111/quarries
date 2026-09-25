from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from importlib.resources import files
import math
import re
import sqlite3

TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z'-]{2,}")

@dataclass(frozen=True)
class GematriaValueHit:
    id: int
    value: int
    source_page: int
    body: str

class TorahCalcReference:
    """Read-only structured reference extracted from the user-supplied TorahCalc PDF."""

    def __init__(self) -> None:
        self.path = files("quarries").joinpath("data/torahcalc.db")
        uri = f"file:{self.path}?mode=ro"
        self.conn = sqlite3.connect(uri, uri=True)
        self.conn.row_factory = sqlite3.Row

    def close(self) -> None:
        self.conn.close()

    def stats(self) -> tuple[int, int]:
        row=self.conn.execute(
            "SELECT COUNT(*) AS rows, COUNT(DISTINCT value) AS values FROM value_sections"
        ).fetchone()
        return int(row["rows"]), int(row["values"])

    def lookup_value(self, value: int) -> list[sqlite3.Row]:
        return self.conn.execute(
            "SELECT id,value,source_page,body FROM value_sections WHERE value=? ORDER BY source_page,id",
            (value,),
        ).fetchall()

    def search_text(self, query: str, limit: int = 40) -> list[sqlite3.Row]:
        q=query.strip()
        if not q:
            return []
        try:
            return self.conn.execute(
                """SELECT v.id,v.value,v.source_page,v.body
                   FROM value_fts f JOIN value_sections v ON v.id=f.rowid
                   WHERE value_fts MATCH ? ORDER BY bm25(value_fts) LIMIT ?""",
                (q,limit),
            ).fetchall()
        except sqlite3.OperationalError:
            like=f"%{q}%"
            return self.conn.execute(
                "SELECT id,value,source_page,body FROM value_sections WHERE body LIKE ? LIMIT ?",
                (like,limit),
            ).fetchall()

    def methods(self) -> list[sqlite3.Row]:
        return self.conn.execute(
            "SELECT name,hebrew_name,description,source_page FROM methods ORDER BY id"
        ).fetchall()

    @staticmethod
    def _tokens(text: str) -> Counter[str]:
        stop={"the","and","that","with","from","this","for","are","was","were","has","have",
              "into","to","of","or","a","an","in","is","be","as","on","by","pr","see","also"}
        return Counter(
            t.lower() for t in TOKEN_RE.findall(text)
            if t.lower() not in stop
        )

    def related(self, source_id: int, limit: int = 12) -> list[tuple[sqlite3.Row,float]]:
        src=self.conn.execute(
            "SELECT id,value,source_page,body FROM value_sections WHERE id=?",(source_id,)
        ).fetchone()
        if not src:
            return []
        a=self._tokens(src["body"])
        if not a:
            return []
        rows=self.conn.execute(
            "SELECT id,value,source_page,body FROM value_sections WHERE id<>?",(source_id,)
        ).fetchall()
        scored=[]
        na=math.sqrt(sum(v*v for v in a.values())) or 1.0
        for row in rows:
            b=self._tokens(row["body"])
            if not b:
                continue
            common=set(a)&set(b)
            dot=sum(a[t]*b[t] for t in common)
            if not dot:
                continue
            nb=math.sqrt(sum(v*v for v in b.values())) or 1.0
            score=dot/(na*nb)
            if score>0.08:
                scored.append((row,score))
        scored.sort(key=lambda x:(-x[1], abs(int(x[0]["value"])-int(src["value"]))))
        return scored[:limit]

    @staticmethod
    def format_hit(row: sqlite3.Row) -> str:
        return (
            f"[b]Gematria value {row['value']}[/b]  •  Source PDF page {row['source_page']}\n\n"
            f"{row['body']}\n\n"
            "[dim]Source note: this text is displayed from the local structured reference "
            "derived from the user-supplied PDF; Quarries does not silently rewrite it.[/]"
        )
