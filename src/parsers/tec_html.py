# src/parsers/tec_html.py
# Surgical fix:
# - Match main.py's call signature: (source, start_date, end_date)
# - Delegate to the TEC REST implementation when possible (most TEC sites expose it).
# - If delegation fails, fall back to a tolerant HTML scrape (kept very simple).

from __future__ import annotations
from typing import List, Dict, Any
from urllib.parse import urlsplit, urlunsplit
from bs4 import BeautifulSoup  # type: ignore

from src.fetch import get
from .tec_rest import fetch_tec_rest


def _site_root(url: str) -> str:
    parts = urlsplit(url)
    # keep scheme + netloc; empty path
    return urlunsplit((parts.scheme, parts.netloc, "", "", ""))


def _fallback_scrape_list(source: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Very basic HTML list fallback for older TEC list views.
    If used, dates might be less precise; we prefer REST wherever possible.
    """
    url = source.get("url") or ""
    resp = get(url)
    html = resp.text
    soup = BeautifulSoup(html, "html.parser")

    events: List[Dict[str, Any]] = []

    # Try common TEC list selectors (newer & older themes)
    # Newer TEC often uses "tribe-events-calendar-list__event" or "tribe-common--event"
    candidates = soup.select(
        ".tribe-events-calendar-list__event, .tribe-common--event, .tribe-events-calendar-list__event-row"
    )
    if not candidates:
        # fallback: any card with link to /event/ or /events/
        candidates = [a.parent for a in soup.select('a[href*="/event/"], a[href*="/events/"]')]

    for node in candidates:
        a = node.select_one('a[href*="/event/"], a[href*="/events/"]')
        if not a:
            continue
        href = a.get("href") or url
        title = (a.get_text() or "").strip()

        # Date can be in <time> tags or data attributes; try a few places
        start = None
        end = None

        t = node.select_one("time[datetime]")
        if t and t.has_attr("datetime"):
            dt = (t["datetime"] or "").strip()
            if dt:
                # keep as-is, main/ics_writer tolerate "YYYY-MM-DDTHH:MM:SS±ZZ:ZZ" or "YYYY-MM-DD"
                start = dt.replace("T", " ").split("+")[0].split("Z")[0]

        # location heuristic
        loc_node = node.select_one(".tribe-events-venue__name, .tribe-events-venue, .tribe-venue, .venue, .tribe-events-meta-group-venue")
        location = (loc_node.get_text().strip() if loc_node else None) or None

        events.append({
            "title": title or "Event",
            "url": href,
            "start_utc": start,  # may be None if not found; writer will handle date-less events defensively
            "end_utc": end,
            "location": location,
        })

    return events


def fetch_tec_html(source: Dict[str, Any], start_date: str | None = None, end_date: str | None = None) -> List[Dict[str, Any]]:
    """
    Signature now matches main.py. Prefer TEC REST (reliable) but keep an HTML fallback.
    """
    # 1) Prefer TEC REST path (reuses battle-tested code)
    try:
        return fetch_tec_rest(source, start_date, end_date)
    except Exception:
        # 2) Fallback to HTML list scraping (best effort)
        return _fallback_scrape_list(source)
