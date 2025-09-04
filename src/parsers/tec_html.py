# src/parsers/tec_html.py
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Dict, Tuple
from urllib.parse import urljoin, urlparse
import re

import requests
from bs4 import BeautifulSoup
from dateutil import parser as dtparse


@dataclass
class Source:
    id: str
    name: str
    url: str
    type: str


USER_AGENT = "northwoods-events-v2 (+https://dsundt.github.io/northwoods-events-v2/)"


def _get(url: str, timeout: int = 30) -> requests.Response:
    return requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=timeout)


def _clean(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()


def _probe_listing(base_url: str) -> Tuple[str, BeautifulSoup]:
    """
    Try a handful of common TEC archive slugs and prefer list view.
    Returns (used_url, soup) for the first page that looks like TEC events.
    """
    base = base_url.rstrip("/")
    candidates = []

    # If caller already points at a TEC view, try it first (and list view variant)
    candidates.append(base)
    candidates.append(base + ("&" if "?" in base else "?") + "eventDisplay=list")

    # Common slugs across TEC installs
    common = [
        "/events/",
        "/events-calendar/",
        "/calendar/",
        "/whats-happening/events/",
    ]
    for c in common:
        u = urljoin(base + "/", c.lstrip("/"))
        candidates.append(u)
        candidates.append(u.rstrip("/") + "/?eventDisplay=list")
        candidates.append(u.rstrip("/") + "/?eventDisplay=list&page=all")

    tried = set()
    for u in candidates:
        if not u or u in tried:
            continue
        tried.add(u)
        try:
            r = _get(u)
            if r.status_code != 200:
                continue
            soup = BeautifulSoup(r.text, "html.parser")
            # Heuristics for TEC list view
            if soup.select(".tribe-events-calendar-list, .tribe-events-calendar-list__event, [data-js='tribe-events-view']"):
                return u, soup
        except Exception:
            continue

    # Fall back to original
    r = _get(base)
    r.raise_for_status()
    return base, BeautifulSoup(r.text, "html.parser")


def fetch_tec_html(src: Dict) -> Tuple[List[Dict], Dict]:
    """
    Parse The Events Calendar (TEC) HTML list views robustly, including sites
    that use custom slugs (e.g., /events-calendar/) and themes.
    """
    source = Source(
        id=src.get("id") or src["name"].lower().replace(" ", "-"),
        name=src["name"],
        url=src["url"],
        type=src["type"],
    )

    diag = {"source": source.id, "page_used": None, "notes": [], "count": 0}
    events: List[Dict] = []

    used_url, soup = _probe_listing(source.url)
    diag["page_used"] = used_url

    # Prefer modern TEC v6 list items
    items = soup.select(".tribe-events-calendar-list__event")
    if not items:
        # Older TEC selectors
        items = soup.select(".tribe-events-list-event, .tribe-event-list-item, article.type-tribe_events")

    # Last-resort generic WP loop entries (some themes wrap TEC differently)
    if not items:
        items = soup.select("article, li")  # broad
    seen = set()

    now = datetime.now(timezone.utc)

    for el in items:
        # Title + URL
        a = el.select_one("a.tribe-events-calendar-list__event-title-link") or el.select_one("h3 a, h2 a, .tribe-events-event-url")
        if not a:
            continue
        title = _clean(a.get_text())
        href = urljoin(used_url, a.get("href") or "")

        key = (title, href)
        if key in seen:
            continue
        seen.add(key)

        # Date/time
        # Modern TEC puts a <time> with datetime
        time_el = el.select_one("time[datetime]")
        start_dt = None
        if time_el and time_el.has_attr("datetime"):
            try:
                start_dt = dtparse.parse(time_el["datetime"])
            except Exception:
                start_dt = None

        if not start_dt:
            # Alternate spans commonly found in TEC
            txt = _clean(el.get_text(" ", strip=True))
            # Look for month name + day + year
            m = re.search(
                r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)\.?\s+\d{1,2},\s+\d{4}(?:\s+\d{1,2}:\d{2}\s*(AM|PM))?",
                txt,
                flags=re.IGNORECASE,
            )
            if m:
                try:
                    start_dt = dtparse.parse(m.group(0), fuzzy=True)
                except Exception:
                    start_dt = None

        if not start_dt:
            # If still unknown, skip — we don't want date-less entries
            diag["notes"].append(f"skip (no date): {title}")
            continue

        if start_dt.tzinfo is None:
            start_dt = start_dt.replace(tzinfo=timezone.utc)

        # Filter obviously old events
        if start_dt < now.replace(hour=0, minute=0, second=0, microsecond=0):
            continue

        ev = {
            "source_id": source.id,
            "title": title,
            "start": start_dt.isoformat(),
            "end": start_dt.isoformat(),
            "url": href,
            "location": None,
            "all_day": False,
        }
        events.append(ev)

    diag["count"] = len(events)
    return events, diag
