# src/parsers/simpleview_html.py
# DROP-IN REPLACEMENT
#
# Purpose:
# - Parse Simpleview event listings by discovering an ICS feed on the page
#   (patterns like '?format=ical' or '.ics') and parsing that. This is more
#   reliable than scraping headings and fixes "0 events" or "headings only".
# - Function signature matches main.py expectations: (source, start_date, end_date)
# - Returns: (events: list[dict], diag: dict)
#
# Notes:
# - This file only changes Simpleview parsing. TEC sources (Boulder/Eagle/Vilas) are untouched.
# - Fixes the previous SyntaxError by avoiding a complex f-string in UID generation.

from __future__ import annotations

import re
from datetime import datetime, date, time, timezone
from typing import Tuple, List, Dict, Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from dateutil import tz
import requests
from icalendar import Calendar

LOCAL_TZ = tz.gettz("America/Chicago")
UTC = tz.UTC

def _get(url: str, timeout: int = 20) -> requests.Response:
    if not isinstance(url, str):
        raise TypeError(f"_get expected a URL string, got {type(url)}")
    resp = requests.get(url, timeout=timeout, headers={"User-Agent": "northwoods-v2/1.0"})
    resp.raise_for_status()
    return resp

def _coerce_date(d) -> date:
    if isinstance(d, date) and not isinstance(d, datetime):
        return d
    if isinstance(d, datetime):
        return d.date()
    return datetime.fromisoformat(str(d)).date()

def _to_utc(dtobj) -> datetime:
    if isinstance(dtobj, date) and not isinstance(dtobj, datetime):
        dtobj = datetime.combine(dtobj, time(0, 0))
    if dtobj.tzinfo is None:
        dtobj = dtobj.replace(tzinfo=LOCAL_TZ)
    return dtobj.astimezone(UTC)

def _in_window(start_utc: datetime, end_utc: Optional[datetime], start_date: date, end_date: date) -> bool:
    window_start = datetime.combine(start_date, time(0, 0, tzinfo=UTC))
    window_end = datetime.combine(end_date, time(23, 59, 59, tzinfo=UTC))
    s = start_utc
    e = end_utc or start_utc
    return not (e < window_start or s > window_end)

def _parse_ics_bytes(ics_bytes: bytes, start_date: date, end_date: date) -> List[Dict]:
    cal = Calendar.from_ical(ics_bytes)
    out: List[Dict] = []
    for comp in cal.walk():
        if comp.name != "VEVENT":
            continue

        summary = str(comp.get("summary", "")).strip()
        if not summary:
            continue

        dtstart = comp.get("dtstart")
        if not dtstart:
            continue
        start_utc = _to_utc(dtstart.dt)

        dtend = comp.get("dtend")
        end_utc = _to_utc(dtend.dt) if dtend else None

        if not _in_window(start_utc, end_utc, start_date, end_date):
            continue

        url = str(comp.get("url", "")).strip() or None
        location = str(comp.get("location", "")).strip() or None

        uid_val = comp.get("uid")
        if uid_val:
            uid = str(uid_val)
        else:
            # Avoid complex f-strings to keep parser happy on all runners
            base = f"{summary}|{start_utc.isoformat()}|{url or ''}"
            uid = "sv-" + str(abs(hash(base)))

        out.append({
            "id": uid,
            "title": summary,
            "start": start_utc,
            "end": end_utc,
            "url": url,
            "location": location,
            "tz": "UTC",
        })
    return out

# Simpleview ICS patterns frequently seen
_ICS_CANDIDATE_PATTERNS = [
    re.compile(r"[?&]format=ical", re.I),
    re.compile(r"\.ics(\b|$)", re.I),
    re.compile(r"/icalendar", re.I),
]

def _discover_ics_href(html: str, page_url: str) -> Optional[str]:
    soup = BeautifulSoup(html, "html.parser")

    # <link rel="alternate" type="text/calendar">
    for link in soup.find_all("link", attrs={"rel": True, "type": True, "href": True}):
        rels = [r.lower() for r in (link.get("rel") or [])]
        typ = (link.get("type") or "").lower()
        href = link.get("href")
        if "alternate" in rels and typ in ("text/calendar", "text/x-vcalendar") and href:
            return urljoin(page_url, href)

    # Anchor candidates with common ICS patterns
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if any(p.search(href) for p in _ICS_CANDIDATE_PATTERNS):
            return urljoin(page_url, href)

    # Buttons or elements with data-href to ICS
    for btn in soup.select("[data-href]"):
        href = btn.get("data-href")
        if href and any(p.search(href) for p in _ICS_CANDIDATE_PATTERNS):
            return urljoin(page_url, href)

    return None

def fetch_simpleview_html(source: Dict, start_date, end_date) -> Tuple[List[Dict], Dict]:
    """
    :param source: dict with keys: name, id, type, url
    :param start_date: date or ISO string
    :param end_date: date or ISO string
    :return: (events, diag)
    """
    page_url = str(source.get("url", "")).strip()
    if not page_url:
        return [], {"ok": False, "error": "Missing source.url", "diag": {}}

    sd = _coerce_date(start_date)
    ed = _coerce_date(end_date)

    diag: Dict = {"ok": True, "error": "", "diag": {"page_url": page_url}}

    # 1) page load
    try:
        page = _get(page_url)
    except Exception as e:
        return [], {"ok": False, "error": f"GET listing failed: {e}", "diag": {"page_url": page_url}}

    # 2) discover ICS
    ics_href = _discover_ics_href(page.text, page_url)
    diag["diag"]["ics_url"] = ics_href

    if not ics_href:
        # Without ICS, Simpleview DOM scraping is not stable across templates.
        return [], {"ok": False, "error": "No ICS link discovered on Simpleview page", "diag": diag["diag"]}

    # 3) fetch & parse ICS
    try:
        ics_resp = _get(ics_href)
        events = _parse_ics_bytes(ics_resp.content, sd, ed)
        diag["diag"]["ics_events"] = len(events)
        return events, diag
    except Exception as e:
        return [], {"ok": False, "error": f"ICS fetch/parse failed: {e}", "diag": diag["diag"]}
