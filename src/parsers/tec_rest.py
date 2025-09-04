# src/parsers/tec_rest.py
from __future__ import annotations
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from urllib.parse import urljoin, urlencode

from dateutil import parser as dtp
from src.fetch import get, session

def _build_api_url(site_root: str, start: datetime, end: datetime, page: int = 1) -> str:
    base = urljoin(site_root, "/wp-json/tribe/events/v1/events")
    qs = urlencode({
        "start_date": start.date().isoformat(),
        "end_date": end.date().isoformat(),
        "per_page": 50,
        "page": page,
    })
    return f"{base}?{qs}"

def fetch_tec_rest(src: Dict, start: datetime, end: datetime) -> Tuple[List[Dict], Dict]:
    """
    Returns (events, diag). Raises on network errors other than 403/404 (so caller can decide).
    """
    site = src["url"]
    s = session()
    page = 1
    events: List[Dict] = []
    pages_diag = []
    api_url = _build_api_url(site, start, end, page=page)

    try:
        while True:
            api_url = _build_api_url(site, start, end, page=page)
            resp = get(api_url, s=s, retries=1)
            data = resp.json()
            items = data.get("events", [])
            for ev in items:
                start_str = ev.get("start_date") or ev.get("start_date_details", {}).get("datetime")
                end_str = ev.get("end_date") or ev.get("end_date_details", {}).get("datetime")
                start_utc = dtp.parse(start_str).strftime("%Y-%m-%d %H:%M:%S") if start_str else None
                end_utc = dtp.parse(end_str).strftime("%Y-%m-%d %H:%M:%S") if end_str else None
                url = ev.get("url") or ev.get("website")
                location = None
                venue = ev.get("venue")
                if isinstance(venue, dict):
                    location = venue.get("address") or venue.get("venue")

                events.append({
                    "uid": f"{ev.get('id')}@northwoods-v2",
                    "title": ev.get("title"),
                    "start_utc": start_utc,
                    "end_utc": end_utc,
                    "url": url,
                    "location": location,
                    "source": src["name"],
                    "calendar": src["name"],
                })
            pages_diag.append({"page": page, "count": len(items)})
            if not data.get("next_rest_url") or len(items) == 0:
                break
            page += 1

        diag = {"ok": True, "error": "", "diag": {"api_url": _build_api_url(site, start, end, 1), "pages": pages_diag}}
        return events, diag

    except Exception as e:
        # Bubble up to let caller decide on fallback.
        raise
