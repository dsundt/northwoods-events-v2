# src/parsers/simpleview_html.py
from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any, Dict, List, Tuple, Optional
from urllib.parse import urljoin, urlparse, urlunparse, parse_qsl, urlencode

import requests
from bs4 import BeautifulSoup
from dateutil import parser as dtp
from icalendar import Calendar

DEFAULT_TIMEOUT = 20


def _http_get(url: str, timeout: int = DEFAULT_TIMEOUT) -> requests.Response:
    headers = {
        "User-Agent": "northwoods-events-v2 (+https://github.com/dsundt/northwoods-events-v2)"
    }
    r = requests.get(url, headers=headers, timeout=timeout)
    r.raise_for_status()
    return r


def _to_utc_string(dt: datetime) -> str:
    if dt.tzinfo is not None:
        dt = dt.astimezone(tz=None)
    return dt.replace(tzinfo=None).strftime("%Y-%m-%d %H:%M:%S")


def _with_query(url: str, add: Dict[str, str]) -> str:
    u = urlparse(url)
    q = dict(parse_qsl(u.query))
    q.update(add)
    return urlunparse((u.scheme, u.netloc, u.path, u.params, urlencode(q), u.fragment))


def _try_simpleview_ical(listing_url: str) -> Tuple[Optional[bytes], str]:
    """
    Many Simpleview sites expose an iCal feed on the listing page with ?ical=1 or ?format=ical.
    """
    candidates = [
        _with_query(listing_url, {"ical": "1"}),
        _with_query(listing_url, {"format": "ical"}),
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


def _parse_ics_bytes(data: bytes, start_date: Optional[str], end_date: Optional[str]) -> List[Dict[str, Any]]:
    evs: List[Dict[str, Any]] = []
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

        # Filter
        if start is not None and hasattr(start, "date"):
            d = start.date()
            if sdt and d < sdt:
                continue
            if edt and d > edt:
                continue

        ev = {
            "uid": f"{comp.get('uid') or comp.get('UID') or title}@simpleview-ics",
            "title": title or "(untitled)",
            "url": url,
            "location": loc,
        }
        if isinstance(start, datetime):
            ev["start_utc"] = _to_utc_string(start)
        if isinstance(end, datetime):
            ev["end_utc"] = _to_utc_string(end)
        evs.append(ev)

    return evs


def _collect_detail_links(listing_html: str, base_url: str) -> List[str]:
    soup = BeautifulSoup(listing_html, "html.parser")
    links: List[str] = []
    # Simpleview detail links tend to look like /event/<slug>/<id>/ or /events/<slug>/
    for a in soup.select("a[href]"):
        href = a["href"]
        if not href:
            continue
        if re.search(r"/event[s]?/[^?#]+/\d+/?", href) or re.search(r"/event[s]?/[^?#]+/?$", href):
            links.append(urljoin(base_url, href))
    return list(dict.fromkeys(links))


def _parse_detail_jsonld(url: str) -> Optional[Dict[str, Any]]:
    try:
        html = _http_get(url).text
    except Exception:
        return None

    s = BeautifulSoup(html, "html.parser")
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
                if not loc_name:
                    adr = loc.get("address")
                    if isinstance(adr, dict):
                        loc_name = ", ".join([adr.get(k, "") for k in ("streetAddress", "addressLocality")]).strip(", ") or None

            ev = {
                "uid": f"{url}@simpleview",
                "title": title,
                "url": url,
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

            return ev

    # Fallback minimal title-only
    title_el = s.select_one("h1, .detail-title, .page-title")
    title = title_el.get_text(strip=True) if title_el else "(untitled)"
    return {"uid": f"{url}@simpleview", "title": title, "url": url, "location": None}


def fetch_simpleview_html(source: Dict[str, Any], start_date: Optional[str] = None, end_date: Optional[str] = None
                          ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Simpleview strategy:
      1) Try iCal export on the listing page (?ical=1 or ?format=ical).
      2) If unavailable, collect detail links from the listing HTML and parse JSON-LD on each detail page.
    """
    base_url = source.get("url", "").strip()
    diag: Dict[str, Any] = {"strategy": "simpleview-ics-or-jsonld", "base_url": base_url}
    events: List[Dict[str, Any]] = []

    # 1) iCal attempt
    ics_bytes, ics_url = _try_simpleview_ical(base_url)
    diag["ical_attempt"] = {"url": ics_url, "ok": bool(ics_bytes)}
    if ics_bytes:
        try:
            ics_events = _parse_ics_bytes(ics_bytes, start_date, end_date)
            diag["ical_count"] = len(ics_events)
            if ics_events:
                return ics_events, {"ok": True, "diag": diag}
        except Exception as e:
            diag["ical_error"] = repr(e)

    # 2) Detail crawl + JSON-LD
    try:
        listing_html = _http_get(base_url).text
    except Exception as e:
        diag["listing_error"] = repr(e)
        return [], {"ok": False, "error": f"GET listing failed: {e}", "diag": diag}

    links = _collect_detail_links(listing_html, base_url)
    diag["detail_links_found"] = len(links)

    for href in links:
        ev = _parse_detail_jsonld(href)
        if not ev:
            continue

        # Window filter (best-effort)
        try:
            if start_date and "start_utc" in ev:
                if dtp.parse(ev["start_utc"]).date() < dtp.parse(start_date).date():
                    continue
            if end_date and "start_utc" in ev:
                if dtp.parse(ev["start_utc"]).date() > dtp.parse(end_date).date():
                    continue
        except Exception:
            pass

        events.append(ev)

    diag["events_parsed"] = len(events)
    return events, {"ok": True, "diag": diag}
