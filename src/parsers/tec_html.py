from __future__ import annotations

from typing import Any, Dict, List, Tuple
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime
from dateutil import parser as dtparse
from icalendar import Calendar
from src.fetch import get
from .tec_rest import fetch_tec_rest  # prefer REST when present


def _rest_available(base_url: str) -> bool:
    try:
        probe = urljoin(base_url.rstrip("/") + "/", "wp-json/tribe/events/v1/")
        r = get(probe)
        return r.ok
    except Exception:
        return False


def _coerce_dt(s: str | None) -> str | None:
    if not s:
        return None
    try:
        dt = dtparse.parse(s)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return None


def _try_ics(base: str, source_name: str) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Fallback to TEC calendar ICS feed commonly exposed at:
      /events/?ical=1   or    /?ical=1
    """
    tried = []
    for rel in ("events/?ical=1", "?ical=1"):
        ics_url = urljoin(base.rstrip("/") + "/", rel)
        tried.append(ics_url)
        try:
            resp = get(ics_url)
            if not resp.ok or "BEGIN:VCALENDAR" not in resp.text:
                continue
            cal = Calendar.from_ical(resp.content)
            events: List[Dict[str, Any]] = []
            for comp in cal.walk("VEVENT"):
                title = str(comp.get("summary") or "").strip()
                url = str(comp.get("url") or comp.get("X-ALT-DESC") or "").strip() or None
                loc = str(comp.get("location") or "").strip() or None
                uid = str(comp.get("uid") or f"{abs(hash(title+str(url))) & 0xffffffff}@northwoods-v2")

                dtstart = comp.get("dtstart")
                dtend = comp.get("dtend")
                # dtstart/dtend may be date or datetime
                if hasattr(dtstart, "dt"):
                    sdt = dtstart.dt
                    if isinstance(sdt, datetime):
                        start_utc = sdt.strftime("%Y-%m-%d %H:%M:%S")
                    else:
                        # all-day
                        start_utc = f"{sdt:%Y-%m-%d} 00:00:00"
                else:
                    start_utc = None

                if hasattr(dtend, "dt"):
                    edt = dtend.dt
                    if isinstance(edt, datetime):
                        end_utc = edt.strftime("%Y-%m-%d %H:%M:%S")
                    else:
                        end_utc = f"{edt:%Y-%m-%d} 23:59:59"
                else:
                    end_utc = None

                events.append({
                    "uid": uid,
                    "title": title,
                    "url": url,
                    "start_utc": start_utc,
                    "end_utc": end_utc,
                    "location": loc,
                    "source": source_name,
                    "calendar": source_name,
                })
            if events:
                return events, {"ok": True, "error": "", "diag": {"ics_urls_tried": tried, "count": len(events)}}
        except Exception:
            continue
    return [], {"ok": False, "error": "No ICS available", "diag": {"ics_urls_tried": tried}}


def fetch_tec_html(source: Dict[str, Any], start_date: str | None = None, end_date: str | None = None, **kwargs) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    HTML fallback for TEC sites, but:
      1) If REST exists -> delegate to REST (more reliable).
      2) If no REST -> try list/detail scrape.
      3) If scrape yields nothing -> try site ICS feed.
    """
    base = source["url"]
    source_name = source.get("name") or source.get("id") or "TEC"

    # Prefer REST if present
    if _rest_available(base):
        return fetch_tec_rest(source, start_date, end_date, **kwargs)

    # Minimal list scrape (best-effort)
    list_url = f"{base.rstrip('/')}/?eventDisplay=list"
    try:
        resp = get(list_url)
        soup = BeautifulSoup(resp.text, "html.parser")
        links = []
        for a in soup.select("a[href*='/event/'], a.tribe-events-calendar-list__event-title-link"):
            href = a.get("href")
            if href:
                links.append(urljoin(base, href))
        links = list(dict.fromkeys(links))  # de-dup

        events: List[Dict[str, Any]] = []
        for href in links:
            try:
                dresp = get(href)
                dsoup = BeautifulSoup(dresp.text, "html.parser")
                title_el = dsoup.select_one("h1, .tribe-events-single-event-title")
                title = (title_el.get_text(strip=True) if title_el else "") or (dsoup.title.get_text(strip=True) if dsoup.title else href)
                # Try common datetime attributes first
                start_el = dsoup.select_one("[data-tribe-start-date], time.dt-start, time.tribe-events-c-event-datetime__start-date")
                end_el = dsoup.select_one("[data-tribe-end-date], time.dt-end, time.tribe-events-c-event-datetime__end-date")
                s = start_el.get("datetime") if start_el and start_el.has_attr("datetime") else (start_el.get("data-tribe-start-date") if start_el and start_el.has_attr("data-tribe-start-date") else None)
                e = end_el.get("datetime") if end_el and end_el.has_attr("datetime") else (end_el.get("data-tribe-end-date") if end_el and end_el.has_attr("data-tribe-end-date") else None)

                start_utc = _coerce_dt(s)
                end_utc = _coerce_dt(e)

                # Venue / address
                loc_node = dsoup.select_one(".tribe-events-meta-group-venue, .tribe-venue, .tribe-events-venue, .tribe-events-c-venue__address, .tribe-events-venue-details")
                location = None
                if loc_node:
                    location = " ".join(loc_node.get_text(" ", strip=True).split())

                events.append({
                    "uid": f"{abs(hash(href)) & 0xffffffff}@northwoods-v2",
                    "title": title,
                    "url": href,
                    "start_utc": start_utc,
                    "end_utc": end_utc,
                    "location": location,
                    "source": source_name,
                    "calendar": source_name,
                })
            except Exception:
                continue

        if events:
            return events, {"ok": True, "error": "", "diag": {"list_url": list_url, "count": len(events)}}
    except Exception:
        pass

    # Fallback to ICS if list/detail failed or empty
    return _try_ics(base, source_name)
