# Path: src/parsers/tec_html.py
from __future__ import annotations
from typing import Any, Dict, List
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from ._common import extract_jsonld_events, jsonld_to_norm, normalize_event

def fetch_tec_html(source: Dict[str, Any], start_date: str, end_date: str) -> List[Dict[str, Any]]:
    """
    HTML fallback for The Events Calendar sites.
    Strategy:
      1) Use JSON-LD if available (robust).
      2) Fallback to tribe-events-data script or visible DOM.
      3) Final fallback: try TEC REST endpoint (some sites permit it even if 'type' says html).
    """
    site = source["url"]
    name = source.get("name") or source.get("id") or "TEC"
    cal = name
    uid_prefix = (source.get("id") or name).replace(" ", "-").lower()

    session = requests.Session()
    resp = session.get(site, timeout=30)
    resp.raise_for_status()
    html = resp.text

    # 1) JSON-LD
    items = extract_jsonld_events(html)
    events = jsonld_to_norm(items, uid_prefix=uid_prefix, calendar=cal, source_name=name)
    if events:
        return events

    # 2) Tribe data script (best-effort)
    soup = BeautifulSoup(html, "html.parser")
    script = soup.find("script", id="tribe-events-data", type="application/json")
    if script and script.string:
        try:
            import json
            data = json.loads(script.string)
            # Newer TEC embed event data under "events" or "jsonld"—prefer jsonld path if present
            if isinstance(data, dict):
                if "jsonld" in data:
                    events = jsonld_to_norm(
                        data["jsonld"], uid_prefix=uid_prefix, calendar=cal, source_name=name
                    )
                    if events:
                        return events
                if "events" in data and isinstance(data["events"], list):
                    tmp: List[Dict[str, Any]] = []
                    for e in data["events"]:
                        start = e.get("startDate") or e.get("start")
                        end = e.get("endDate") or e.get("end")
                        url = e.get("url")
                        title = e.get("title") or e.get("name")
                        location = None
                        v = e.get("venue") or {}
                        if isinstance(v, dict):
                            location = v.get("address") or v.get("venue") or v.get("name")
                        ev = normalize_event(
                            uid_prefix=uid_prefix,
                            raw_id=e.get("id") or url or title,
                            title=title,
                            url=url,
                            start=start,
                            end=end,
                            location=location,
                            calendar=cal,
                            source_name=name,
                        )
                        if ev:
                            tmp.append(ev)
                    if tmp:
                        return tmp
        except Exception:
            pass

    # 3) As a final fallback, try TEC REST (some html-only configs still allow REST)
    try:
        from .tec_rest import fetch_tec_rest
        return fetch_tec_rest(source, start_date, end_date)
    except Exception:
        return []
