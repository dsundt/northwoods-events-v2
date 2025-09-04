# src/parsers/tec_html.py

from __future__ import annotations

from typing import Dict, List
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from dateutil import parser as dtp
from datetime import datetime
import json

from src.fetch import get
from src.parsers.tec_rest import fetch_tec_rest  # reuse the robust REST code

def _site_root(url: str) -> str:
    p = urlparse(url)
    return f"{p.scheme}://{p.netloc}/"

def _parse_html_list(url: str, source_name: str) -> List[Dict]:
    """
    Very generic HTML fallback for TEC list pages.
    Tries several common TEC list selectors; normalizes minimal fields.
    """
    events: List[Dict] = []
    r = get(url)
    soup = BeautifulSoup(r.text, "html.parser")

    # Common TEC list patterns
    candidates = []
    candidates += soup.select("article.type-tribe_events")
    candidates += soup.select(".tribe-events-calendar-list__event")
    candidates += soup.select("[data-tribe-event-id]")

    seen = set()
    for node in candidates:
        # Title + URL
        a = node.select_one("a.tribe-event-url, a.tribe-events-c-events-bar__event-title-link, h3 a, .tribe-events-calendar-list__event-title-link")
        title = (a.get_text(strip=True) if a else node.get_text(" ", strip=True)[:120])
        href = a["href"] if a and a.has_attr("href") else None

        # Dates (prefer <time datetime=...>)
        start_iso = None
        end_iso = None
        tstart = node.select_one("time[datetime]")
        if tstart and tstart.has_attr("datetime"):
            start_iso = tstart["datetime"]
        tend = node.select("time[datetime]")
        if len(tend) >= 2 and tend[1].has_attr("datetime"):
            end_iso = tend[1]["datetime"]

        # Fallbacks with text parsing
        if not start_iso:
            txt = " ".join(x.get_text(" ", strip=True) for x in node.select(".tribe-event-date-start, .tribe-events-calendar-list__event-date, .tribe-events-abbr"))
            if txt:
                try:
                    start_iso = dtp.parse(txt, fuzzy=True).isoformat()
                except Exception:
                    pass

        # Location (best-effort)
        loc = None
        locnode = node.select_one(".tribe-events-venue-details, .tribe-events-venue, .tribe-events-calendar-list__event-venue")
        if locnode:
            loc = locnode.get_text(" ", strip=True)

        uid = None
        if node.has_attr("data-tribe-event-id"):
            uid = f"{node['data-tribe-event-id']}@northwoods-v2"
        elif href:
            uid = f"{hash(href)}@northwoods-v2"

        if uid and uid in seen:
            continue
        seen.add(uid)

        # Normalize UTC-ish
        def to_utc_str(s):
            if not s: return None
            try:
                dt = dtp.parse(s)
                if not dt.tzinfo:
                    dt = dt.replace(tzinfo=None)
                return dt.isoformat().replace("+00:00", "")
            except Exception:
                return None

        start_utc = to_utc_str(start_iso)
        end_utc = to_utc_str(end_iso)

        if title and start_utc:
            events.append({
                "uid": uid or f"{len(events)}@northwoods-v2",
                "title": title,
                "start_utc": start_utc,
                "end_utc": end_utc,
                "url": href,
                "location": loc,
                "source": source_name,
                "calendar": source_name,
            })

    return events

def fetch_tec_html(source: Dict, start_date: str, end_date: str) -> List[Dict]:
    """
    Signature standardized as (source, start_date, end_date).

    Strategy:
    1) Attempt TEC REST at the site root (most TEC installs expose it).
    2) If REST yields no events, fall back to HTML list scraping on the provided URL.
    """
    src_name = source.get("name") or source.get("id") or "TEC"
    base_url = source.get("url", "").strip()
    if not base_url:
        return []

    # 1) Try REST at root
    try:
        rest_source = dict(source)
        rest_source["url"] = _site_root(base_url)
        rest_events = fetch_tec_rest(rest_source, start_date, end_date)
        if rest_events:
            return rest_events
    except Exception:
        # Swallow here; we’ll try HTML fallback next
        pass

    # 2) HTML fallback – try common list URL if caller gave a homepage
    if base_url.rstrip("/").endswith("/"):
        list_url = base_url.rstrip("/") + "/events/?eventDisplay=list"
    else:
        # If they already supplied a list page, just use it
        list_url = base_url

    try:
        return _parse_html_list(list_url, src_name)
    except Exception:
        return []
