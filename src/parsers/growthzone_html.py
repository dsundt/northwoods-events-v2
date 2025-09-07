# src/parsers/growthzone_html.py
# DROP-IN REPLACEMENT
#
# Purpose:
# - Parse GrowthZone (ChamberMaster) event listings by FIRST discovering an ICS feed on the page,
#   then parsing that ICS (more stable than scraping HTML).
# - Function signature matches main.py expectations: (source, start_date, end_date)
# - Returns: (events: list[dict], diag: dict)  -- non-breaking, similar to tec_rest style
#
# Dependencies available in requirements.txt:
#   requests, beautifulsoup4, icalendar, python-dateutil, PyYAML
#
# Notes:
# - We do not modify other parsers or working TEC sources.
# - We keep events normalized: title, start (UTC), end (UTC or None), url, location, id (string)
# - We filter to [start_date, end_date] inclusive.
# - We tolerate all-day events (date-only) and missing DTEND.

from __future__ import annotations

import re
from datetime import datetime, date, time, timezone
from typing import Tuple, List, Dict, Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from dateutil import tz
import requests
from icalendar import Calendar, Event

LOCAL_TZ = tz.gettz("America/Chicago")  # GrowthZone sites here are WI-based
UTC = tz.UTC

# ---- Small HTTP helper (uses your existing requests pin) ----
def _get(url: str, timeout: int = 20) -> requests.Response:
    # Ensure url is truly a string (avoid the "InvalidSchema" crash when a dict leaks in)
    if not isinstance(url, str):
        raise TypeError(f"_get expected a URL string, got {type(url)}")
    resp = requests.get(url, timeout=timeout, headers={"User-Agent": "northwoods-v2/1.0"})
    resp.raise_for_status()
    return resp

# ---- Date helpers ----
def _coerce_date(d) -> date:
    if isinstance(d, date) and not isinstance(d, datetime):
        return d
    if isinstance(d, datetime):
        return d.date()
    # string like '2025-09-04'
    return datetime.fromisoformat(str(d)).date()

def _to_utc(dtobj) -> datetime:
    """Normalize icalendar dt to UTC aware datetime."""
    if isinstance(dtobj, date) and not isinstance(dtobj, datetime):
        # All-day: assume local midnight start
        dtobj = datetime.combine(dtobj, time(0, 0))
    if dtobj.tzinfo is None:
        dtobj = dtobj.replace(tzinfo=LOCAL_TZ)
    return dtobj.astimezone(UTC)

def _in_window(start_utc: datetime, end_utc: Optional[datetime], start_date: date, end_date: date) -> bool:
    # Keep event if any overlap with [start_date, end_date]
    window_start = datetime.combine(start_date, time(0, 0, tzinfo=UTC))
    window_end = datetime.combine(end_date, time(23, 59, 59, tzinfo=UTC))
    s = start_utc
    e = end_utc or start_utc
    return not (e < window_start or s > window_end)

# ---- ICS parsing ----
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
        start_val = dtstart.dt
        start_utc = _to_utc(start_val)

        dtend = comp.get("dtend")
        end_utc = _to_utc(dtend.dt) if dtend else None

        url = str(comp.get("url", "")).strip() or None
        location = str(comp.get("location", "")).strip() or None

        # Filter to window
        if not _in_window(start_utc, end_utc, start_date, end_date):
            continue

        # Build a stable id: prefer UID, else fallback
        uid_val = comp.get("uid")
        uid = str(uid_val) if uid_val else f"gz-{hash((summary, start_utc.isoformat(), url or ''))}"

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

# ---- ICS discovery on GrowthZone pages ----
_ICS_CANDIDATE_PATTERNS = [
    re.compile(r"events/ical", re.I),
    re.compile(r"calendar/ical", re.I),
    re.compile(r"[?&]format=ical", re.I),
    re.compile(r"\.ics(\b|$)", re.I),
]

def _discover_ics_href(html: str, page_url: str) -> Optional[str]:
    soup = BeautifulSoup(html, "html.parser")

    # Try <link rel="alternate" type="text/calendar">
    for link in soup.find_all("link", attrs={"rel": True, "type": True, "href": True}):
        rels = [r.lower() for r in (link.get("rel") or [])]
        typ = (link.get("type") or "").lower()
        href = link.get("href")
        if "alternate" in rels and typ in ("text/calendar", "text/x-vcalendar") and href:
            return urljoin(page_url, href)

    # Try <a> candidates with common ICS patterns
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if any(p.search(href) for p in _ICS_CANDIDATE_PATTERNS):
            return urljoin(page_url, href)

    return None

# ---- Public entry point (used by main.py) ----
def fetch_growthzone_html(source: Dict, start_date, end_date) -> Tuple[List[Dict], Dict]:
    """
    :param source: dict with keys: name, id, type, url
    :param start_date: date or ISO string
    :param end_date: date or ISO string
    :return: (events, diag)
    """
    # Defensive conversions
    page_url = str(source.get("url", "")).strip()
    if not page_url:
        return [], {"ok": False, "error": "Missing source.url", "diag": {}}

    sd = _coerce_date(start_date)
    ed = _coerce_date(end_date)

    diag: Dict = {"ok": True, "error": "", "diag": {"page_url": page_url}}

    # 1) Load listing page and discover ICS
    try:
        page = _get(page_url)
    except Exception as e:
        return [], {"ok": False, "error": f"GET listing failed: {e}", "diag": {"page_url": page_url}}

    ics_href = _discover_ics_href(page.text, page_url)
    diag["diag"]["ics_url"] = ics_href

    if not ics_href:
        # No ICS found — GrowthZone pages almost always expose one; without it HTML scraping gets brittle.
        # We fail gracefully with a strong diagnostic so we can adjust if needed, without breaking other sources.
        return [], {"ok": False, "error": "No ICS link discovered on GrowthZone page", "diag": diag["diag"]}

    # 2) Fetch and parse ICS
    try:
        ics_resp = _get(ics_href)
        events = _parse_ics_bytes(ics_resp.content, sd, ed)
        diag["diag"]["ics_events"] = len(events)
        return events, diag
    except Exception as e:
        return [], {"ok": False, "error": f"ICS fetch/parse failed: {e}", "diag": diag["diag"]}
