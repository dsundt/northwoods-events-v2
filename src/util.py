from __future__ import annotations

import re
import unicodedata
from datetime import date, datetime, time, timezone, timedelta
from urllib.parse import urljoin, urlparse, urlunparse, parse_qsl, urlencode
from typing import Any, Dict, List, Optional, Tuple

from bs4 import BeautifulSoup
from dateutil import parser as dtp

def absurl(base: str, href: str) -> str:
    return urljoin(base, href)


def _normalize_ascii(value: str) -> str:
    """Best-effort ASCII normalization for slug components."""
    normalized = unicodedata.normalize("NFKD", value)
    return normalized.encode("ascii", "ignore").decode("ascii")


def slugify(text: str, fallback: str = "item") -> str:
    """Convert arbitrary text into a filesystem- and URL-friendly slug."""
    text = _normalize_ascii((text or "").strip().lower())
    # Replace non-word characters with a hyphen
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    text = text.strip("-")
    fallback = _normalize_ascii((fallback or "item").strip().lower() or "item")
    fallback = re.sub(r"[^\w-]", "", fallback)
    fallback = fallback or "item"
    return text or fallback


def json_default(value: Any) -> str:
    """Serialize datetime-like objects for JSON dumps."""
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.isoformat()
    if isinstance(value, (date, time)):
        return value.isoformat()
    return str(value)

def parse_first_jsonld_event(soup: BeautifulSoup, base_url: str) -> Optional[Dict[str, Any]]:
    """Return a dict with normalized fields from the first JSON-LD Event in the page."""
    for tag in soup.find_all("script", type="application/ld+json"):
        try:
            import json
            data = json.loads(tag.string or "")
        except Exception:
            continue
        # Could be a list or a single object
        candidates = data if isinstance(data, list) else [data]
        for obj in candidates:
            if not isinstance(obj, dict): 
                continue
            # Event or has @type list including Event
            atype = obj.get("@type")
            types = [atype] if isinstance(atype, str) else (atype or [])
            if ("Event" in types) or (atype == "Event"):
                name = (obj.get("name") or "").strip()
                url = obj.get("url") or ""
                start = obj.get("startDate")
                end = obj.get("endDate")
                loc = obj.get("location")
                location_text = None
                if isinstance(loc, dict):
                    location_text = loc.get("name") or loc.get("address") or None
                elif isinstance(loc, str):
                    location_text = loc
                # Normalize dates to ISO if parseable
                start_iso = dtp.parse(start).isoformat() if start else None
                end_iso = dtp.parse(end).isoformat() if end else None
                return {
                    "title": name,
                    "url": absurl(base_url, url),
                    "start_utc": start_iso,
                    "end_utc": end_iso,
                    "location": location_text,
                }
    return None

def sanitize_event(ev: dict, source_name: str, calendar_name: str) -> Optional[dict]:
    """Ensure required fields exist; add ids; skip invalids."""
    title = (ev.get("title") or "").strip()
    url = ev.get("url") or ""
    start = ev.get("start_utc")
    if not title or not start:
        return None
    uid_base = f"{title}|{start}|{source_name}"
    import hashlib
    uid = hashlib.sha1(uid_base.encode("utf-8")).hexdigest() + "@northwoods-v2"
    return {
        "uid": uid,
        "title": title,
        "start_utc": start,
        "end_utc": ev.get("end_utc"),
        "url": url,
        "location": ev.get("location"),
        "source": source_name,
        "calendar": calendar_name,
    }


def _ensure_query_param(items: List[Tuple[str, str]], key: str, value: str) -> List[Tuple[str, str]]:
    lowered = key.lower()
    new_items = list(items)
    for idx, (existing_key, _) in enumerate(new_items):
        if existing_key.lower() == lowered:
            new_items[idx] = (existing_key, value)
            return new_items
    new_items.append((key, value))
    return new_items


def expand_tec_ics_urls(
    base_url: str,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
) -> List[str]:
    """Return a list of TEC ICS URLs augmented with common range/display params."""

    if not base_url:
        return []

    now = datetime.now(timezone.utc)
    if start_date is None:
        start_date = now - timedelta(days=1)
    if end_date is None:
        end_date = now + timedelta(days=180)

    placeholders = {
        "start_date": start_date.strftime("%Y-%m-%d"),
        "end_date": end_date.strftime("%Y-%m-%d"),
        "start_iso": start_date.isoformat(),
        "end_iso": end_date.isoformat(),
    }

    def _format(url: str) -> str:
        if "{" in url and "}" in url:
            try:
                return url.format(**placeholders)
            except Exception:
                return url
        return url

    formatted = _format(base_url)
    parsed = urlparse(formatted)

    base_query = parse_qsl(parsed.query, keep_blank_values=True)
    base_query = _ensure_query_param(base_query, "ical", "1")

    combos: List[List[Tuple[str, str]]] = []
    combo_keys: set[Tuple[Tuple[str, str], ...]] = set()

    def _add_combo(pairs: List[Tuple[str, str]]):
        combo = list(base_query)
        for key, value in pairs:
            if value is None:
                continue
            combo = _ensure_query_param(combo, key, value)
        key = tuple((k.lower(), v) for k, v in combo)
        if key not in combo_keys:
            combo_keys.add(key)
            combos.append(combo)

    common_pairs = [
        [],
        [("tribe_display", "list")],
        [("tribe_display", "list"), ("tribe-bar-date", placeholders["start_date"])],
        [("tribe_display", "list"), ("tribe-bar-date", placeholders["start_date"]), ("tribe_paged", "1")],
        [("eventDisplay", "list")],
        [("eventDisplay", "list"), ("eventDate", placeholders["start_date"])],
        [("eventDisplay", "month"), ("eventDate", placeholders["start_date"])],
        [("start_date", placeholders["start_date"]), ("end_date", placeholders["end_date"])],
        [("startDate", placeholders["start_date"]), ("endDate", placeholders["end_date"])],
    ]

    for pairs in common_pairs:
        _add_combo(pairs)

    path_candidates: List[str] = []

    def _add_path(candidate: str):
        if not candidate:
            candidate = "/"
        if not candidate.startswith("/"):
            candidate = f"/{candidate}"
        normalized = re.sub(r"/{2,}", "/", candidate)
        if normalized not in path_candidates:
            path_candidates.append(normalized)

    original_path = parsed.path or "/"
    trimmed = (parsed.path or "").rstrip("/")

    _add_path(original_path or "/")
    if trimmed and trimmed != original_path:
        _add_path(trimmed)

    base_root = trimmed or ""
    if not base_root:
        base_root = "/events"
    elif base_root.endswith("/events") or base_root.endswith("/event"):
        pass
    else:
        base_root = f"{base_root}/events"

    _add_path(base_root)
    _add_path(f"{base_root}/list")

    # Common TEC rewrites
    _add_path("/events")
    _add_path("/events/list")
    _add_path("/index.php/events")
    _add_path("/index.php/events/list")

    seen: set[str] = set()
    urls: List[str] = []

    def _push(url: str):
        if not url or url in seen:
            return
        seen.add(url)
        urls.append(url)

    if "ical=" in parsed.query.lower():
        _push(formatted)

    for path in path_candidates:
        for items in combos:
            query = urlencode(items, doseq=True)
            candidate = urlunparse(parsed._replace(path=path, query=query))
            candidate = _format(candidate)
            if "ical=" not in candidate.lower():
                continue
            _push(candidate)

    return urls
