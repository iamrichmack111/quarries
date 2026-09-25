from __future__ import annotations

import json
import os
import re
from datetime import datetime
from pathlib import Path

from .gematria import factorization_text, hebrew_numeral, method_results, reduction_chain
from .storage import DATA_DIR
from .torahcalc_reference import TorahCalcReference

RESEARCH_DIR = DATA_DIR / "research"
GEMATRIA_JSONL = RESEARCH_DIR / "gematria-entries.jsonl"
PARASHAH_DIR = RESEARCH_DIR / "parashah"


def _ensure_dirs() -> None:
    RESEARCH_DIR.mkdir(parents=True, exist_ok=True)
    PARASHAH_DIR.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(RESEARCH_DIR, 0o700)
        os.chmod(PARASHAH_DIR, 0o700)
    except OSError:
        pass


def reference_hits(value: int) -> list[dict]:
    ref = TorahCalcReference()
    try:
        return [dict(row) for row in ref.lookup_value(int(value))]
    finally:
        ref.close()


def enriched_methods(text: str, include_reference: bool = True) -> list[dict]:
    rows = []
    ref = TorahCalcReference() if include_reference else None
    cache: dict[int, list[dict]] = {}
    try:
        for item in method_results(text):
            value = int(item["value"])
            row = dict(item)
            row["hebrew_numeral"] = hebrew_numeral(value)
            row["factorization"] = factorization_text(value)
            row["reduction_chain"] = reduction_chain(value)
            if ref is not None:
                if value not in cache:
                    cache[value] = [dict(hit) for hit in ref.lookup_value(value)]
                row["reference_hits"] = cache[value]
            else:
                row["reference_hits"] = []
            rows.append(row)
        return rows
    finally:
        if ref is not None:
            ref.close()


def analysis_record(text: str, source: dict | None = None, include_reference: bool = True) -> dict:
    return {
        "saved_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "text": text,
        "source": source or {"type": "manual"},
        "methods": enriched_methods(text, include_reference=include_reference),
    }


def save_analysis(text: str, source: dict | None = None) -> tuple[dict, Path]:
    _ensure_dirs()
    record = analysis_record(text, source=source, include_reference=True)
    with GEMATRIA_JSONL.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")
    try:
        os.chmod(GEMATRIA_JSONL, 0o600)
    except OSError:
        pass
    return record, GEMATRIA_JSONL


def save_parashah_analysis(name: str, date: str, payload: dict) -> Path:
    _ensure_dirs()
    safe = re.sub(r"[^a-zA-Z0-9._-]+", "-", (name or "parashah").strip()).strip("-").lower() or "parashah"
    day = re.sub(r"[^0-9-]", "", date or "") or datetime.now().date().isoformat()
    path = PARASHAH_DIR / f"{day}-{safe}.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass
    return path

WORD_STUDY_JSONL = RESEARCH_DIR / "word-studies.jsonl"

def save_word_study(payload: dict) -> Path:
    """Append a combined lexical/Tanakh/Gematria study record locally."""
    _ensure_dirs()
    record=dict(payload or {})
    record.setdefault("saved_at", datetime.now().astimezone().isoformat(timespec="seconds"))
    with WORD_STUDY_JSONL.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")
    try: os.chmod(WORD_STUDY_JSONL, 0o600)
    except OSError: pass
    return WORD_STUDY_JSONL
