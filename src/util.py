from __future__ import annotations

import re
import unicodedata
from datetime import date, datetime, time, timezone
from urllib.parse import urljoin
from typing import Any, Dict, List, Optional

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
