# src/parsers/growthzone_html.py
# Surgical fix:
# - Update signature to (source, start_date, end_date) to stop TypeError.
# - Tolerant scraping of GrowthZone listings: collect detail links, then parse each detail page.
# - Keep it bounded (max 40 details) to avoid long GH Actions runs.

from __future__ import annotations
import re
from typing import List, Dict, Any
from urllib.parse import urljoin

from bs4 import BeautifulSoup  # type: ignore
from src.fetch import get

MAX_DETAIL_PAGES = 40

DATE_PAT = re.compile(
    r"(?P<mon>\w+)\s+(?P<day>\d{1,2})(?:,\s*(?P<year>\d{4}))?(?:\s+at\s+(?P<hour>\d{1,2}):(?P<min>\d{2})\s*(?P<ampm>AM|PM)?)?",
    re.IGNORECASE,
)

def _norm_space(s: str | None) -> str | None:
    return re.sub(r"\s+", " ", s).strip() if s else None

def _extract_dt_from_text(txt: str) -> str | None:
    """
    Parse a simple 'September 4, 2025 at 7:00 PM' into 'YYYY-MM-DD HH:MM:SS'.
    If year missing, we won't guess; return date-only if possible.
    """
    m = DATE_PAT.search(txt or "")
    if not m:
        return None
    mon = m.group("mon")
    day = m.group("day")
    year = m.group("year")
    hour = m.group("hour")
    minute = m.group("min")
    ampm = m.group("ampm")

    # Normalize month name
    try:
        from datetime import datetime
        if year:
            y = int(year)
        else:
            # if not present, leave as date-only in ISO with an arbitrary current year?
            # Safer: return as month-day only; but writer needs ISO. We'll return 'YYYY-MM-DD' using current year.
            y = datetime.utcnow().year

        mon_num = datetime.strptime(mon[:3], "%b").month if len(mon) >= 3 else datetime.strptime(mon, "%B").month

        if hour and minute and ampm:
            h = int(hour) % 12
            if ampm.upper() == "PM":
                h += 12
            return f"{y:04d}-{mon_num:02d}-{int(day):02d} {h:02d}:{int(minute):02d}:00"
        else:
            return f"{y:04d}-{mon_num:02d}-{int(day):02d}"
    except Exception:
        return None

def _parse_detail(url: str) -> Dict[str, Any]:
    resp = get(url)
    soup = BeautifulSoup(resp.text, "html.parser")

    # Title
    title_node = soup.select_one("h1, .gz-event-title, .event-title, .title")
    title = _norm_space(title_node.get_text()) if title_node else "Event"

    # Date/time: try microdata/time tags first
    t = soup.select_one("time[datetime]")
    if t and t.has_attr("datetime"):
        dt = (t["datetime"] or "").strip()
        start = dt.replace("T", " ").split("+")[0].split("Z")[0]
    else:
        # Fallback to searching common labels
        date_container = soup.find(string=re.compile(r"Date|When", re.I))
        start = None
        if date_container:
            start = _extract_dt_from_text(str(date_container.parent.get_text() if hasattr(date_container, "parent") else date_container))

    # Location
    loc_node = soup.select_one('[itemprop="location"], .location, .gz-event-location, .venue, .address')
    location = _norm_space(loc_node.get_text()) if loc_node else None

    return {
        "title": title or "Event",
        "url": url,
        "start_utc": start,
        "end_utc": None,
        "location": location,
    }

def fetch_growthzone_html(source: Dict[str, Any], start_date: str | None = None, end_date: str | None = None) -> List[Dict[str, Any]]:
    """
    Match main.py signature. Scrape listing for detail URLs, parse each detail page.
    """
    base = source.get("url") or ""
    if not base:
        return []

    # 1) Fetch listing page
    resp = get(base)
    soup = BeautifulSoup(resp.text, "html.parser")

    # 2) Find detail links
    links = []
    for a in soup.select('a[href*="/events/details/"], a[href*="/events/details?"]'):
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
            # best effort: skip bad detail pages
            continue

    return events
