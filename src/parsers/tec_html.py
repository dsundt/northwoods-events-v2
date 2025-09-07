# src/parsers/tec_html.py
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup
from dateutil import parser as dtp
from datetime import datetime

from src.fetch import get

def _dt_to_str(dt: Optional[datetime]) -> Optional[str]:
    if not dt:
        return None
    return dt.strftime("%Y-%m-%d %H:%M:%S")

def fetch_tec_html(url: str, start_utc: str = None, end_utc: str = None) -> List[Dict[str, Any]]:
    """
    The Events Calendar (TEC) list page scraper.
    Use TEC REST where possible; use this only when REST is unavailable.
    Supports TEC v5/v6 list markup with flexible selectors.
    """
    resp = get(url)
    soup = BeautifulSoup(resp.text, "html.parser")

    events: List[Dict[str, Any]] = []

    # TEC v6 list: .tribe-events-calendar-list__event or data-event-id
    cards = soup.select(".tribe-events-calendar-list__event, [data-event-id]")
    if not cards:
        # Older/common list container
        cards = soup.select(".tribe-common-g-row, .tribe-events-list-event, article.type-tribe_events")

    for el in cards:
        # Title and link
        a = el.select_one("a.tribe-events-calendar-list__event-title-link, a.tribe-events-event-title, a[href*='/event/'], a[href*='/events/']")
        title = (a.get_text(strip=True) if a else "") or (el.get_text(strip=True)[:180] if el else "")
        href = a.get("href") if a else None

        # Datetime: try <time datetime="..."> first
        t_start = el.select_one("time.tribe-events-calendar-list__event-datetime, time[datetime]")
        start_dt = end_dt = None
        if t_start and t_start.has_attr("datetime"):
            try:
                start_dt = dtp.parse(t_start["datetime"])
            except Exception:
                start_dt = None

        # Try to find explicit end time (some themes put a second <time>)
        t_end = None
        if t_start:
            siblings = t_start.find_all_next("time", limit=2)
            if siblings:
                for s in siblings:
                    if s is not t_start and s.has_attr("datetime"):
                        try:
                            cand = dtp.parse(s["datetime"])
                            if not end_dt or cand > (end_dt or start_dt or cand):
                                end_dt = cand
                        except Exception:
                            continue

        # Fallback: parse any human-readable date string within the card
        if not start_dt:
            date_txt_el = el.select_one(".tribe-events-calendar-list__event-datetime, .tribe-event-date-start, .tribe-events-start-time, .tribe-events-schedule, .tribe-events-meta-group-details")
            if date_txt_el:
                txt = date_txt_el.get_text(" ", strip=True)
                try:
                    if " - " in txt:
                        left, right = txt.split(" - ", 1)
                        start_dt = dtp.parse(left, fuzzy=True)
                        try:
                            end_dt = dtp.parse(right, fuzzy=True, default=start_dt)
                        except Exception:
                            end_dt = None
                    else:
                        start_dt = dtp.parse(txt, fuzzy=True)
                except Exception:
                    start_dt = None

        # Location
        loc_el = el.select_one(".tribe-events-calendar-list__event-venue, .tribe-venue, .tribe-events-venue, .tribe-events-venue-details, .tribe-events-venue-details *")
        location = None
        if loc_el:
            location = loc_el.get_text(" ", strip=True) or None

        if not title and not href and not start_dt:
            # Skip empty shells
            continue

        events.append({
            "uid": f"tec-html-{hash((title, href or '', _dt_to_str(start_dt) or ''))}",
            "title": title or "Event",
            "start_utc": _dt_to_str(start_dt),
            "end_utc": _dt_to_str(end_dt),
            "url": href,
            "location": location,
        })

    return events
