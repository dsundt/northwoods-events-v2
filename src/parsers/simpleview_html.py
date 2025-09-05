# src/parsers/simpleview_html.py
"""
Simpleview HTML parser (Let's Minocqua).

Surgical fixes:
- Match signature (source, start_date, end_date)
- From the events listing, collect links to '/event/.../<id>/' detail pages
- On each detail page, prefer JSON-LD (@type: "Event") for robust dates/venue
- Filter to the requested window
"""

import json
import re
from datetime import datetime
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

def _extract_event_from_jsonld(soup):
    """
    Return dict with keys: name, startDate, endDate, location (name or address), url
    or None if not found.
    """
    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        try:
            data = json.loads(script.string.strip())
        except Exception:
            continue

        # Sometimes it's a list
        candidates = data if isinstance(data, list) else [data]
        for obj in candidates:
            if isinstance(obj, dict) and obj.get("@type") in ("Event", ["Event"]):
                name = obj.get("name")
                start = obj.get("startDate")
                end = obj.get("endDate")
                url = obj.get("url")
                loc = None
                loc_obj = obj.get("location")
                if isinstance(loc_obj, dict):
                    loc = loc_obj.get("name") or (
                        loc_obj.get("address", {}).get("streetAddress")
                        if isinstance(loc_obj.get("address"), dict)
                        else None
                    )
                return {
                    "name": name,
                    "start": start,
                    "end": end,
                    "url": url,
                    "location": loc,
                }
    return None

def fetch_simpleview_html(source, start_date, end_date):
    base_url = source.get("url", "").strip()
    if not base_url:
        return []

    session = requests.Session()
    session.headers.update({"User-Agent": "northwoods-events-v2 (+github)"})

    window_start = dtparse.parse(start_date).replace(tzinfo=None) if start_date else None
    window_end = dtparse.parse(end_date).replace(tzinfo=None) if end_date else None

    # 1) Listing page
    r = session.get(base_url, timeout=30)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")

    # 2) Collect detail links of the form '/event/.../<id>/' or '/event/.../'
    links = set()
    for a in soup.select('a[href^="/event/"], a[href*="/event/"]'):
        href = a.get("href") or ""
        full = urljoin(base_url, href)
        # Heuristic: avoid in-page anchors and non-event routes
        if "/event/" in full and "#" not in full:
            links.add(full)

    detail_urls = list(links)[:200]

    events = []
    for url in detail_urls:
        try:
            d = session.get(url, timeout=30)
            d.raise_for_status()
            s = BeautifulSoup(d.text, "html.parser")

            # Prefer JSON-LD
            meta = _extract_event_from_jsonld(s)
            if meta:
                title = meta.get("name") or s.find("h1").get_text(" ", strip=True) if s.find("h1") else "Untitled"
                start_dt = dtparse.parse(meta["start"]) if meta.get("start") else None
                end_dt = dtparse.parse(meta["end"]) if meta.get("end") else None
                loc = meta.get("location")
            else:
                # Fallback: try H1 and any datetime-ish text near it
                title_tag = s.find("h1")
                title = title_tag.get_text(" ", strip=True) if title_tag else "Untitled"
                body = s.get_text(" ", strip=True)
                # Look for ISO-like datetime in the page as a fallback
                iso_match = re.search(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}", body)
                start_dt = dtparse.parse(iso_match.group(0)) if iso_match else None
                end_dt = None
                # Location fallback
                loc = None
                mloc = re.search(r"(Location|Venue)\s*:\s*(.+?)\s{2,}", body)
                if mloc:
                    loc = mloc.group(2).strip()

            if start_dt:
                naive = start_dt.replace(tzinfo=None)
                if window_start and naive < window_start:
                    continue
                if window_end and naive > window_end:
                    continue

            events.append(_normalize_event(source, title, start_dt, end_dt, url, loc))
        except Exception:
            continue

    return events
