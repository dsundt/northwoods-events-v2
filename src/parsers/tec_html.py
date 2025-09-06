# src/parsers/tec_html.py
from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any, Dict, List, Tuple, Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from dateutil import parser as dtp
from icalendar import Calendar

DEFAULT_TIMEOUT = 20


def _to_utc_string(dt: datetime) -> str:
    if dt.tzinfo is not None:
        dt = dt.astimezone(tz=None)  # convert to local tz first
        dt = dt.astimezone(tz=None).astimezone()  # normalize
        dt = dt.astimezone(tz=None)
    # Force naive UTC string (main.py normalizer is tolerant but we keep it stable)
    return dt.replace(tzinfo=None).strftime("%Y-%m-%d %H:%M:%S")


def _parse_ics_bytes(data: bytes, start_date: Optional[str], end_date: Optional[str]) -> List[Dict[str, Any]]:
    events: List[Dict[str, Any]] = []
    cal = Calendar.from_ical(data)
    sdt = dtp.parse(start_date).date() if start_date else None
    edt = dtp.parse(end_date).date() if end_date else None

    for comp in cal.walk():
        if comp.name != "VEVENT":
            continue
        title = str(comp.get("summary") or "").strip()
        url = str(comp.get("url") or comp.get("UID") or "").strip() or None
        loc = str(comp.get("location") or "").strip() or None

        dtstart = comp.get("dtstart")
        dtend = comp.get("dtend")
        try:
            start = dtstart.dt if dtstart else None
            end = dtend.dt if dtend else None
        except Exception:
            start = end = None

        # Filter by window if provided
        if start is not None and hasattr(start, "date"):
            d = start.date()
            if sdt and d < sdt:
                continue
            if edt and d > edt:
                continue

        ev = {
            "uid": f"{comp.get('uid') or comp.get('UID') or title}@tec-html",
            "title": title or "(untitled)",
            "url": url,
            "location": loc,
        }
        if isinstance(start, datetime):
            ev["start_utc"] = _to_utc_string(start)
        if isinstance(end, datetime):
            ev["end_utc"] = _to_utc_string(end)

        events.append(ev)

    return events


def _http_get(url: str, timeout: int = DEFAULT_TIMEOUT) -> requests.Response:
    headers = {
        "User-Agent": "northwoods-events-v2 (+https://github.com/dsundt/northwoods-events-v2)"
    }
    r = requests.get(url, headers=headers, timeout=timeout)
    r.raise_for_status()
    return r


def _try_tec_ical(base_url: str) -> Tuple[Optional[bytes], str]:
    """
    Try common TEC iCal endpoints in a safe order, returning (data, which_url).
    """
    candidates = [
        # canonical TEC feed on sites with /events/ listing
        urljoin(base_url, "events/?ical=1"),
        # sometimes homepage ical exists
        urljoin(base_url, "?ical=1"),
        # some sites expose list display ical
        urljoin(base_url, "events/?tribe_display=list&ical=1"),
    ]

    for u in candidates:
        try:
            resp = _http_get(u)
            body = resp.content or b""
            if body and b"BEGIN:VCALENDAR" in body:
                return body, u
        except Exception:
            continue
    return None, ""


def fetch_tec_html(source: Dict[str, Any], start_date: Optional[str] = None, end_date: Optional[str] = None
                   ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Robust TEC HTML fetcher for sites without reliable REST (e.g., St. Germain).
    Strategy:
      1) Attempt TEC's built-in iCal feed (?ical=1). This is the most stable and version-proof.
      2) If not found, fall back to minimal HTML crawl and JSON-LD extraction (best-effort).
    Returns (events, diag).
    """
    base_url = source.get("url", "").strip()
    diag: Dict[str, Any] = {"strategy": "tec-html", "base_url": base_url, "steps": []}
    events: List[Dict[str, Any]] = []

    # 1) iCal feed
    ics_bytes, ics_url = _try_tec_ical(base_url)
    diag["steps"].append({"step": "try_ical", "url": ics_url, "ok": bool(ics_bytes)})

    if ics_bytes:
        try:
            events = _parse_ics_bytes(ics_bytes, start_date, end_date)
            diag["ical_count"] = len(events)
            return events, {"ok": True, "diag": diag}
        except Exception as e:
            diag["ical_error"] = repr(e)

    # 2) Minimal HTML fallback – look for links to individual events and parse JSON-LD there
    try:
        listing = _http_get(base_url).text
        soup = BeautifulSoup(listing, "html.parser")
        links = []
        for a in soup.select("a[href]"):
            href = a["href"]
            if not href:
                continue
            # TEC event permalink often contains /event/ or /events/ with a slug
            if re.search(r"/event(s)?/[^?#]+", href):
                links.append(urljoin(base_url, href))
        links = list(dict.fromkeys(links))  # dedupe
        diag["fallback_links"] = len(links)

        for href in links:
            try:
                html = _http_get(href).text
                s = BeautifulSoup(html, "html.parser")
                # JSON-LD
                for tag in s.select('script[type="application/ld+json"]'):
                    try:
                        data = json.loads(tag.string or "{}")
                    except Exception:
                        continue
                    items = data if isinstance(data, list) else [data]
                    for it in items:
                        if not isinstance(it, dict):
                            continue
                        if it.get("@type") not in ("Event", "MusicEvent", "TheaterEvent"):
                            continue
                        title = (it.get("name") or "").strip() or "(untitled)"
                        start = it.get("startDate")
                        end = it.get("endDate")
                        loc = it.get("location")
                        loc_name = None
                        if isinstance(loc, dict):
                            loc_name = loc.get("name") or None
                            # prefer a human-friendly line
                            if not loc_name:
                                adr = loc.get("address")
                                if isinstance(adr, dict):
                                    loc_name = ", ".join([adr.get(k, "") for k in ("streetAddress", "addressLocality")]).strip(", ") or None

                        ev = {
                            "uid": f"{href}@tec-html",
                            "title": title,
                            "url": href,
                            "location": loc_name,
                        }
                        if start:
                            try:
                                ev["start_utc"] = _to_utc_string(dtp.parse(start))
                            except Exception:
                                pass
                        if end:
                            try:
                                ev["end_utc"] = _to_utc_string(dtp.parse(end))
                            except Exception:
                                pass

                        # Window filter (best-effort)
                        if start_date and "start_utc" in ev:
                            if dtp.parse(ev["start_utc"]).date() < dtp.parse(start_date).date():
                                continue
                        if end_date and "start_utc" in ev:
                            if dtp.parse(ev["start_utc"]).date() > dtp.parse(end_date).date():
                                continue

                        events.append(ev)
            except Exception:
                continue

        diag["fallback_count"] = len(events)
        return events, {"ok": True, "diag": diag}
    except Exception as e:
        diag["fallback_error"] = repr(e)

    return [], {"ok": False, "error": "TEC HTML parse produced no events", "diag": diag}
