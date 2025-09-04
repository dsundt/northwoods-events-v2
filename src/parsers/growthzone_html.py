from __future__ import annotations
from typing import List, Tuple, Dict, Any
from bs4 import BeautifulSoup
from src.fetch import get
from src.models import Event
from dateutil import parser as dtp


def fetch_growthzone_html(url: str, start_date, end_date) -> Tuple[List[Event], Dict[str, Any]]:
    resp = get(url)
    soup = BeautifulSoup(resp.content, "html.parser")
    evs: List[Event] = []
    diag: Dict[str, Any] = {}

    # GrowthZone calendar table/cards
    rows = soup.select("div.calendar-listing, div.calendarevent, li.event, article.event, .event-list .event")
    for r in rows:
        a = r.find("a", href=True)
        if not a:
            continue
        title = a.get_text(strip=True)
        href = a["href"]
        date_txt = r.get_text(" ", strip=True)
        start = _parse_date(date_txt)
        if not start:
            continue
        evs.append(Event(title=title, start_utc=start, url=href))

    return evs, diag


def _parse_date(text: str):
    try:
        return dtp.parse(text, fuzzy=True)
    except Exception:
        return None
