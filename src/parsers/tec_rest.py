from __future__ import annotations
from typing import List, Dict, Any, Tuple
from urllib.parse import urlencode
from bs4 import BeautifulSoup
from dateutil import parser as dtp

from src.fetch import json, get
from src.util import sanitize_event

def _build_api(base: str, start_iso: str, end_iso: str, page: int, per_page: int = 50) -> str:
    # TEC REST: /wp-json/tribe/events/v1/events
    base = base.rstrip("/") + "/wp-json/tribe/events/v1/events"
    qs = urlencode({"start_date": start_iso, "end_date": end_iso, "per_page": per_page, "page": page})
    return f"{base}?{qs}"

def fetch_tec_rest(source: dict, start_iso: str, end_iso: str) -> Tuple[List[dict], dict]:
    diag = {"api_url": None, "pages": []}
    items: List[dict] = []
    page = 1
    while True:
        url = _build_api(source["url"], start_iso, end_iso, page)
        if diag["api_url"] is None:
            diag["api_url"] = url
        try:
            payload, resp = json(url)
        except Exception as e:
            raise
        events = payload.get("events") or []
        for ev in events:
            title = (ev.get("title") or {}).get("rendered") or ev.get("title") or ""
            website = ev.get("url") or ev.get("link") or ""
            start = ev.get("start_date") or ev.get("start") or ev.get("date")
            end = ev.get("end_date") or ev.get("end")
            # Normalize time
            start_iso2 = dtp.parse(start).isoformat() if start else None
            end_iso2 = dtp.parse(end).isoformat() if end else None
            norm = sanitize_event(
                {"title": title, "url": website, "start_utc": start_iso2, "end_utc": end_iso2, "location": ev.get("venue") or None},
                source["name"], source["name"]
            )
            if norm:
                items.append(norm)
        diag["pages"].append({"page": page, "count": len(events)})
        if len(events) < 50:
            break
        page += 1
        if len(items) >= int(source.get("max_events", 100000)):
            break
    return items, diag
