from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote

import httpx

BASE = "https://www.sefaria.org"
CACHE_DIR = Path.home() / ".local" / "share" / "quarries" / "sefaria-cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)


class SefariaError(RuntimeError):
    pass


def _safe_name(value: str) -> str:
    value = re.sub(r"[^A-Za-z0-9._-]+", "-", (value or "sefaria").strip()).strip("-")
    return value[:120] or "sefaria"


@dataclass
class SefariaClient:
    timeout: float = 20.0

    def _get(self, path: str, params: dict | None = None) -> dict | list:
        url = BASE + path
        try:
            r = httpx.get(
                url,
                params=params,
                timeout=max(self.timeout, 30.0),
                follow_redirects=True,
                headers={"User-Agent": "Quarries/0.10.7"},
            )
            r.raise_for_status()
            return r.json()
        except Exception as exc:
            raise SefariaError(f"Sefaria request failed: {exc}") from exc


    @staticmethod
    def _sheet_id(tref: str) -> int | None:
        """Return the numeric ID for a reference such as 'Sheet 404263'."""
        match = re.fullmatch(
            r"\s*Sheet\s+(\d+)\s*",
            tref or "",
            re.I,
        )
        return int(match.group(1)) if match else None

    def sheet(self, sheet_id: int) -> dict:
        """Fetch a Sefaria source sheet and reject unavailable/private sheets."""
        payload = self._get(f"/api/sheets/{sheet_id}")

        if not isinstance(payload, dict):
            raise SefariaError(
                f"Sefaria returned an invalid response for Sheet {sheet_id}."
            )

        if payload.get("error"):
            raise SefariaError(
                f"Sheet {sheet_id}: {payload['error']}"
            )

        if not payload.get("sources"):
            raise SefariaError(
                f"Sheet {sheet_id} exists but contains no accessible sources."
            )

        payload["_quarries_type"] = "sheet"
        payload["_quarries_ref"] = f"Sheet {sheet_id}"

        return payload

    def text(self, tref: str) -> dict:
        tref = (tref or "").strip()
        if not tref:
            raise SefariaError("Sefaria reference is empty.")

        sheet_id = self._sheet_id(tref)
        if sheet_id is not None:
            return self.sheet(sheet_id)

        tref = (tref or "").strip()
        if not tref:
            raise SefariaError("A Sefaria reference is required.")
        # One call per language keeps response parsing predictable across text types.
        he = self._get(f"/api/v3/texts/{quote(tref, safe='')}", {"version": "hebrew"})
        en = self._get(f"/api/v3/texts/{quote(tref, safe='')}", {"version": "english"})
        return {"reference": tref, "hebrew": he, "english": en}

    def calendars(self, year: int | None = None, month: int | None = None, day: int | None = None, diaspora: int = 1) -> dict:
        params = {"diaspora": diaspora}
        if year and month and day:
            params.update({"year": year, "month": month, "day": day})
        return self._get("/api/calendars", params)

    def topic(self, slug: str) -> dict:
        slug = (slug or "").strip()
        if not slug:
            raise SefariaError("A topic slug is required.")
        return self._get(f"/api/v2/topics/{quote(slug, safe='')}", {"with_refs": 1, "with_links": 1, "group_related": 1})

    def topics(self, query: str, limit: int = 30) -> list[dict]:
        query = (query or "").strip().lower()
        if not query:
            return []
        cache = CACHE_DIR / "topics.json"
        data = None
        if cache.exists() and time.time() - cache.stat().st_mtime < 86400 * 7:
            try:
                data = json.loads(cache.read_text(encoding="utf-8"))
            except Exception:
                data = None
        if not isinstance(data, list):
            data = self._get("/api/topics", {"limit": 0, "minify": 1})
            if isinstance(data, list):
                try:
                    cache.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
                except Exception:
                    pass
        if not isinstance(data, list):
            return []
        out = []
        for t in data:
            hay = " ".join(str(t.get(k, "")) for k in ("slug", "primaryTitle", "description", "categoryDescription")).lower()
            titles = t.get("titles") or []
            hay += " " + " ".join(str(x.get("text", "")) for x in titles if isinstance(x, dict)).lower()
            if query in hay:
                out.append(t)
            if len(out) >= max(1, min(limit, 100)):
                break
        return out

    def related(self, tref: str) -> dict:
        return self._get(f"/api/related/{quote((tref or '').strip(), safe='')}")

    def manuscripts(self, tref: str) -> dict | list:
        return self._get(f"/api/manuscripts/{quote((tref or '').strip(), safe='')}")


def version_text(payload: dict, language: str) -> list[str]:
    """Flatten Texts v3 versions into segment strings without assuming a text depth."""
    data = payload.get(language) if isinstance(payload, dict) and language in payload else payload
    if not isinstance(data, dict):
        return []
    versions = data.get("versions") or []
    if not versions:
        return []
    text = versions[0].get("text")
    out: list[str] = []
    def walk(x):
        if isinstance(x, str):
            out.append(re.sub(r"<[^>]+>", " ", x).replace("&nbsp;", " ").strip())
        elif isinstance(x, list):
            for y in x: walk(y)
    walk(text)
    return [x for x in out if x]


def manuscript_image_urls(payload) -> list[str]:
    urls: list[str] = []
    def walk(x):
        if isinstance(x, dict):
            for k, v in x.items():
                lk = k.lower()
                if isinstance(v, str) and v.startswith(("http://", "https://")) and ("image" in lk or re.search(r"\.(?:jpg|jpeg|png|webp)(?:\?|$)", v, re.I)):
                    urls.append(v)
                else:
                    walk(v)
        elif isinstance(x, list):
            for y in x: walk(y)
    walk(payload)
    # stable de-duplication
    seen, out = set(), []
    for u in urls:
        if u not in seen:
            seen.add(u); out.append(u)
    return out



def _sheet_plain_text(value) -> str:
    """Normalize text and simple HTML from a Sefaria Sheet."""
    if value is None:
        return ""

    if isinstance(value, list):
        return " ".join(
            part
            for part in (_sheet_plain_text(item) for item in value)
            if part
        )

    text = str(value)

    text = re.sub(
        r"<br\s*/?>",
        "\n",
        text,
        flags=re.I,
    )

    text = re.sub(r"<[^>]+>", "", text)

    replacements = {
        "&nbsp;": " ",
        "&amp;": "&",
        "&quot;": '"',
        "&#39;": "'",
        "&lt;": "<",
        "&gt;": ">",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    text = re.sub(r"[ \t]+", " ", text)

    return text.strip()


def sheet_segments(payload: dict) -> list[dict]:
    """
    Flatten a Sefaria Sheet into the Hebrew/English segment structure
    expected by the Quarries reader.
    """
    segments = []

    def walk(sources):
        for source in sources or []:

            if not isinstance(source, dict):
                continue

            hebrew = ""
            english = ""

            value = source.get("text")

            if isinstance(value, dict):
                hebrew = _sheet_plain_text(
                    value.get("he")
                )
                english = _sheet_plain_text(
                    value.get("en")
                )

            elif value:
                english = _sheet_plain_text(value)

            outside_bi = source.get("outsideBiText")

            if isinstance(outside_bi, dict):
                hebrew = (
                    hebrew
                    or _sheet_plain_text(
                        outside_bi.get("he")
                    )
                )

                english = (
                    english
                    or _sheet_plain_text(
                        outside_bi.get("en")
                    )
                )

            outside = source.get("outsideText")

            if outside:
                english = (
                    english
                    or _sheet_plain_text(outside)
                )

            reference = _sheet_plain_text(
                source.get("ref")
            )

            if hebrew or english or reference:

                segments.append({
                    "index": len(segments) + 1,
                    "reference": reference,
                    "hebrew": hebrew,
                    "english": english,
                })

            walk(source.get("subsources"))

    walk(payload.get("sources"))

    return segments
