from __future__ import annotations

import datetime as dt
from urllib.parse import urljoin, urlencode
from typing import List, Tuple, Dict, Any

from src.fetch import get_json
from src.models import Event

API_PATH = "/wp-json/tribe/events/v1/events"


def iso_date(d):
    if isinstance(d, (dt.date, dt.datetime)):
        return d.strftime("%Y-%m-%d")
    return str(d)


def fetch_tec_rest(base_url: str, start_date, end_date, per_page=50, max_pages=8) -> Tuple[List[Event], Dict[str, Any]]:
    """
    Fetch from The Events Calendar REST API.
    Returns (events, diag) where diag has api_url and per-page counts.
    """
    start = iso_date(start_date)
    end = iso_date(end_date)
    events: List[Event] = []
    diag: Dict[str, Any] = {"api_url": None, "pages": []}

    api_root = urljoin(base_url.rstrip("/") + "/", API_PATH.lstrip("/"))

    page = 1
    while page <= max_pages:
        params = {"start_date": start, "end_date": end, "per_page": per_page, "page": page}
        url = f"{api_root}?{urlencode(params)}"
        if page == 1:
            diag["api_url"] = url

        data = get_json(url)
        items = data.get("events", []) or []
        diag["pages"].append({"page": page, "count": len(items)})

        for e in items:
            title = e.get("title")
            url_e = e.get("url") or e.get("website")
            start_iso = e.get("start_date")
            end_iso = e.get("end_date")
            loc = e.get("venue") or {}
            venue = None
            if isinstance(loc, dict):
                venue = ", ".join([x for x in [loc.get("venue"), loc.get("address"), loc.get("city"), loc.get("region")] if x])

            events.append(Event(
                title=title or "(no title)",
                start_utc=start_iso,
                end_utc=end_iso,
                url=url_e,
                location=venue,
                source_name=None,
                calendar=None,
                source_url=base_url,
                meta={"tec_rest_id": e.get("id")},
            ))

        total_pages = data.get("total_pages") or 1
        if page >= total_pages:
            break
        page += 1

    return events, diag
