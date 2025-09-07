# src/parsers/growthzone_html.py
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup
from dateutil import parser as dtp
from datetime import datetime
import json

from src.fetch import get

TZ_HINT = None  # keep naive "YYYY-MM-DD HH:MM:SS" strings unless input provides tz

def _dt_to_str(dt: Optional[datetime]) -> Optional[str]:
    if not dt:
        return None
    # Normalize to "YYYY-MM-DD HH:MM:SS"
    return dt.strftime("%Y-%m-%d %H:%M:%S")

def _parse_event_ldjson(block: str) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    try:
        data = json.loads(block.strip())
    except Exception:
        return out

    items = data if isinstance(data, list) else [data]
    for obj in items:
        if not isinstance(obj, dict):
            continue
        # Accept Event or nested in @graph
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
            uid = ev.get("@id") or url or f"gz-{hash((title, start_s or '', url or ''))}"

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
    Generic GrowthZone/ChamberMaster list fallback.
    Tries to read card title, link, date string near card, and location.
    Works across a variety of site skins.
    """
    events: List[Dict[str, Any]] = []

    # Common anchors that look like event cards
    anchors = soup.select('a[href*="/events/details"], a[href*="/events/details/"], a[href*="/event/"], a[href*="Event?"]')
    seen = set()

    for a in anchors:
        url = a.get("href")
        title = (a.get_text(strip=True) or "")
        if not url or not title:
            continue
        key = (title, url)
        if key in seen:
            continue
        seen.add(key)

        # Try to find a date/time near the anchor
        container = a
        for _ in range(4):
            container = container.parent if container and container.parent else container
        date_text = None
        location = None

        # Common patterns
        cands = []
        if container:
            cands.extend(container.select(".date, .event-date, .mn-date, time, .gz-date, .cm_event_date"))
            cands.extend(container.select(".location, .event-location, .mn-location, .gz-location, .cm_event_location"))
        # Extract
        dt_str = None
        loc_str = None

        for el in cands:
            txt = el.get_text(" ", strip=True)
            if not txt:
                continue
            # Heuristic: first token with a month/day likely the date
            if not dt_str and any(m in txt.lower() for m in ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]):
                dt_str = txt
            # Heuristic: anything that looks like an address or venue
            if not loc_str and any(k in txt.lower() for k in ["st ", "street", "ave", "road", "rd", "center", "hall", "park", "library", "casino", "resort"]):
                loc_str = txt

        start_dt = end_dt = None
        if dt_str:
            # Extremely permissive parse; GrowthZone often uses "Mon, Sep 9, 2025 5:00 PM - 7:00 PM"
            try:
                # Try "start - end"
                if " - " in dt_str:
                    left, right = dt_str.split(" - ", 1)
                    start_dt = dtp.parse(left, fuzzy=True)
                    # end may be time-only
                    try:
                        end_dt = dtp.parse(right, fuzzy=True, default=start_dt)
                    except Exception:
                        end_dt = None
                else:
                    start_dt = dtp.parse(dt_str, fuzzy=True)
            except Exception:
                start_dt = end_dt = None

        events.append({
            "uid": f"gz-{hash((title, _dt_to_str(start_dt) or '', url))}",
            "title": title,
            "start_utc": _dt_to_str(start_dt),
            "end_utc": _dt_to_str(end_dt),
            "url": url,
            "location": loc_str,
        })

    return events

def fetch_growthzone_html(url: str, start_utc: str = None, end_utc: str = None) -> List[Dict[str, Any]]:
    """
    Rhinelander (GrowthZone / ChamberMaster)
    Strategy:
      1) Prefer any JSON-LD Event in the page.
      2) Fall back to flexible card scraping.
    """
    resp = get(url)
    soup = BeautifulSoup(resp.text, "html.parser")

    # JSON-LD first (most reliable)
    all_events: List[Dict[str, Any]] = []
    for s in soup.select('script[type="application/ld+json"]'):
        try:
            all_events.extend(_parse_event_ldjson(s.string or ""))
        except Exception:
            continue

    if not all_events:
        all_events = _parse_cards(soup)

    # Filter out entries without a title or date
    clean = [e for e in all_events if e.get("title")]
    return clean
