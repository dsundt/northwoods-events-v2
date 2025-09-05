# src/parsers/tec_rest.py
from __future__ import annotations

import json
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Tuple
from urllib.parse import urlparse, urlunparse

import requests
from dateutil import parser as dtp


def _to_origin(site_url: str) -> str:
    """
    Normalize any TEC site/page URL to its scheme://host origin.
    """
    u = urlparse(site_url)
    return urlunparse((u.scheme or "https", u.netloc, "", "", "", ""))


def _api_url(origin: str, page: int, start_date: str, end_date: str) -> str:
    return f"{origin}/wp-json/tribe/events/v1/events?start_date={start_date}&end_date={end_date}&per_page=50&page={page}"


def _request_json(url: str) -> Dict[str, Any]:
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    return r.json()


def _normalize_event(e: Dict[str, Any], source_name: str, source_id: str) -> Dict[str, Any]:
    # TEC REST returns ISO strings; they often include timezone offsets.
    def to_utc(s: str | None) -> str | None:
        if not s:
            return None
        try:
            return dtp.parse(s).astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            return None

    title = (e.get("title") or {}).get("rendered") or e.get("title") or ""
    url = e.get("url") or e.get("link")
    venue = (e.get("venue") or {}).get("address") or (e.get("venue") or {}).get("venue") or None
    start_utc = to_utc(e.get("start_date"))
    end_utc = to_utc(e.get("end_date"))

    # TEC's numeric id is stable; combine with repo tag for UID
    uid = f"{e.get('id', 'evt')}@northwoods-v2"

    return {
        "uid": uid,
        "title": title.strip(),
        "start_utc": start_utc,
        "end_utc": end_utc,
        "url": url,
        "location": venue,
        "source": source_name,
        "calendar": source_name,
        "source_id": source_id,
    }


def fetch_tec_rest(url: str, start_date: str, end_date: str) -> List[Dict[str, Any]]:
    """
    Pulls events via The Events Calendar REST API.

    Args:
        url: Any page on the TEC site (home, /events/, etc.)
        start_date: YYYY-MM-DD
        end_date:   YYYY-MM-DD

    Returns:
        List of normalized event dicts.
    """
    origin = _to_origin(url)
    page = 1
    events: List[Dict[str, Any]] = []
    source_name = None
    source_id = None  # filled by main.py after normalization; safe to keep placeholder now

    while True:
        api = _api_url(origin, page, start_date, end_date)
        data = _request_json(api)
        items = data.get("events") or []
        if not items:
            break
        for e in items:
            ev = _normalize_event(e, source_name or "", source_id or "")
            events.append(ev)
        page += 1
        if not data.get("rest_url") and len(items) < 50:
            # Conservative exit if pagination hints are missing
            break
        if page > 20:  # hard safety cap
            break

    return events


def fetch_tec_html(url: str, start_date: str, end_date: str) -> List[Dict[str, Any]]:
    """
    Wrapper for historical 'tec_html' type.

    Most TEC sites expose REST; prefer that. We derive origin from the HTML/list
    URL and call the REST loader to keep behavior identical.

    Keeping this ensures old configs that still say 'tec_html' continue working.
    """
    return fetch_tec_rest(url, start_date, end_date)
