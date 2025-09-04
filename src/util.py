from __future__ import annotations
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from dateutil import parser as dtp
from typing import Optional, List, Dict, Any

def absurl(base: str, href: str) -> str:
    return urljoin(base, href)

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
