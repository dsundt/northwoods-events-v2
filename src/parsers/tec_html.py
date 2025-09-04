# src/parsers/tec_html.py
from __future__ import annotations
from datetime import datetime
from typing import Dict, List, Tuple
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from dateutil import parser as dtp
from src.fetch import get, session

def fetch_tec_html(src: Dict, start: datetime, end: datetime) -> Tuple[List[Dict], Dict]:
    """
    Parse TEC list view HTML (fallback when REST is unavailable).
    Tries common list endpoints: ?eventDisplay=list and ?tribe_event_display=list.
    """
    base = src["url"].rstrip("/") + "/"
    candidates = [
        urljoin(base, "events/?eventDisplay=list"),
        urljoin(base, "events/?tribe_event_display=list"),
    ]
    s = session()
    events: List[Dict] = []
    tried = []
    for url in candidates:
        tried.append(url)
        try:
            resp = get(url, s=s, retries=1)
        except Exception:
            continue
        soup = BeautifulSoup(resp.text, "html.parser")

        # TEC list items typically have class names with "tribe-events-calendar-list__event" or "tribe-common-event"
        items = soup.select(".tribe-events-calendar-list__event, .tribe-common-event")
        if not items:
            # Try generic anchors as last resort
            items = soup.select("a.tribe-events-calendar-list__event-title-link, a.tribe-event-url")

        for node in items:
            # title
            a = node.select_one("a[href]") or node if node.name == "a" else None
            title = (a.get_text(strip=True) if a else node.get_text(strip=True)) or "(untitled)"
            href = a["href"] if a and a.has_attr("href") else None
            url_abs = urljoin(base, href) if href else None

            # time — TEC includes <time datetime="...">
            t = node.select_one("time[datetime]") or soup.select_one("time[datetime]")
            start_utc = None
            end_utc = None
            if t and t.has_attr("datetime"):
                try:
                    dt = dtp.parse(t["datetime"])
                    start_utc = dt.strftime("%Y-%m-%d %H:%M:%S")
                except Exception:
                    pass

            loc = None
            loc_node = node.select_one(".tribe-events-venue, .tribe-events-calendar-list__event-venue, .tribe-events-address")
            if loc_node:
                loc = loc_node.get_text(" ", strip=True)

            events.append({
                "uid": f"tec-html-{hash(url_abs)}@northwoods-v2",
                "title": title,
                "start_utc": start_utc,
                "end_utc": end_utc,
                "url": url_abs,
                "location": loc,
                "source": src["name"],
                "calendar": src["name"],
            })

        # If we found anything, stop scanning
        if events:
            break

    diag = {"ok": bool(events), "error": "" if events else "No TEC HTML events found", "diag": {"tried": tried, "found": len(events)}}
    return events, diag
