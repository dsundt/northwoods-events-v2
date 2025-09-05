# src/parsers/simpleview_html.py
# Surgical fix:
# - Update signature to (source, start_date, end_date) to stop TypeError.
# - Simpleview listing -> detail scrape (bounded), tolerant selectors.

from __future__ import annotations
from typing import List, Dict, Any
from urllib.parse import urljoin

from bs4 import BeautifulSoup  # type: ignore
from src.fetch import get

MAX_DETAIL_PAGES = 50

def _norm(s: str | None) -> str | None:
    if not s:
        return None
    import re
    return re.sub(r"\s+", " ", s).strip()

def _parse_detail(url: str) -> Dict[str, Any]:
    resp = get(url)
    soup = BeautifulSoup(resp.text, "html.parser")

    # Title
    title_node = soup.select_one("h1, .detail-intro h1, .event-title, .sv-event-title")
    title = _norm(title_node.get_text()) if title_node else "Event"

    # Date/time
    t = soup.select_one("time[datetime]")
    start = None
    end = None
    if t and t.has_attr("datetime"):
        dt = (t["datetime"] or "").strip()
        # normalize 'YYYY-MM-DDTHH:MM:SS±ZZ:ZZ' to 'YYYY-MM-DD HH:MM:SS'
        start = dt.replace("T", " ").split("+")[0].split("Z")[0]

    # Location
    loc_node = soup.select_one(".address, .location, .event-details__location, .sv-event-venue, [itemprop='location']")
    location = _norm(loc_node.get_text()) if loc_node else None

    return {
        "title": title or "Event",
        "url": url,
        "start_utc": start,
        "end_utc": end,
        "location": location,
    }

def fetch_simpleview_html(source: Dict[str, Any], start_date: str | None = None, end_date: str | None = None) -> List[Dict[str, Any]]:
    """
    Match main.py signature. Scrape listing for detail URLs, parse each detail page.
    """
    base = source.get("url") or ""
    if not base:
        return []

    # 1) Fetch listing
    resp = get(base)
    soup = BeautifulSoup(resp.text, "html.parser")

    # 2) Find event detail links (common Simpleview pattern contains '/event/' or query ?event=)
    links: List[str] = []
    for a in soup.select('a[href*="/event/"], a[href*="event="]'):
        href = a.get("href") or ""
        if not href:
            continue
        abs_url = urljoin(base, href)
        if abs_url not in links:
            links.append(abs_url)

    events: List[Dict[str, Any]] = []
    for url in links[:MAX_DETAIL_PAGES]:
        try:
            events.append(_parse_detail(url))
        except Exception:
            continue

    return events
