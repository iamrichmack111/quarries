from __future__ import annotations

import html
import json
import re
from datetime import date, datetime, timedelta
from urllib.parse import quote

import httpx

from .storage import DATA_DIR

CACHE = DATA_DIR / "parashah-cache.json"
CACHE_SCHEMA = 3
HEBCAL = "https://www.hebcal.com/hebcal"
SEFARIA = "https://www.sefaria.org/api/texts/"


def _next_saturday(today: date) -> date:
    return today + timedelta(days=(5 - today.weekday()) % 7)


def _load_cache() -> dict | None:
    try:
        return json.loads(CACHE.read_text(encoding="utf-8"))
    except Exception:
        return None


def _save_cache(data: dict) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _extract_ref(event: dict) -> str:
    leyning = event.get("leyning") or {}
    return leyning.get("torah") or leyning.get("fullkriyah", {}).get("1", {}).get("k") or ""


def _clean_hebrew_fragment(value: str) -> str:
    """Turn Sefaria HTML/entity text into clean display text.

    Sefaria occasionally returns literal ``&nbsp;`` entities inside Hebrew strings.
    We decode entities before stripping tags and collapse non-breaking/duplicate spaces.
    """
    value = html.unescape(value or "")
    value = re.sub(r"<br\s*/?>", " ", value, flags=re.I)
    value = re.sub(r"<[^>]+>", " ", value)
    value = value.replace("\u00a0", " ")
    value = re.sub(r"(?:&nbsp;|&#160;|&#xA0;)", " ", value, flags=re.I)
    return re.sub(r"\s+", " ", value).strip()


def _flatten_strings(value) -> list[str]:
    out: list[str] = []
    if isinstance(value, str):
        cleaned = _clean_hebrew_fragment(value)
        if cleaned:
            out.append(cleaned)
    elif isinstance(value, list):
        for child in value:
            out.extend(_flatten_strings(child))
    return out


def _verse_refs(ref: str, count: int) -> list[str]:
    """Generate useful refs for the common single-chapter range returned by Hebcal."""
    m = re.match(r"^(.+?)\s+(\d+):(\d+)-(\d+)$", (ref or "").strip())
    if m:
        book, chapter, first, last = m.groups()
        first_i, last_i = int(first), int(last)
        refs = [f"{book} {chapter}:{n}" for n in range(first_i, last_i + 1)]
        if len(refs) >= count:
            return refs[:count]
    m = re.match(r"^(.+?)\s+(\d+):(\d+)$", (ref or "").strip())
    if m and count == 1:
        return [ref]
    return [f"Verse {i}" for i in range(1, count + 1)]


def _fetch_hebrew_text(ref: str) -> dict:
    if not ref:
        return {"text": "", "verses": []}
    url = SEFARIA + quote(ref.replace(" ", "_"), safe="_:-")
    r = httpx.get(url, params={"lang": "he", "context": 0}, timeout=12.0, follow_redirects=True)
    r.raise_for_status()
    data = r.json()
    raw = data.get("he") or data.get("text") or ""
    parts = _flatten_strings(raw)
    refs = _verse_refs(ref, len(parts))
    verses = [
        {"ref": refs[i] if i < len(refs) else f"Verse {i + 1}", "number": i + 1, "text": text}
        for i, text in enumerate(parts)
    ]
    return {"text": " ".join(parts), "verses": verses}


def _sanitize_cached(cached: dict) -> dict:
    """Make even an older/offline cache readable after an upgrade."""
    out = dict(cached)
    out["hebrew_text"] = _clean_hebrew_fragment(out.get("hebrew_text", ""))
    if out.get("hebrew_verses"):
        out["hebrew_verses"] = [
            {**v, "text": _clean_hebrew_fragment(v.get("text", ""))}
            for v in out["hebrew_verses"] if isinstance(v, dict)
        ]
    out["cache_schema"] = CACHE_SCHEMA
    return out


def weekly_parashah(on_date: date | None = None) -> dict:
    today = on_date or datetime.now().astimezone().date()
    shabbat = _next_saturday(today)
    cached = _load_cache()
    if (
        cached
        and cached.get("cache_schema") == CACHE_SCHEMA
        and cached.get("date") == shabbat.isoformat()
        and cached.get("title")
    ):
        return _sanitize_cached(cached)

    params = {
        "v": "1", "cfg": "json", "start": shabbat.isoformat(), "end": shabbat.isoformat(),
        "s": "on", "maj": "on", "min": "on", "mod": "on", "nx": "on", "ss": "on",
        "M": "on", "lg": "s", "geo": "none"
    }
    try:
        r = httpx.get(HEBCAL, params=params, timeout=12.0, follow_redirects=True)
        r.raise_for_status()
        items = r.json().get("items", [])
        event = next((x for x in items if x.get("category") == "parashat"), None)
        if not event:
            event = next((x for x in items if x.get("leyning") and x.get("date") == shabbat.isoformat()), None)
        if not event:
            raise RuntimeError("No Torah reading returned for this Shabbat.")
        ref = _extract_ref(event)
        hebrew_text = ""
        hebrew_verses: list[dict] = []
        text_error = ""
        try:
            fetched = _fetch_hebrew_text(ref)
            hebrew_text = fetched["text"]
            hebrew_verses = fetched["verses"]
        except Exception as exc:
            text_error = str(exc)
        data = {
            "cache_schema": CACHE_SCHEMA,
            "date": shabbat.isoformat(),
            "title": event.get("title", "Weekly Torah Reading"),
            "hebrew": _clean_hebrew_fragment(event.get("hebrew", "")),
            "category": event.get("category", ""),
            "torah_ref": ref,
            "haftarah": (event.get("leyning") or {}).get("haftarah", ""),
            "aliyot": event.get("leyning") or {},
            "hebrew_text": hebrew_text,
            "hebrew_verses": hebrew_verses,
            "text_error": text_error,
            "source": "Hebcal calendar metadata; Hebrew text fetched from Sefaria when available.",
            "fetched_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        }
        _save_cache(data)
        return data
    except Exception as exc:
        if cached:
            cached = _sanitize_cached(cached)
            cached["stale"] = True
            cached["warning"] = f"Using cached weekly reading: {exc}"
            return cached
        return {
            "cache_schema": CACHE_SCHEMA,
            "date": shabbat.isoformat(), "title": "Weekly Torah Reading", "hebrew": "",
            "torah_ref": "", "haftarah": "", "aliyot": {}, "hebrew_text": "", "hebrew_verses": [],
            "warning": f"Could not retrieve weekly reading: {exc}", "offline": True,
        }
