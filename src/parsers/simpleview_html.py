# src/parsers/simpleview_html.py
"""
Simpleview events parser
- The listing page is often JS-rendered, so scrape is unreliable.
- Strategy:
  1) If sources.yaml provides manual_ics_url, fetch that.
  2) Else, attempt to auto-detect ICS/iCal links on the listing page.
  3) Parse ICS with icalendar to return normalized events.

Signature is tolerant to current main.py calls:
    fetch_simpleview_html(url, start_date=None, end_date=None, session=None, **kwargs)
"""

from __future__ import annotations
from typing import List, Dict, Optional, Any
import re
from datetime import datetime
from dateutil.tz import gettz
import requests
from bs4 import BeautifulSoup
from icalendar import Calendar

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
    return re.sub(r"/+$", "", base) + ("" if href.startswith("/") else "/") + href.lstrip("/")

def _try_load_ics(url: str, session: Optional[requests.Session] = None) -> Optional[bytes]:
    sess = session or requests.Session()
    r = sess.get(url, headers=UA, timeout=30)
    r.raise_for_status()
    ct = r.headers.get("Content-Type", "").lower()
    if "text/calendar" in ct or url.lower().endswith(".ics"):
        return r.content
    # Some sites send text/plain
    if "text/plain" in ct or "text/" in ct:
        return r.content
    # If it looks like ICS, still accept
    if r.text.strip().startswith("BEGIN:VCALENDAR"):
        return r.content
    return None

def _find_ics_link_on_listing(listing_url: str, session: Optional[requests.Session]) -> Optional[str]:
    sess = session or requests.Session()
    r = sess.get(listing_url, headers=UA, timeout=30)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")

    # Look for common ICS anchor patterns
    for a in soup.find_all("a", href=True):
        href = a["href"]
        txt = (a.get_text() or "").lower()
        if any(k in href.lower() for k in (".ics", "ical", "i-cal", "calendar-export")):
            return _abs_url(listing_url, href)
        if "ical" in txt or "add to calendar" in txt:
            return _abs_url(listing_url, href)

    # Some Simpleview sites expose query params that produce ICS
    # Try a few safe patterns if we didn't find explicit links
    candidates = [
        listing_url + ("&" if "?" in listing_url else "?") + "format=ical",
        listing_url + ("&" if "?" in listing_url else "?") + "export=ical",
        listing_url.rstrip("/") + "/?ical=1",
        listing_url.rstrip("/") + "/ical/",
    ]
    for c in candidates:
        try:
            if _try_load_ics(c, session=sess):
                return c
        except Exception:
            continue
    return None

def _events_from_ics(ics_bytes: bytes) -> List[Dict[str, Any]]:
    cal = Calendar.from_ical(ics_bytes)
    events: List[Dict[str, Any]] = []
    for comp in cal.walk():
        if comp.name != "VEVENT":
            continue
        title = _clean_text(str(comp.get("summary")))
        url = _clean_text(str(comp.get("url") or comp.get("X-ALT-DESC") or ""))
        loc = _clean_text(str(comp.get("location")))
        dtstart = comp.get("dtstart")
        dtend = comp.get("dtend")
        start = None
        end = None
        if dtstart:
            val = dtstart.dt
            if isinstance(val, datetime):
                start = val.isoformat()
        if dtend:
            val = dtend.dt
            if isinstance(val, datetime):
                end = val.isoformat()
        events.append({
            "title": title or "Untitled Event",
            "url": url,
            "location": loc,
            "start": start,
            "end": end,
        })
    return events

def fetch_simpleview_html(url: str,
                          start_date: Optional[str] = None,
                          end_date: Optional[str] = None,
                          session: Optional[requests.Session] = None,
                          manual_ics_url: Optional[str] = None,
                          **kwargs) -> List[Dict[str, Any]]:
    """
    Prefer ICS (manual or auto-detected). If no ICS is found, return [] with no error.
    """
    sess = session or requests.Session()

    # 1) If the caller provided a manual ICS URL via sources.yaml (recommended), use it
    if manual_ics_url:
        ics_bytes = _try_load_ics(manual_ics_url, session=sess)
        if ics_bytes:
            return _events_from_ics(ics_bytes)

    # 2) Attempt to auto-detect an ICS/iCal link on the listing page
    ics_link = _find_ics_link_on_listing(url, session=sess)
    if ics_link:
        ics_bytes = _try_load_ics(ics_link, session=sess)
        if ics_bytes:
            return _events_from_ics(ics_bytes)

    # 3) No ICS found (JS-only listing) — return empty; the report will show ok:false for this source
    return []
