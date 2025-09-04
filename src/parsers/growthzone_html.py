from __future__ import annotations
import datetime as dt
import re
from typing import Dict, Any, List, Tuple
import requests
from bs4 import BeautifulSoup

MONTHS_AHEAD = 3  # small, surgical crawl

def _month_iter(start: dt.date, months: int):
    y, m = start.year, start.month
    for _ in range(months):
        yield y, m
        m += 1
        if m > 12:
            m = 1
            y += 1

def _parse_month(html: str, source_label: str) -> List[Dict[str, Any]]:
    soup = BeautifulSoup(html, "html.parser")
    events: List[Dict[str, Any]] = []

    # GrowthZone calendar has anchor links per event; robustness: match event row anchors
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "/events/details/" in href or "/events/details/" in href.lower():
            title = a.get_text(strip=True)
            # try to pull datetime nearby
            cell = a.find_parent()
            when = ""
            # look for sibling text/date spans
            for sib in (cell or a).parent.find_all(["div", "span"], recursive=True):
                txt = sib.get_text(" ", strip=True)
                if re.search(r"\d{1,2}:\d{2}\s*(AM|PM)|\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\b", txt, re.I):
                    when = txt
                    break

            events.append({
                "uid": f"gz-{hash(href)}@northwoods-v2",
                "title": title,
                "start_utc": None,  # exact times require detail page; we keep lightweight
                "end_utc": None,
                "url": href if href.startswith("http") else requests.compat.urljoin("https://business.rhinelanderchamber.com", href),
                "location": None,
                "source": source_label,
                "calendar": source_label,
            })
    return events

def fetch_growthzone_html(base_url: str, start: dt.date, end: dt.date
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Crawl a few months of GrowthZone calendar list pages. If the calendar renders empty (what you've seen),
    we still return the diag with HTTP 200 but zero events, matching the behavior captured in report.json.
    """
    source_label = "Rhinelander Chamber (GrowthZone)"
    diag = {"months": []}
    all_events: List[Dict[str, Any]] = []
    ok = True
    error = ""

    try:
        for (y, m) in _month_iter(start, MONTHS_AHEAD):
            url = f"{base_url}?CalendarType=0&term=&from={y}-{m:02d}-01"
            resp = requests.get(url, timeout=30)
            resp.raise_for_status()
            month_events = _parse_month(resp.text, source_label)
            diag["months"].append({"month": f"{y}-{m:02d}", "count": len(month_events)})
            all_events.extend(month_events)
    except Exception as e:
        ok = False
        error = f"{type(e).__name__}: {e}"

    return all_events, {"ok": ok, "error": error, "diag": diag}
