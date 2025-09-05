# src/parsers/tec_rest.py
from __future__ import annotations

import datetime as dt
from typing import List, Dict, Any, Optional
from urllib.parse import urljoin, urlencode

from bs4 import BeautifulSoup  # installed but not used; kept for parity
import requests

def _date_only(s: str) -> str:
    # Accept "YYYY-MM-DD" or "YYYY-MM-DD HH:MM:SS" and always return date only.
    return s[:10]

def _fmt_dt(s: Optional[str]) -> Optional[str]:
    if not s:
        return None
    # TEC REST commonly returns ISO 8601 with TZ. Normalize to "YYYY-MM-DD HH:MM:SS"
    try:
        # Handle strings like "2025-09-06 10:00:00" or ISO with timezone
        try:
            d = dt.datetime.fromisoformat(s.replace("Z", "+00:00"))
        except ValueError:
            # Fallback: just slice safely
            return s[:19] if len(s) >= 19 else s
        return d.astimezone(dt.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return s[:19] if len(s) >= 19 else s

def _events_from_page(payload: Dict[str, Any], source_name: str) -> List[Dict[str, Any]]:
    items = payload.get("events") or []
    out: List[Dict[str, Any]] = []
    for ev in items:
        eid = ev.get("id") or ev.get("uid") or ev.get("slug") or ev.get("url")
        title = (ev.get("title") or {}).get("rendered") if isinstance(ev.get("title"), dict) else ev.get("title")
        url = ev.get("url") or ev.get("website_url") or ev.get("permalink")
        venue = ev.get("venue") or {}
        location = None
        if isinstance(venue, dict):
            # Prefer address line if provided
            location = venue.get("address") or venue.get("venue") or venue.get("city")
        start_raw = ev.get("start_date") or ev.get("start") or ev.get("startDate") or ev.get("start_date_details", {}).get("date")
        end_raw = ev.get("end_date") or ev.get("end") or ev.get("endDate") or ev.get("end_date_details", {}).get("date")

        out.append({
            "uid": f"{eid}@northwoods-v2",
            "title": title or "(untitled)",
            "start_utc": _fmt_dt(start_raw) or None,
            "end_utc": _fmt_dt(end_raw) or None,
            "url": url,
            "location": location,
            "source": source_name,
            "calendar": source_name,
        })
    return out

def _build_api_url(root: str, start_date: str, end_date: str) -> str:
    # root is like "https://boulderjct.org/".
    base = urljoin(root, "/wp-json/tribe/events/v1/events")
    qs = {
        "start_date": _date_only(start_date),
        "end_date": _date_only(end_date),
        "per_page": 50,
        "page": 1,
    }
    return f"{base}?{urlencode(qs)}"

def fetch_tec_rest(source: dict, start_date: str, end_date: str) -> List[Dict[str, Any]]:
    """
    Fetch via The Events Calendar REST API.
    Expects source['url'] to be the site root (e.g., 'https://boulderjct.org/').
    """
    root = source.get("url")
    name = source.get("name") or source.get("id") or "Unknown TEC Site"
    if not root:
        return []

    all_events: List[Dict[str, Any]] = []
    page = 1
    while True:
        api_url = _build_api_url(root, start_date, end_date).replace("page=1", f"page={page}")
        resp = requests.get(api_url, timeout=30)
        resp.raise_for_status()
        payload = resp.json()
        batch = _events_from_page(payload, name)
        all_events.extend(batch)
        # TEC REST includes "total_pages" or simply returns fewer than per_page at the end
        total_pages = payload.get("total_pages")
        if total_pages:
            if page >= int(total_pages):
                break
        else:
            if len(batch) < 50:
                break
        page += 1

    return all_events
