from __future__ import annotations
from typing import List, Tuple, Dict, Any
from bs4 import BeautifulSoup
from dateutil import parser as dtp
from src.fetch import get
from src.models import Event


def fetch_simpleview_html(url: str, start_date, end_date) -> Tuple[List[Event], Dict[str, Any]]:
    resp = get(url)
    soup = BeautifulSoup(resp.content, "html.parser")
    evs: List[Event] = []
    diag: Dict[str, Any] = {}

    cards = soup.select(".l-event-list .c-card, .event-list .event, .event-card, li.event, article.event, .result-item, .tiles .tile")
    if not cards:
        cards = soup.find_all("a", href=True)

    for el in cards:
        link = el.select_one(".c-card__heading a, .event-title a, a[href*='/event/']")
        if not link and getattr(el, "name", "") == "a":
            link = el
        if not link:
            continue

        title = link.get_text(strip=True)
        href = link.get("href")

        # Try to get a parseable date from text/time tags
        start = None
        t = el.find("time")
        if t and t.has_attr("datetime"):
            try:
                start = dtp.parse(t["datetime"])
            except Exception:
                start = None
        if not start:
            txt = el.get_text(" ", strip=True)
            try:
                start = dtp.parse(txt, fuzzy=True)
            except Exception:
                start = None
        if not start:
            continue

        evs.append(Event(title=title or "(no title)", start_utc=start, url=href))

    return evs, diag
