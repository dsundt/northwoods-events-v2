from __future__ import annotations
import datetime as dt
from urllib.parse import urljoin, urlencode
import json
import requests
from typing import Dict, Any, List, Tuple

def _iso(d: dt.date | dt.datetime) -> str:
    if isinstance(d, dt.datetime):
        return d.date().isoformat()
    return d.isoformat()

def _build_api_url(base: str, start: dt.date, end: dt.date, page: int, per_page: int) -> str:
    # Standard The Events Calendar REST path
    api_path = "/wp-json/tribe/events/v1/events"
    qs = {
        "start_date": _iso(start),
        "end_date": _iso(end),
        "per_page": per_page,
        "page": page,
    }
    return urljoin(base, api_path) + "?" + urlencode(qs)

def _page(base: str, start: dt.date, end: dt.date, page: int, per_page: int) -> Dict[str, Any]:
    url = _build_api_url(base, start, end, page, per_page)
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    return resp.json()

def _as_events(items: List[Dict[str, Any]], source_label: str) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for it in items:
        # TEC provides UTC times under 'utc_start_date' / 'utc_end_date' (if available),
        # but some sites only supply 'start_date' (site tz). Keep UTC if present.
        start_utc = it.get("utc_start_date") or it.get("start_date")
        end_utc = it.get("utc_end_date") or it.get("end_date")
        out.append({
            "uid": f"{it.get('id')}@northwoods-v2",
            "title": it.get("title") or "",
            "start_utc": start_utc,
            "end_utc": end_utc,
            "url": it.get("url") or "",
            "location": (it.get("venue", {}) or {}).get("address"),
            "source": source_label,
            "calendar": source_label,
        })
    return out

def fetch_tec_rest(base_url: str, start: dt.date, end: dt.date, per_page: int = 50, max_pages: int = 12
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Pulls events from TEC REST. If the REST endpoint 404s (as with St. Germain or Oneida),
    we return [] and include a diag showing the failing URL. We do NOT try HTML fallbacks here
    to keep behavior isolated and predictable for working sources.
    """
    events: List[Dict[str, Any]] = []
    diag = {"api_url": _build_api_url(base_url, start, end, 1, per_page), "pages": []}
    try:
        for page in range(1, max_pages + 1):
            data = _page(base_url, start, end, page, per_page)
            items = data.get("events", []) or data.get("data", []) or []
            if not items:
                break
            events.extend(_as_events(items, source_label=""))
            diag["pages"].append({"page": page, "count": len(items)})
            if len(items) < per_page:  # last page
                break
        # fill source_label now to avoid copying on each event
        for e in events:
            e["source"] = e["calendar"] = ""
        ok = True
        error = ""
    except requests.HTTPError as e:
        ok = False
        error = f"HTTPError: {e}"
    except Exception as e:
        ok = False
        error = f"{type(e).__name__}: {e}"
    return events, {"ok": ok, "error": error, "diag": diag}
