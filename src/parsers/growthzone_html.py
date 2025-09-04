from __future__ import annotations
from typing import List, Tuple
from datetime import date
from dateutil.relativedelta import relativedelta
from bs4 import BeautifulSoup

from src.fetch import get
from src.util import absurl, parse_first_jsonld_event, sanitize_event

def _month_iter(start: date, months: int) -> List[date]:
    return [start + relativedelta(months=+i) for i in range(months)]

def _render_month_url(base_calendar_url: str, d: date) -> str:
    # GrowthZone usually supports month navigation via query params or anchor. A robust approach:
    # try appending ?m=YYYY-MM-01 (if not supported, the page still returns the current month).
    return f"{base_calendar_url}?m={d.strftime('%Y-%m-01')}"

def fetch_growthzone_html(source: dict, start_iso: str, end_iso: str) -> Tuple[List[dict], dict]:
    months = int(source.get("months_ahead", 3))
    diag = {"months": months, "pages": 0, "detail_hits": 0}
    # 1) Crawl month views to get event detail links
    links: List[str] = []
    for d in _month_iter(date.today().replace(day=1), months):
        url = _render_month_url(source["url"], d)
        resp = get(url)
        soup = BeautifulSoup(resp.text, "html.parser")
        diag["pages"] += 1
        # Typical GrowthZone selectors for calendar/event list:
        for a in soup.select("a.calendarEventLink, a.eventItemLink, a[href*='/events/details/']"):
            href = a.get("href")
            if href:
                links.append(absurl(url, href))
    links = list(dict.fromkeys(links))
    # 2) Visit details and parse JSON-LD when available
    items: List[dict] = []
    for href in links:
        try:
            r = get(href)
            soup = BeautifulSoup(r.text, "html.parser")
            j = parse_first_jsonld_event(soup, href)
            if j:
                diag["detail_hits"] += 1
                norm = sanitize_event(j, source["name"], source["name"])
                if norm:
                    items.append(norm)
        except Exception:
            continue
    return items, diag
