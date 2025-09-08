# src/parsers/growthzone_html.py
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup
from dateutil import parser as dtp
from datetime import datetime
import json

from src.fetch import get

def _dtstr(dt: Optional[datetime]) -> Optional[str]:
    return dt.strftime("%Y-%m-%d %H:%M:%S") if dt else None

def _parse_ldjson(txt: str) -> List[Dict[str, Any]]:
    try:
        data = json.loads((txt or "").strip())
    except Exception:
        return []
    items = data if isinstance(data, list) else [data]
    out: List[Dict[str, Any]] = []
    for obj in items:
        if not isinstance(obj, dict):
            continue
        graphs = []
        if obj.get("@type") == "Event":
            graphs = [obj]
        elif isinstance(obj.get("@graph"), list):
            graphs = [x for x in obj["@graph"] if isinstance(x, dict) and x.get("@type") == "Event"]
        for ev in graphs:
            title = (ev.get("name") or "").strip()
            if not title:
                continue
            start_s = ev.get("startDate")
            end_s   = ev.get("endDate")
            try:
                start_dt = dtp.parse(start_s) if start_s else None
            except Exception:
                start_dt = None
            try:
                end_dt = dtp.parse(end_s) if end_s else None
            except Exception:
                end_dt = None

            loc = None
            loc_obj = ev.get("location")
            if isinstance(loc_obj, dict):
                loc = loc_obj.get("name") or loc_obj.get("address") or None

            url = ev.get("url") or None
            uid = ev.get("@id") or url or f"gz-{hash((title, start_s or '', url or ''))}"

            out.append({
                "uid": str(uid),
                "title": title,
                "start_utc": _dtstr(start_dt),
                "end_utc": _dtstr(end_dt),
                "url": url,
                "location": loc,
            })
    return out

def _parse_detail(url: str) -> List[Dict[str, Any]]:
    r = get(url)
    soup = BeautifulSoup(r.text, "html.parser")

    # Prefer JSON-LD
    events: List[Dict[str, Any]] = []
    for s in soup.select('script[type="application/ld+json"]'):
        events.extend(_parse_ldjson(s.string or ""))

    if events:
        return events

    # Fallback – scrape text on detail page
    title = (soup.select_one("h1, h2") or {}).get_text(strip=True) if soup else None

    # Dates – GrowthZone often renders a "Date and Time" block
    dt_text = None
    dt_el = soup.find(string=lambda x: isinstance(x, str) and "date" in x.lower())
    if dt_el:
        block = dt_el.parent
        if block:
            txt = block.get_text(" ", strip=True)
            if txt and any(m in txt.lower() for m in ["jan","feb","mar","apr","may","jun","jul","aug","sep","oct","nov","dec"]):
                dt_text = txt

    start_dt = end_dt = None
    if dt_text:
        try:
            if " - " in dt_text:
                left, right = dt_text.split(" - ", 1)
                start_dt = dtp.parse(left, fuzzy=True)
                try:
                    end_dt = dtp.parse(right, fuzzy=True, default=start_dt)
                except Exception:
                    end_dt = None
            else:
                start_dt = dtp.parse(dt_text, fuzzy=True)
        except Exception:
            start_dt = end_dt = None

    # Location block
    loc = None
    for sel in ["address", ".location", ".venue", ".event-location"]:
        el = soup.select_one(sel)
        if el:
            loc = el.get_text(" ", strip=True)
            if loc:
                break

    if title:
        return [{
            "uid": f"gz-{hash((title, _dtstr(start_dt) or '', url))}",
            "title": title,
            "start_utc": _dtstr(start_dt),
            "end_utc": _dtstr(end_dt),
            "url": url,
            "location": loc,
        }]
    return []

def fetch_growthzone_html(url: str, start_utc: str = None, end_utc: str = None) -> List[Dict[str, Any]]:
    # Calendar view: collect unique detail links, then parse each detail page
    r = get(url)
    soup = BeautifulSoup(r.text, "html.parser")

    links = set()
    for a in soup.select('a[href*="/events/details"], a[href*="/event/details"]'):
        href = a.get("href")
        if not href:
            continue
        # Make absolute if needed
        if href.startswith("/"):
            # derive site root from the calendar URL
            from urllib.parse import urljoin
            href = urljoin(url, href)
        links.add(href)

    events: List[Dict[str, Any]] = []
    for href in links:
        try:
            events.extend(_parse_detail(href))
        except Exception:
            # continue on individual failures
            continue

    # Keep only items with titles; dates are best-effort
    return [e for e in events if e.get("title")]
