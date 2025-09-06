# Path: src/parsers/simpleview_html.py
from __future__ import annotations
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin, urlparse, parse_qs

import requests

from ._common import extract_jsonld_events, jsonld_to_norm, normalize_event

def _try_json_endpoints(base_url: str, session: requests.Session) -> List[Dict[str, Any]]:
    """
    Try common Simpleview JSON endpoints:
      - ?format=json appended to the events listing URL
      - /events/?format=json
      - /events?format=json
    """
    urls = []
    # Given URL may already be /events/ or /events
    if "?" in base_url:
        urls.append(base_url + "&format=json")
    else:
        urls.append(base_url + "?format=json")

    # Also attempt normalized variants
    if base_url.rstrip("/").endswith("/events"):
        urls.append(base_url.rstrip("/") + "/?format=json")
    elif "/events/" in base_url:
        urls.append(base_url.rstrip("/") + "/?format=json")

    for u in urls:
        try:
            r = session.get(u, timeout=30)
            if r.status_code != 200:
                continue
            data = r.json()
            # Common shapes: {"Items": [...]} or {"items":[...]} or {"results":[...]}
            items = data.get("Items") or data.get("items") or data.get("results")
            if not isinstance(items, list):
                continue
            out = []
            for idx, it in enumerate(items):
                title = it.get("Title") or it.get("title") or it.get("Name") or it.get("name")
                url = it.get("Url") or it.get("url") or it.get("DetailURL") or it.get("detailUrl")
                start = it.get("StartDate") or it.get("startDate") or it.get("Start")
                end = it.get("EndDate") or it.get("endDate") or it.get("End")
                # location may be composed from Venue fields
                venue_name = (it.get("VenueName") or it.get("venueName") or
                              (it.get("Venue") or {}).get("Name"))
                city = it.get("City") or it.get("city")
                location = " | ".join([x for x in [venue_name, city] if x])
                out.append((title, url, start, end, location))
            if out:
                return out
        except Exception:
            continue
    return []

def fetch_simpleview_html(source: Dict[str, Any], start_date: str, end_date: str) -> List[Dict[str, Any]]:
    """
    Simpleview calendars:
      1) Prefer JSON-LD on the HTML page (robust).
      2) Try known JSON endpoints (?format=json variants).
      3) Fallback returns [].
    """
    url = source["url"]
    name = source.get("name") or source.get("id") or "Simpleview"
    cal = name
    uid_prefix = (source.get("id") or name).replace(" ", "-").lower()

    session = requests.Session()
    # First load the HTML (for JSON-LD)
    try:
        resp = session.get(url, timeout=30)
        resp.raise_for_status()
        html = resp.text
        items = extract_jsonld_events(html)
        events = jsonld_to_norm(items, uid_prefix=uid_prefix, calendar=cal, source_name=name)
        if events:
            return events
    except Exception:
        # keep going to JSON endpoints
        pass

    # Try JSON endpoints
    json_items = _try_json_endpoints(url, session)
    out: List[Dict[str, Any]] = []
    for idx, (title, link, start, end, location) in enumerate(json_items):
        ev = normalize_event(
            uid_prefix=uid_prefix, raw_id=link or title or idx, title=title, url=link,
            start=start, end=end, location=location, calendar=cal, source_name=name
        )
        if ev:
            out.append(ev)

    return out
