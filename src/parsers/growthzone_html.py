# src/parsers/growthzone_html.py
"""
GrowthZone (ChamberMaster) HTML parser
- Robustly extracts event rows from the list page
- Hydrates each event with start/end and location by visiting the detail page
  (JSON-LD first; falls back to "When/Where" text blocks)
- Signature is tolerant to existing call patterns:
    fetch_growthzone_html(url, start_date=None, end_date=None, session=None, **_)
Returns: list[dict] with keys: title, url, start, end, location
"""

from __future__ import annotations
from typing import List, Dict, Optional, Any
import re
import json
from datetime import datetime
from dateutil import parser as dtparse
from dateutil.tz import gettz

import requests
from bs4 import BeautifulSoup

TZ = gettz("America/Chicago")
UA = {"User-Agent": "northwoods-events-v2/2.0 (+GitHub Actions)"}

def _clean_text(s: Optional[str]) -> Optional[str]:
    if not s:
        return None
    s = re.sub(r"\s+", " ", s).strip()
    return s or None

def _abs_url(base: str, href: str) -> str:
    if href.startswith("http://") or href.startswith("https://"):
        return href
    # GrowthZone typically uses absolute paths like /events/details/...
    return re.sub(r"/+$", "", base) + ("" if href.startswith("/") else "/") + href.lstrip("/")

def _parse_when_text(text: str) -> (Optional[datetime], Optional[datetime]):
    """
    Try to coerce the 'When:' line into start/end datetimes.
    Accepts many formats, assumes America/Chicago when tz missing.
    """
    if not text:
        return None, None
    # Common patterns like:
    # "Saturday Sep 6, 2025 10:00 AM - 4:00 PM"
    # "Sep 6, 2025 10:00 AM - Sep 6, 2025 4:00 PM"
    # "Sep 6, 2025"
    # We'll split on ' - ' and parse left/right.
    parts = [p.strip() for p in re.split(r"\s+-\s+", text)]
    try:
        if len(parts) == 2:
            left = dtparse.parse(parts[0], tzinfos={"CST": TZ, "CDT": TZ})
            right = dtparse.parse(parts[1], tzinfos={"CST": TZ, "CDT": TZ})
            # If right has no date, borrow date from left
            if right and (right.date() != right.date() or right.year == 1900):
                right = datetime.combine(left.date(), right.time()).replace(tzinfo=left.tzinfo or TZ)
            if not left.tzinfo:
                left = left.replace(tzinfo=TZ)
            if not right.tzinfo:
                right = right.replace(tzinfo=TZ)
            return left, right
        elif len(parts) == 1:
            d = dtparse.parse(parts[0], tzinfos={"CST": TZ, "CDT": TZ})
            if not d.tzinfo:
                d = d.replace(tzinfo=TZ)
            # No explicit end — assume 1h
            return d, d.replace(hour=d.hour + 1) if d else (d, None)
    except Exception:
        return None, None
    return None, None

def _parse_jsonld_event(soup: BeautifulSoup) -> Dict[str, Any]:
    payload = {}
    for tag in soup.find_all("script", attrs={"type": "application/ld+json"}):
        try:
            data = json.loads(tag.string or tag.text or "{}")
        except Exception:
            continue
        # Could be a list or a dict
        candidates = data if isinstance(data, list) else [data]
        for node in candidates:
            if isinstance(node, dict) and node.get("@type", "").lower().endswith("event"):
                payload = node
                break
        if payload:
            break
    return payload

def _get_when_where_from_detail(url: str, session: Optional[requests.Session] = None) -> (Optional[datetime], Optional[datetime], Optional[str]):
    sess = session or requests.Session()
    r = sess.get(url, headers=UA, timeout=30)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")

    # 1) JSON-LD first (most reliable)
    data = _parse_jsonld_event(soup)
    if data:
        start = data.get("startDate") or data.get("startTime")
        end = data.get("endDate") or data.get("endTime")
        loc = None
        location = data.get("location")
        if isinstance(location, dict):
            loc = location.get("name") or location.get("address") or None
            # If address is a dict
            addr = location.get("address")
            if isinstance(addr, dict):
                parts = [addr.get(k) for k in ("streetAddress", "addressLocality", "addressRegion")]
                loc = _clean_text(", ".join([p for p in parts if p]) or loc)
        elif isinstance(location, str):
            loc = location
        try:
            start_dt = dtparse.parse(start) if start else None
            end_dt = dtparse.parse(end) if end else None
            if start_dt and not start_dt.tzinfo:
                start_dt = start_dt.replace(tzinfo=TZ)
            if end_dt and not end_dt.tzinfo:
                end_dt = end_dt.replace(tzinfo=TZ)
            return start_dt, end_dt, _clean_text(loc)
        except Exception:
            pass

    # 2) Fallback: text blocks like "When:" / "Where:"
    # GrowthZone usually renders details with these labels somewhere in the detail page.
    text = soup.get_text(" ", strip=True)
    when_match = re.search(r"\bWhen:\s*(.+?)(?:\s{2,}|\bWhere:\b|$)", text, flags=re.I)
    where_match = re.search(r"\bWhere:\s*(.+?)(?:\s{2,}|\bContact\s|$)", text, flags=re.I)
    when_txt = when_match.group(1).strip() if when_match else ""
    where_txt = where_match.group(1).strip() if where_match else None

    start_dt, end_dt = _parse_when_text(when_txt)
    return start_dt, end_dt, _clean_text(where_txt)

def fetch_growthzone_html(url: str,
                          start_date: Optional[str] = None,
                          end_date: Optional[str] = None,
                          session: Optional[requests.Session] = None,
                          **kwargs) -> List[Dict[str, Any]]:
    """
    Tolerant signature — accepts extra positional/keyword args used by main.py.
    Only the first list page is parsed (GrowthZone paginates; detail hydration happens per event).
    """
    sess = session or requests.Session()
    resp = sess.get(url, headers=UA, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    events: List[Dict[str, Any]] = []
    seen = set()

    # 1) Try GrowthZone card/list anchors that lead to details pages
    #    Detail URLs look like: /events/details/<slug>-<id>
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if re.search(r"/events/details/[^/]+-\d+/?$", href):
            ev_url = _abs_url(url, href)
            title = _clean_text(a.get_text() or a.get("title"))
            if not title:
                # look up to a parent with heading
                h = a.find_parent().find(["h2", "h3"]) if a.find_parent() else None
                if h:
                    title = _clean_text(h.get_text())
            key = (title or "", ev_url)
            if key in seen:
                continue
            seen.add(key)

            # Hydrate date/location from detail page
            start_dt, end_dt, loc = _get_when_where_from_detail(ev_url, session=sess)
            events.append({
                "title": title or "Untitled Event",
                "url": ev_url,
                "start": start_dt.isoformat() if start_dt else None,
                "end": end_dt.isoformat() if end_dt else None,
                "location": loc,
            })

    # 2) If nothing found (rare), try list date+title blocks
    if not events:
        # Heuristic: lines with a date next to a link (from your logs)
        text_blocks = soup.find_all(text=re.compile(r"\b(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)\b|\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)\b", re.I))
        for node in text_blocks:
            a = node.find_next("a") if hasattr(node, "find_next") else None
            if a and a.has_attr("href") and re.search(r"/events/details/[^/]+-\d+/?$", a["href"]):
                title = _clean_text(a.get_text()) or "Untitled Event"
                ev_url = _abs_url(url, a["href"])
                # parse date from the text we matched
                when_line = _clean_text(str(node))
                start_dt, end_dt = _parse_when_text(when_line)
                events.append({
                    "title": title,
                    "url": ev_url,
                    "start": start_dt.isoformat() if start_dt else None,
                    "end": end_dt.isoformat() if end_dt else None,
                    "location": None,
                })

    return events
