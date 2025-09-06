from __future__ import annotations

from typing import Any, Dict, List, Tuple
from urllib.parse import urljoin, urlencode
from datetime import datetime, timedelta
from dateutil import parser as dtparse
from src.fetch import get


def _date_str(d: datetime) -> str:
    return d.strftime("%Y-%m-%d")


def _as_local_naive(s: str | None) -> str | None:
    """
    TEC REST returns e.g. '2025-09-04 10:00:00' (site tz) or ISO.
    We coerce to 'YYYY-MM-DD HH:MM:SS' (naive) so downstream stays consistent.
    """
    if not s:
        return None
    try:
        dt = dtparse.parse(s)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return s  # leave as-is


def _location_from_venue(e: Dict[str, Any]) -> str | None:
    v = e.get("venue") or {}
    parts = []
    # TEC v1 returns keys like 'venue', 'address', 'city', 'state', 'zip'
    for key in ("venue", "address", "city", "state", "zip"):
        val = v.get(key)
        if val:
            parts.append(str(val).strip())
    return ", ".join(p for p in parts if p) or None


def _normalize(e: Dict[str, Any], source_name: str) -> Dict[str, Any]:
    uid = f"{e.get('id')}@northwoods-v2"
    title = (e.get("title") or "").strip()
    url = e.get("url") or e.get("link") or None
    start_utc = _as_local_naive(e.get("start_date") or e.get("start"))
    end_utc = _as_local_naive(e.get("end_date") or e.get("end"))
    location = _location_from_venue(e) or (e.get("venue") or {}).get("venue")

    # All-day safeguard: if only date provided, make it an all-day block
    if start_utc and len(start_utc) == 10:  # 'YYYY-MM-DD'
        start_utc = start_utc + " 00:00:00"
    if end_utc and len(end_utc) == 10:
        end_utc = end_utc + " 23:59:59"

    return {
        "uid": uid,
        "title": title,
        "url": url,
        "start_utc": start_utc,
        "end_utc": end_utc,
        "location": location,
        "source": source_name,
        "calendar": source_name,
    }


def fetch_tec_rest(source: Dict[str, Any], start_date: str | None = None, end_date: str | None = None, **_) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Pulls events from The Events Calendar REST endpoint:
      <site>/wp-json/tribe/events/v1/events

    start_date / end_date are 'YYYY-MM-DD'. If None, defaults to [today .. today+120 days].
    """
    base = source["url"].rstrip("/") + "/"
    source_name = source.get("name") or source.get("id") or "Unknown TEC"
    start = start_date or _date_str(datetime.utcnow())
    end = end_date or _date_str(datetime.utcnow() + timedelta(days=120))

    api_base = urljoin(base, "wp-json/tribe/events/v1/events")
    per_page = 50
    page = 1
    all_events: List[Dict[str, Any]] = []
    pages_info: List[Dict[str, Any]] = []

    while True:
        qs = {
            "start_date": start,
            "end_date": end,
            "per_page": per_page,
            "page": page,
        }
        url = f"{api_base}?{urlencode(qs)}"
        resp = get(url)
        data = resp.json()
        events = data.get("events") or []
        pages_info.append({"page": page, "count": len(events)})
        for e in events:
            all_events.append(_normalize(e, source_name))
        if len(events) < per_page:
            break
        page += 1

    diag = {
        "ok": True,
        "error": "",
        "diag": {
            "api_url": f"{api_base}?start_date={start}&end_date={end}&per_page={per_page}&page=1",
            "pages": pages_info,
        },
    }
    return all_events, diag
