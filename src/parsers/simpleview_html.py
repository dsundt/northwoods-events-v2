# src/parsers/simpleview_html.py
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup
from dateutil import parser as dtp
from datetime import datetime
import json

from src.fetch import get

def _dt_to_str(dt: Optional[datetime]) -> Optional[str]:
    if not dt:
        return None
    return dt.strftime("%Y-%m-%d %H:%M:%S")

def _parse_ldjson(block: str) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    try:
        data = json.loads(block.strip())
    except Exception:
        return out

    items = data if isinstance(data, list) else [data]
    for obj in items:
        if not isinstance(obj, dict):
            continue
        # Handle flat Event or graph
        candidates = []
        if obj.get("@type") == "Event":
            candidates = [obj]
        elif "@graph" in obj and isinstance(obj["@graph"], list):
            candidates = [x for x in obj["@graph"] if isinstance(x, dict) and x.get("@type") == "Event"]

        for ev in candidates:
            title = (ev.get("name") or "").strip()
            if not title:
                continue

            start_s = ev.get("startDate")
            end_s = ev.get("endDate")
            try:
                start_dt = dtp.parse(start_s) if start_s else None
                end_dt = dtp.parse(end_s) if end_s else None
            except Exception:
                start_dt = end_dt = None

            loc = None
            loc_obj = ev.get("location")
            if isinstance(loc_obj, dict):
                loc = loc_obj.get("name") or loc_obj.get("address") or None

            url = ev.get("url") or None
            uid = ev.get("@id") or url or f"sv-{hash((title, start_s or '', url or ''))}"

            out.append({
                "uid": str(uid),
                "title": title,
                "start_utc": _dt_to_str(start_dt),
                "end_utc": _dt_to_str(end_dt),
                "url": url,
                "location": loc,
            })
    return out

def _parse_cards(soup: BeautifulSoup) -> List[Dict[str, Any]]:
    """
    Simpleview fallback for sites that render event lists server-side but
    without ld+json. Avoids capturing section headings by requiring a link.
    """
    events: List[Dict[str, Any]] = []
    seen = set()

    # Event card anchors commonly look like /event/<slug>/ or /events/<slug>/
    anchors = soup.select('a[href*="/event/"], a[href*="/events/"]')

    for a in anchors:
        title = a.get_text(strip=True) or ""
        href = a.get("href") or ""
        if not title or not href:
            continue
        # Skip obvious nav or heading links without a surrounding card
        if len(title.split()) < 2:
            continue

        # Climb a bit to find context
        container = a
        for _ in range(4):
            container = container.parent if container and container.parent else container

        # Try to find a date/time and a location near the anchor
        dt_text = None
        loc_text = None
        if container:
            for el in container.select("time, .date, .event-date, .sv-date, .listing-date"):
                txt = el.get_text(" ", strip=True)
                if txt and any(m in txt.lower() for m in ["jan","feb","mar","apr","may","jun","jul","aug","sep","oct","nov","dec"]):
                    dt_text = txt
                    break
            for el in container.select(".location, .venue, .event-location, .sv-venue, address"):
                txt = el.get_text(" ", strip=True)
                if txt and len(txt) > 3:
                    loc_text = txt
                    break

        start_dt = end_dt = None
        if dt_text:
            try:
                if " - " in dt_text:
                    left, right = dt_text.split(" - ", 1)
                    start_dt = dtp.parse(left, fuzzy=True)
                    try:
                        end_dt = dtp.parse(right, fuzzy=True, default=start_dt)
                    except Exception:
                        end_dt = None
                else:
                    start_dt = dtp.parse(dt_text, fuzzy=True)
            except Exception:
                start_dt = end_dt = None

        key = (title, href, _dt_to_str(start_dt))
        if key in seen:
            continue
        seen.add(key)

        events.append({
            "uid": f"sv-{hash(key)}",
            "title": title,
            "start_utc": _dt_to_str(start_dt),
            "end_utc": _dt_to_str(end_dt),
            "url": href,
            "location": loc_text,
        })

    return events

def fetch_simpleview_html(url: str, start_utc: str = None, end_utc: str = None) -> List[Dict[str, Any]]:
    """
    Let's Minocqua (Simpleview)
    Strategy:
      1) Prefer JSON-LD Event data.
      2) Fallback to card scraping while ignoring headings.
    """
    resp = get(url)
    soup = BeautifulSoup(resp.text, "html.parser")

    # JSON-LD first
    all_events: List[Dict[str, Any]] = []
    for s in soup.select('script[type="application/ld+json"]'):
        try:
            all_events.extend(_parse_ldjson(s.string or ""))
        except Exception:
            continue

    if not all_events:
        all_events = _parse_cards(soup)

    # Filter to entries that at least have a title and a plausible date if available
    clean = [e for e in all_events if e.get("title")]
    return clean
