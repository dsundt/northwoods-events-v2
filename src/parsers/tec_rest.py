# Path: src/parsers/tec_rest.py
from __future__ import annotations
from typing import Any, Dict, List
from urllib.parse import urljoin

import requests

from ._common import normalize_event, _join_loc

def _rest_base(site_url: str) -> str:
    base = site_url.strip()
    if not base.endswith("/"):
        base += "/"
    return urljoin(base, "wp-json/tribe/events/v1/events")

def fetch_tec_rest(source: Dict[str, Any], start_date: str, end_date: str) -> List[Dict[str, Any]]:
    """
    Fetch from The Events Calendar REST API.
    Returns normalized event dicts.
    """
    site = source["url"]
    name = source.get("name") or source.get("id") or "TEC"
    cal = name
    uid_prefix = (source.get("id") or name).replace(" ", "-").lower()

    events: List[Dict[str, Any]] = []
    endpoint = _rest_base(site)

    page = 1
    session = requests.Session()
    while True:
        params = {
            "start_date": start_date,
            "end_date": end_date,
            "per_page": 50,
            "page": page,
        }
        resp = session.get(endpoint, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        items = data.get("events") or []
        if not items:
            break

        for e in items:
            # The Events Calendar REST commonly returns date fields like "start_date" / "end_date"
            start = e.get("start_date") or e.get("start")
            end = e.get("end_date") or e.get("end")
            url = e.get("url")
            eid = e.get("id")
            title = (e.get("title") or {}).get("rendered") or e.get("title") or e.get("name")

            # Venue / location assembly
            v = e.get("venue") or {}
            location = _join_loc([
                v.get("venue"),
                v.get("address"),
                v.get("city"),
                v.get("state"),
                v.get("zip"),
            ])

            ev = normalize_event(
                uid_prefix=uid_prefix, raw_id=eid, title=title, url=url,
                start=start, end=end, location=location, calendar=cal, source_name=name
            )
            if ev:
                events.append(ev)

        # Paging: stop when less than per_page
        if len(items) < 50:
            break
        page += 1

    return events
