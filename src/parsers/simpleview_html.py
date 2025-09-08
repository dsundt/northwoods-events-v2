# src/parsers/simpleview_html.py
from __future__ import annotations

import re
from datetime import datetime
from html import unescape
from typing import List, Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET

_UA = {
    "User-Agent": "Mozilla/5.0 (compatible; northwoods-events/2.0; +https://github.com/dsundt/northwoods-events-v2)"
}

# We will drop items that look “recurring” if no concrete date is extractable.
_RECURRING_HINTS = re.compile(r"\b(recurring|every\s+\w+|weekly|daily)\b", re.I)

_DATE_RE_RANGE = re.compile(
    r"([A-Za-z]{3,9}\s+\d{1,2},\s*\d{4})\s*[-–]\s*([A-Za-z]{3,9}\s+\d{1,2},\s*\d{4})"
)
_DATE_RE_SINGLE = re.compile(r"([A-Za-z]{3,9}\s+\d{1,2},\s*\d{4})")
_DATE_ISO = re.compile(r"(\d{4}-\d{2}-\d{2})")

def _clean(s: Optional[str]) -> Optional[str]:
    if not s:
        return None
    s = unescape(s)
    s = re.sub(r"<[^>]+>", " ", s)  # strip tags if present
    s = re.sub(r"\s+", " ", s).strip()
    return s or None

def _to_std_date(s: str) -> Optional[str]:
    for fmt in ("%B %d, %Y", "%b %d, %Y", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(s, fmt)
            return dt.strftime("%Y-%m-%d 00:00:00")
        except Exception:
            pass
    return None

def _extract_dates(txt: str) -> (Optional[str], Optional[str]):
    txt = " ".join(txt.split())
    m = _DATE_RE_RANGE.search(txt)
    if m:
        s = _to_std_date(m.group(1))
        e = _to_std_date(m.group(2))
        return s, e
    m = _DATE_RE_SINGLE.search(txt)
    if m:
        s = _to_std_date(m.group(1))
        return s, None
    m = _DATE_ISO.search(txt)
    if m:
        s = _to_std_date(m.group(1))
        return s, None
    return None, None

def _extract_location(txt: str) -> Optional[str]:
    m = re.search(r"\bLocation\s*:?\s*(.+?)\s*(?:\||$)", txt, flags=re.I)
    if m:
        return re.sub(r"^\s*Location\s*:?\s*", "", m.group(1), flags=re.I).strip()
    # Try a “ at Venue ” pattern
    m = re.search(r"\bat\s+([A-Z][\w &'\-\.]+)", txt)
    return m.group(1).strip() if m else None

def _fetch_detail_for_dates(url: str, sess: requests.Session, timeout: int = 20) -> (Optional[str], Optional[str], Optional[str]):
    """When RSS description has no dates, pull the detail page and parse JSON-LD."""
    try:
        r = sess.get(url, timeout=timeout)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        # JSON-LD
        for tag in soup.find_all("script", attrs={"type": "application/ld+json"}):
            try:
                import json
                data = json.loads(tag.string or tag.text or "{}")
            except Exception:
                continue
            items = data if isinstance(data, list) else [data]
            for obj in items:
                if isinstance(obj, dict) and obj.get("@type") in ("Event", ["Event"]):
                    start = obj.get("startDate")
                    end = obj.get("endDate")
                    loc = None
                    loc_obj = obj.get("location")
                    if isinstance(loc_obj, dict):
                        loc = loc_obj.get("name") or loc_obj.get("address")
                    def norm(x):
                        if not x or not isinstance(x, str):
                            return None
                        x = x.strip()
                        x = re.sub(r"Z$", "+0000", x)  # minimal TZ normalize
                        # Try the common formats
                        for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
                            try:
                                dt = datetime.strptime(x, fmt)
                                if "%H" in fmt:
                                    return dt.strftime("%Y-%m-%d %H:%M:%S")
                                else:
                                    return dt.strftime("%Y-%m-%d 00:00:00")
                            except Exception:
                                pass
                        return None
                    return norm(start), norm(end), _clean(loc)
        # Otherwise, scrape text
        text = _clean(soup.get_text(" ")) or ""
        s, e = _extract_dates(text)
        return s, e, _extract_location(text)
    except Exception:
        return None, None, None

def fetch_simpleview_html(url: str, timeout: int = 20, max_items: int = 200) -> List[dict]:
    """
    Minocqua RSS:
      - Keep only items with a **concrete** date.
      - If description doesn't include a date, try the detail page once.
      - If still undated OR clearly recurring, **skip** (per your instruction).
    """
    sess = requests.Session()
    sess.headers.update(_UA)

    r = sess.get(url, timeout=timeout)
    r.raise_for_status()

    # Parse RSS with stdlib XML (no feedparser dependency)
    try:
        root = ET.fromstring(r.text)
    except Exception:
        # Some feeds return HTML if blocked; fallback: no events
        return []

    ns = {}
    channel = root.find("channel") or root
    items = channel.findall("item")
    events: List[dict] = []

    for it in items[:max_items]:
        title = _clean((it.findtext("title") or ""))
        link = (it.findtext("link") or "").strip()
        desc = _clean(it.findtext("description") or "")

        # First pass: pull dates from description
        start, end = _extract_dates(desc or "")

        # If looks recurring and no concrete date -> skip
        if not start and desc and _RECURRING_HINTS.search(desc):
            continue

        # Try detail page once if still no date
        location = _extract_location(desc or "") or None
        if not start and link:
            s2, e2, loc2 = _fetch_detail_for_dates(link, sess, timeout=timeout)
            start = start or s2
            end = end or e2
            location = location or loc2

        # Still no start? skip
        if not start:
            continue

        uid = f"sv-{abs(hash((link or title or '', start or '')))}"
        events.append({
            "uid": uid,
            "title": title or "(untitled event)",
            "start_utc": start,
            "end_utc": end,
            "url": link or url,
            "location": location,
        })

    return events
