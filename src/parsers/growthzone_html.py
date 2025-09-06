# Path: src/parsers/growthzone_html.py
from __future__ import annotations
from typing import Any, Dict, List

import requests
from bs4 import BeautifulSoup

from ._common import extract_jsonld_events, jsonld_to_norm, normalize_event

def fetch_growthzone_html(source: Dict[str, Any], start_date: str, end_date: str) -> List[Dict[str, Any]]:
    """
    GrowthZone calendars vary. Reliable approach:
      1) Parse JSON-LD Events (most GZ pages embed them).
      2) Fallback to visible DOM (cards), extracting date/time & location.
    """
    url = source["url"]
    name = source.get("name") or source.get("id") or "GrowthZone"
    cal = name
    uid_prefix = (source.get("id") or name).replace(" ", "-").lower()

    session = requests.Session()
    resp = session.get(url, timeout=30)
    resp.raise_for_status()
    html = resp.text

    # 1) JSON-LD
    items = extract_jsonld_events(html)
    events = jsonld_to_norm(items, uid_prefix=uid_prefix, calendar=cal, source_name=name)
    if events:
        return events

    # 2) DOM fallback (best-effort generic selectors)
    soup = BeautifulSoup(html, "html.parser")
    candidates = soup.select(".gz-event, .event, .chamberMaster_event, .cm-calendar__event")
    out: List[Dict[str, Any]] = []

    for card in candidates:
        title_tag = card.select_one("a, .gz-event__title, .event-title")
        title = (title_tag.get_text(strip=True) if title_tag else None)
        link = title_tag.get("href") if title_tag and title_tag.has_attr("href") else None

        # Date/time often appears in a date element or meta text
        dt_text = None
        dt_el = card.select_one(".gz-event__date, .event-date, time, .cm-calendar__date, .date")
        if dt_el:
            dt_text = dt_el.get_text(" ", strip=True)
        # Location
        loc_el = card.select_one(".gz-event__location, .event-location, .location, address")
        location = loc_el.get_text(" ", strip=True) if loc_el else None

        # Very generic: hope dateutil parses dt_text; growthzone often uses “Sep 5, 2025 5:00 PM”
        start = dt_text
        end = None

        ev = normalize_event(
            uid_prefix=uid_prefix, raw_id=link or title, title=title, url=link,
            start=start, end=end, location=location, calendar=cal, source_name=name
        )
        if ev:
            out.append(ev)

    return out
