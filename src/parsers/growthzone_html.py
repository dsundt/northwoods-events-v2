# src/parsers/growthzone_html.py
from __future__ import annotations

import json
import re
from datetime import datetime
from html import unescape
from typing import List, Optional
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

_UA = {
    "User-Agent": "Mozilla/5.0 (compatible; northwoods-events/2.0; +https://github.com/dsundt/northwoods-events-v2)"
}

# ------------ helpers

def _clean_text(s: Optional[str]) -> Optional[str]:
    if not s:
        return None
    s = unescape(s)
    s = re.sub(r"\s+", " ", s).strip()
    return s or None

def _strip_location_label(s: Optional[str]) -> Optional[str]:
    if not s:
        return None
    return re.sub(r"^\s*(Location|Where)\s*:?\s*", "", s, flags=re.I).strip() or None

_DATE_PATTERNS = [
    # ISO-ish
    "%Y-%m-%dT%H:%M:%S%z",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%d",
    # Common US formats GrowthZone uses
    "%b %d, %Y %I:%M %p",
    "%B %d, %Y %I:%M %p",
    "%b %d, %Y",
    "%B %d, %Y",
    "%m/%d/%Y %I:%M %p",
    "%m/%d/%Y",
]

def _try_parse_dt(s: str) -> Optional[str]:
    s = s.strip()
    # normalize timezone "Z" -> +0000 for strptime
    s = re.sub(r"Z$", "+0000", s)
    for fmt in _DATE_PATTERNS:
        try:
            dt = datetime.strptime(s, fmt)
            # normalize to "YYYY-MM-DD HH:MM:SS"
            if "%H" in fmt or "%I" in fmt:
                return dt.strftime("%Y-%m-%d %H:%M:%S")
            else:
                return dt.strftime("%Y-%m-%d 00:00:00")
        except Exception:
            continue
    return None

def _first_jsonld_event(soup: BeautifulSoup) -> Optional[dict]:
    for tag in soup.find_all("script", attrs={"type": "application/ld+json"}):
        try:
            data = json.loads(tag.string or tag.text or "{}")
        except Exception:
            continue
        items = data if isinstance(data, list) else [data]
        for obj in items:
            if not isinstance(obj, dict):
                continue
            t = obj.get("@type")
            types = [t] if isinstance(t, str) else (t or [])
            if any(str(x).lower() == "event" for x in types):
                return obj
    return None

def _event_from_jsonld(obj: dict) -> dict:
    title = _clean_text(obj.get("name"))
    start = obj.get("startDate")
    end = obj.get("endDate")
    loc = None
    loc_obj = obj.get("location")
    if isinstance(loc_obj, dict):
        loc = _clean_text(loc_obj.get("name")) or _clean_text(loc_obj.get("address"))
    elif isinstance(loc_obj, list) and loc_obj:
        l0 = loc_obj[0]
        if isinstance(l0, dict):
            loc = _clean_text(l0.get("name")) or _clean_text(l0.get("address"))
    return {
        "title": title,
        "start_utc": _try_parse_dt(start) if isinstance(start, str) else None,
        "end_utc": _try_parse_dt(end) if isinstance(end, str) else None,
        "location": _strip_location_label(loc),
    }

def _extract_fallback_date(text: str) -> Optional[str]:
    """
    Pull something like:
      'Wednesday, September 17, 2025 5:30 PM - 7:30 PM'
      'September 17, 2025'
      '09/17/2025'
    """
    text = " ".join(text.split())
    # Range with a start date at the front — we only need the first date/time
    m = re.search(r"([A-Za-z]{3,9}\s+\d{1,2},\s*\d{4}(?:\s+\d{1,2}:\d{2}\s*(AM|PM))?)", text, flags=re.I)
    if m:
        return _try_parse_dt(m.group(1))

    m = re.search(r"(\d{1,2}/\d{1,2}/\d{4}(?:\s+\d{1,2}:\d{2}\s*(AM|PM))?)", text, flags=re.I)
    if m:
        return _try_parse_dt(m.group(1))

    m = re.search(r"(\d{4}-\d{2}-\d{2}(?:T\d{2}:\d{2}:\d{2}Z?)?)", text)
    if m:
        return _try_parse_dt(m.group(1))
    return None

def _extract_fallback_location(soup: BeautifulSoup, full_text: str) -> Optional[str]:
    # Try common label/value pattern
    # e.g. <div>Location</div><div>Some Venue</div>
    labels = soup.find_all(text=re.compile(r"^\s*(Location|Where)\s*:?\s*$", re.I))
    for lab in labels:
        par = getattr(lab, "parent", None)
        if par and par.next_sibling:
            cand = _clean_text(getattr(par.next_sibling, "get_text", lambda: "")())
            cand = _strip_location_label(cand)
            if cand:
                return cand
    # Regex from page text
    m = re.search(r"(?:Location|Where)\s*:?\s*(.+)", full_text, flags=re.I)
    if m:
        return _strip_location_label(_clean_text(m.group(1)))
    return None

# ------------ main fetcher

def fetch_growthzone_html(url: str, max_events: int = 120, timeout: int = 20) -> List[dict]:
    """
    Rhinelander: ensure dates + clean location label
    Works against GrowthZone/ChamberMaster sites by crawling the calendar, then the detail pages.
    """
    sess = requests.Session()
    sess.headers.update(_UA)

    resp = sess.get(url, timeout=timeout)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    # Find event detail links
    links = set()
    for a in soup.select("a[href]"):
        href = a.get("href") or ""
        if "/events/details/" in href:
            links.add(urljoin(resp.url, href))
    # Some calendars list multiple months: follow next/prev? Keep it simple; first batch only.
    detail_urls = list(links)[:max_events]

    results: List[dict] = []

    for durl in detail_urls:
        try:
            dresp = sess.get(durl, timeout=timeout)
            dresp.raise_for_status()
            dhtml = dresp.text
            ddoc = BeautifulSoup(dhtml, "html.parser")

            # Prefer JSON-LD
            ev = _first_jsonld_event(ddoc)
            title = None
            start = None
            end = None
            loc = None
            if ev:
                data = _event_from_jsonld(ev)
                title = data["title"]
                start = data["start_utc"]
                end = data["end_utc"]
                loc = data["location"]

            # Fallbacks
            text = _clean_text(ddoc.get_text(" ")) or ""
            if not title:
                h1 = ddoc.find("h1")
                title = _clean_text(h1.get_text()) if h1 else None

            if not start:
                start = _extract_fallback_date(text)

            if not loc:
                loc = _extract_fallback_location(ddoc, text)

            # If we STILL have no start date, we skip (prevents null dates).
            if not start:
                continue

            uid = f"gz-{abs(hash((durl, title or '')))}"

            results.append({
                "uid": uid,
                "title": title or "(untitled event)",
                "start_utc": start,
                "end_utc": end,
                "url": durl,
                "location": _strip_location_label(loc),
            })
        except Exception:
            # Skip single-bad pages; continue
            continue

    return results
