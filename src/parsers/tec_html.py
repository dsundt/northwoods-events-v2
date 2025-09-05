# src/parsers/tec_html.py
"""
TEC (The Events Calendar) 'HTML' adapter.

Surgical approach:
1) Try the proven TEC REST flow (same as Boulder/Eagle/Vilas) first.
2) If REST is not available (or returns 0), fall back to scraping the listing
   and detail pages, preferring JSON-LD @type: Event.

Signature matches main.py expectations:
    fetch_tec_html(source, start_date, end_date) -> list[dict]
"""

from __future__ import annotations
import json
import re
from urllib.parse import urljoin
from dateutil import parser as dtparse
import requests
from bs4 import BeautifulSoup

# Primary: rely on the stable TEC REST parser already working elsewhere
from .tec_rest import fetch_tec_rest


def _to_iso_naive(dt_obj):
    return dt_obj.replace(tzinfo=None).strftime("%Y-%m-%d %H:%M:%S") if dt_obj else None


def _normalize_event(source, title, start_dt, end_dt, url, location):
    uid = f"{abs(hash(url)) % 10**8}@northwoods-v2"
    name = source.get("name") or source.get("id") or "TEC"
    return {
        "uid": uid,
        "title": title or "Untitled",
        "start_utc": _to_iso_naive(start_dt),
        "end_utc": _to_iso_naive(end_dt or start_dt),
        "url": url,
        "location": (location or "").strip() or None,
        "source": name,
        "calendar": name,
    }


def _extract_events_from_listing_jsonld(listing_soup):
    """TEC often emits an array of Event JSON-LD on the listing page."""
    events = []
    for s in listing_soup.find_all("script", {"type": "application/ld+json"}):
        try:
            data = json.loads(s.string or "")
        except Exception:
            continue
        # Could be a list of events or a graph
        blocks = data if isinstance(data, list) else [data]
        for block in blocks:
            if not isinstance(block, dict):
                continue
            # Handle @graph
            nodes = block.get("@graph") if isinstance(block.get("@graph"), list) else [block]
            for obj in nodes:
                if isinstance(obj, dict) and obj.get("@type") in ("Event", ["Event"]):
                    events.append(obj)
    return events


def _fetch_detail_jsonld(session, url):
    """Open a TEC event detail page; read JSON-LD Event if present."""
    try:
        r = session.get(url, timeout=30)
        r.raise_for_status()
        s = BeautifulSoup(r.text, "html.parser")
        # Search JSON-LD for Event
        for scr in s.find_all("script", {"type": "application/ld+json"}):
            try:
                data = json.loads(scr.string or "")
            except Exception:
                continue
            candidates = data if isinstance(data, list) else [data]
            for obj in candidates:
                if isinstance(obj, dict) and obj.get("@type") in ("Event", ["Event"]):
                    return obj
            # @graph
            if isinstance(data, dict) and isinstance(data.get("@graph"), list):
                for obj in data["@graph"]:
                    if isinstance(obj, dict) and obj.get("@type") in ("Event", ["Event"]):
                        return obj
        # Fallback: grab title & try to parse date-ish text
        title_tag = s.find("h1")
        title = title_tag.get_text(" ", strip=True) if title_tag else "Untitled"
        body = s.get_text(" ", strip=True)
        # Weak fallback when no JSON-LD: try ISO-ish or month names
        start_dt = None
        m_iso = re.search(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}", body)
        if m_iso:
            start_dt = dtparse.parse(m_iso.group(0))
        location = None
        m_loc = re.search(r"(Location|Venue)\s*:\s*(.+?)\s{2,}", body)
        if m_loc:
            location = m_loc.group(2).strip()
        return {
            "@type": "Event",
            "name": title,
            "startDate": start_dt.isoformat() if start_dt else None,
            "endDate": None,
            "url": url,
            "location": {"name": location} if location else None,
        }
    except Exception:
        return None


def fetch_tec_html(source, start_date, end_date):
    """
    Preferred path: use TEC REST (stable, already working).
    If that yields nothing (endpoint disabled), use HTML/JSON-LD fallback.
    """
    # 1) Try TEC REST first
    try:
        rest_events = fetch_tec_rest(source, start_date, end_date)
        if rest_events:
            return rest_events
    except Exception:
        # silently fall through to HTML scraping
        pass

    # 2) HTML fallback
    base_url = source.get("url", "").strip()
    if not base_url:
        return []

    session = requests.Session()
    session.headers.update({"User-Agent": "northwoods-events-v2 (+github)"})

    win_start = dtparse.parse(start_date).replace(tzinfo=None) if start_date else None
    win_end = dtparse.parse(end_date).replace(tzinfo=None) if end_date else None

    try:
        r = session.get(base_url, timeout=30)
        r.raise_for_status()
    except Exception:
        return []

    soup = BeautifulSoup(r.text, "html.parser")

    # Prefer JSON-LD on listing (fast & reliable if present)
    jsonld_events = _extract_events_from_listing_jsonld(soup)
    results = []

    def within_window(dtobj):
        if not dtobj:
            return True
        naive = dtobj.replace(tzinfo=None)
        if win_start and naive < win_start:
            return False
        if win_end and naive > win_end:
            return False
        return True

    if jsonld_events:
        for e in jsonld_events:
            title = e.get("name") or "Untitled"
            url = e.get("url") or base_url
            start_dt = dtparse.parse(e["startDate"]) if e.get("startDate") else None
            end_dt = dtparse.parse(e["endDate"]) if e.get("endDate") else None
            if not within_window(start_dt):
                continue
            loc = None
            loc_obj = e.get("location")
            if isinstance(loc_obj, dict):
                loc = loc_obj.get("name") or (
                    loc_obj.get("address", {}).get("streetAddress")
                    if isinstance(loc_obj.get("address"), dict)
                    else None
                )
            results.append(_normalize_event(source, title, start_dt, end_dt, url, loc))
        if results:
            return results

    # If listing JSON-LD missing, collect card links and visit details.
    links = set()
    for a in soup.select('a.tribe-event-url, a[href*="/event/"], a[href*="/events/"]'):
        href = a.get("href") or ""
        full = urljoin(base_url, href)
        if "#tribe" in full:
            continue
        links.add(full)
    detail_urls = list(links)[:200]

    for url in detail_urls:
        meta = _fetch_detail_jsonld(session, url)
        if not meta or meta.get("@type") not in ("Event", ["Event"]):
            continue
        title = meta.get("name") or "Untitled"
        start_dt = dtparse.parse(meta["startDate"]) if meta.get("startDate") else None
        end_dt = dtparse.parse(meta["endDate"]) if meta.get("endDate") else None
        if not within_window(start_dt):
            continue
        loc = None
        loc_obj = meta.get("location")
        if isinstance(loc_obj, dict):
            loc = loc_obj.get("name") or (
                loc_obj.get("address", {}).get("streetAddress")
                if isinstance(loc_obj.get("address"), dict)
                else None
            )
        results.append(_normalize_event(source, title, start_dt, end_dt, url, loc))

    return results
