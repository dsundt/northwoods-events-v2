# src/parsers/simpleview_html.py
from __future__ import annotations
from datetime import datetime
from typing import Dict, List, Tuple
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from dateutil import parser as dtp
from src.fetch import get, session

def _first_jsonld_event(soup: BeautifulSoup):
    import json
    for script in soup.select('script[type="application/ld+json"]'):
        try:
            data = json.loads(script.string or "")
            items = data if isinstance(data, list) else [data]
            for it in items:
                if isinstance(it, dict) and it.get("@type") in ("Event", "MusicEvent", "Festival"):
                    return it
        except Exception:
            continue
    return None

def fetch_simpleview_html(src: Dict, start: datetime | None = None, end: datetime | None = None) -> Tuple[List[Dict], Dict]:
    """
    Parse Simpleview events (e.g., Minocqua). Accepts (src, start, end) to be compatible with main().
    Strategy: crawl listing page, follow item links, parse JSON-LD Event for dates.
    """
    base = src["url"].rstrip("/") + "/"
    s = session()
    resp = get(base, s=s, retries=1)
    soup = BeautifulSoup(resp.text, "html.parser")

    # Typical Simpleview anchors contain '/event/' or '/events/'
    anchors = soup.select('a[href*="/event/"], a[href*="/events/"]')
    seen = set()
    events: List[Dict] = []

    for a in anchors:
        href = a.get("href")
        if not href:
            continue
        url_abs = urljoin(base, href)
        if url_abs in seen:
            continue
        seen.add(url_abs)

        # Fetch detail page to get reliable dates (JSON-LD)
        try:
            d = get(url_abs, s=s, retries=1)
            dsoup = BeautifulSoup(d.text, "html.parser")
            j = _first_jsonld_event(dsoup)
        except Exception:
            j = None

        title = (a.get_text(strip=True) or (j.get("name") if j else None) or "(untitled)")
        start_utc = None
        end_utc = None
        if j:
            if j.get("startDate"):
                try:
                    start_utc = dtp.parse(j["startDate"]).strftime("%Y-%m-%d %H:%M:%S")
                except Exception:
                    pass
            if j.get("endDate"):
                try:
                    end_utc = dtp.parse(j["endDate"]).strftime("%Y-%m-%d %H:%M:%S")
                except Exception:
                    pass

        # Filter to requested window if both start/end were provided
        if start and end and start_utc:
            try:
                sdt = dtp.parse(start_utc)
                if sdt < start or sdt > end:
                    continue
            except Exception:
                pass

        # Location (if present in JSON-LD)
        loc = None
        if j and isinstance(j.get("location"), dict):
            loc = j["location"].get("name")

        events.append({
            "uid": f"sv-{hash(url_abs)}@northwoods-v2",
            "title": title,
            "start_utc": start_utc,
            "end_utc": end_utc,
            "url": url_abs,
            "location": loc,
            "source": src["name"],
            "calendar": src["name"],
        })

    diag = {"ok": bool(events), "error": "" if events else "No Simpleview events found", "diag": {"found": len(events)}}
    return events, diag
