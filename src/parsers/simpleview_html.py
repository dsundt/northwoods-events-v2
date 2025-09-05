# src/parsers/simpleview_html.py
"""
Simpleview HTML parser (Let's Minocqua).

Fixes:
- Signature (source, start_date, end_date).
- Prefer JSON-LD @type: Event, including when embedded under @graph.
- Robust link discovery on listing.
- Date window filtering.

If a page lacks JSON-LD, we fall back to light heuristics.
"""

from __future__ import annotations
import json
import re
from urllib.parse import urljoin
from dateutil import parser as dtparse
import requests
from bs4 import BeautifulSoup


def _to_iso_naive(dt_obj):
    return dt_obj.replace(tzinfo=None).strftime("%Y-%m-%d %H:%M:%S") if dt_obj else None


def _normalize_event(source, title, start_dt, end_dt, url, location):
    uid = f"{abs(hash(url)) % 10**8}@northwoods-v2"
    name = source.get("name") or source.get("id") or "Simpleview"
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


def _extract_event_jsonld(soup):
    """Return the first JSON-LD Event object found, or None."""
    for script in soup.find_all("script", {"type": "application/ld+json"}):
        try:
            data = json.loads(script.string or "")
        except Exception:
            continue

        # Direct object
        if isinstance(data, dict):
            if data.get("@type") in ("Event", ["Event"]):
                return data
            # @graph with events
            graph = data.get("@graph")
            if isinstance(graph, list):
                for obj in graph:
                    if isinstance(obj, dict) and obj.get("@type") in ("Event", ["Event"]):
                        return obj

        # Array of objects
        if isinstance(data, list):
            for obj in data:
                if isinstance(obj, dict) and obj.get("@type") in ("Event", ["Event"]):
                    return obj
    return None


def fetch_simpleview_html(source, start_date, end_date):
    base_url = (source.get("url") or "").strip()
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

    # Discover event detail links. Simpleview typically uses /event/<slug>/...
    links = set()
    for a in soup.select('a[href*="/event/"], a.m-event-card__link'):
        href = a.get("href") or ""
        full = urljoin(base_url, href)
        if "/event/" in full and "#" not in full:
            links.add(full)
    detail_urls = list(links)[:250]

    def in_window(dtobj):
        if not dtobj:
            return True
        n = dtobj.replace(tzinfo=None)
        if win_start and n < win_start:
            return False
        if win_end and n > win_end:
            return False
        return True

    events = []
    for url in detail_urls:
        try:
            d = session.get(url, timeout=30)
            d.raise_for_status()
            ds = BeautifulSoup(d.text, "html.parser")

            meta = _extract_event_jsonld(ds)
            if meta:
                title = meta.get("name") or (ds.find("h1").get_text(" ", strip=True) if ds.find("h1") else "Untitled")
                start_dt = dtparse.parse(meta["startDate"]) if meta.get("startDate") else None
                end_dt = dtparse.parse(meta["endDate"]) if meta.get("endDate") else None
                if start_dt and not in_window(start_dt):
                    continue
                loc = None
                loc_obj = meta.get("location")
                if isinstance(loc_obj, dict):
                    loc = loc_obj.get("name") or (
                        loc_obj.get("address", {}).get("streetAddress")
                        if isinstance(loc_obj.get("address"), dict)
                        else None
                    )
                events.append(_normalize_event(source, title, start_dt, end_dt, url, loc))
                continue

            # Fallback if no JSON-LD: derive title/date from text
            title_tag = ds.find("h1")
            title = title_tag.get_text(" ", strip=True) if title_tag else "Untitled"
            body = ds.get_text(" ", strip=True)

            # Try ISOish date first
            start_dt = None
            end_dt = None
            m = re.search(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}", body)
            if m:
                start_dt = dtparse.parse(m.group(0))

            if start_dt and not in_window(start_dt):
                continue

            # Basic location fallback
            loc = None
            mloc = re.search(r"(Location|Venue)\s*:\s*(.+?)\s{2,}", body)
            if mloc:
                loc = mloc.group(2).strip()

            events.append(_normalize_event(source, title, start_dt, end_dt, url, loc))
        except Exception:
            continue

    return events
