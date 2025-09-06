from __future__ import annotations

from typing import Any, Dict, List, Tuple
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime, timedelta
from src.fetch import get
from .tec_rest import fetch_tec_rest  # delegate when REST exists


def _rest_available(base_url: str) -> bool:
    try:
        probe = urljoin(base_url.rstrip("/") + "/", "wp-json/tribe/events/v1/")
        r = get(probe)
        return r.ok
    except Exception:
        return False


def fetch_tec_html(source: Dict[str, Any], start_date: str | None = None, end_date: str | None = None, **kwargs) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    HTML fallback for older TEC list pages, but **automatically delegates to TEC REST**
    if the endpoint is available. This lets you keep `type: tec_html` in sources.yaml
    without sacrificing reliability.
    """
    base = source["url"]
    if _rest_available(base):
        # Delegate — REST is far more stable and gives structured data (incl. venue).
        return fetch_tec_rest(source, start_date, end_date, **kwargs)

    # If truly no REST, try to scrape list view.
    # We keep this minimal and tolerant; many TEC sites have pagination & different classes.
    # Note: Without REST, locations are often missing in list tiles.
    start = start_date or datetime.utcnow().strftime("%Y-%m-%d")
    list_url = f"{base.rstrip('/')}/?eventDisplay=list&tribe-bar-date={start}"
    resp = get(list_url)
    soup = BeautifulSoup(resp.text, "html.parser")

    # TEC v6 list items commonly have data-event-id or anchor with class containing 'event-title'
    items = []
    for a in soup.select("a[href*='/event/'], a.tribe-events-calendar-list__event-title-link"):
        title = (a.get_text() or "").strip()
        href = urljoin(base, a.get("href"))
        if not title or not href:
            continue
        items.append({"title": title, "url": href})

    # We can’t reliably get start/end from the list view; fetch details—best-effort.
    events: List[Dict[str, Any]] = []
    for it in items:
        try:
            dresp = get(it["url"])
            dsoup = BeautifulSoup(dresp.text, "html.parser")
            # Common TEC detail meta tags
            start = dsoup.select_one("[data-tribe-start-date], time.dt-start, time.tribe-events-c-event-datetime__start-date")
            end = dsoup.select_one("[data-tribe-end-date], time.dt-end, time.tribe-events-c-event-datetime__end-date")
            start_s = start.get("datetime") if start and start.has_attr("datetime") else (start.get("data-tribe-start-date") if start and start.has_attr("data-tribe-start-date") else None)
            end_s = end.get("datetime") if end and end.has_attr("datetime") else (end.get("data-tribe-end-date") if end and end.has_attr("data-tribe-end-date") else None)

            # Venue text often appears in element with class containing 'venue' or 'location'
            loc_node = dsoup.select_one(".tribe-events-meta-group-venue, .tribe-venue, .tribe-events-venue, .tribe-events-c-venue__address, .tribe-events-venue-details")
            location = None
            if loc_node:
                location = " ".join(loc_node.get_text(" ").split())

            events.append({
                "uid": f"{hash(it['url']) & 0xffffffff}@northwoods-v2",
                "title": it["title"],
                "url": it["url"],
                "start_utc": (start_s or "").replace("T", " ").replace("Z", ""),
                "end_utc": (end_s or "").replace("T", " ").replace("Z", ""),
                "location": location,
                "source": source.get("name") or source.get("id") or "TEC",
                "calendar": source.get("name") or source.get("id") or "TEC",
            })
        except Exception:
            continue

    return events, {"ok": True, "error": "", "diag": {"list_url": list_url, "count": len(events)}}
