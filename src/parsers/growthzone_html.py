# src/parsers/growthzone_html.py

from __future__ import annotations

from typing import Dict, List, Set
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from dateutil import parser as dtp
from datetime import datetime
import json
import re

from src.fetch import get

def _jsonld_events(soup: BeautifulSoup) -> List[Dict]:
    out = []
    for tag in soup.find_all("script", {"type": "application/ld+json"}):
        try:
            data = json.loads(tag.string or tag.text or "")
        except Exception:
            continue
        # Normalize array vs object
        items = data if isinstance(data, list) else [data]
        for it in items:
            if isinstance(it, dict) and it.get("@type") in ("Event","MusicEvent","TheaterEvent","ExhibitionEvent"):
                out.append(it)
    return out

def _extract_dates_from_jsonld(items: List[Dict]) -> Dict[str,str]:
    start = end = None
    for it in items:
        start = start or it.get("startDate")
        end = end or it.get("endDate")
    return {"start": start, "end": end}

def _first_text(soup: BeautifulSoup, selectors: List[str]) -> str | None:
    for sel in selectors:
        n = soup.select_one(sel)
        if n:
            t = n.get_text(" ", strip=True)
            if t: return t
    return None

def _parse_event_detail(url: str, source_name: str) -> Dict | None:
    r = get(url)
    soup = BeautifulSoup(r.text, "html.parser")

    # JSON-LD first
    jl = _jsonld_events(soup)
    dates = _extract_dates_from_jsonld(jl)

    # Title
    title = _first_text(soup, [
        "h1", ".headline", ".page-title", ".event-title", ".details-title"
    ])

    # Location best-effort
    location = _first_text(soup, [
        "[itemprop='location'] [itemprop='name']",
        "[itemprop='location']",
        ".venue", ".location", ".event-venue"
    ])

    # Fallback date scraping if JSON-LD absent
    start = dates["start"]
    end = dates["end"]
    if not start:
        txt = _first_text(soup, [".event-date", ".date", ".dates", ".detail-date"])
        if txt:
            try: start = dtp.parse(txt, fuzzy=True).isoformat()
            except Exception: pass
    if not end and start:
        # Try derive duration window; GrowthZone often single-slot
        end = start

    if not (title and start):
        return None

    def to_utc_str(s):
        try:
            dt = dtp.parse(s)
            return dt.isoformat()
        except Exception:
            return None

    return {
        "uid": f"{hash(url)}@northwoods-v2",
        "title": title,
        "start_utc": to_utc_str(start),
        "end_utc": to_utc_str(end) or to_utc_str(start),
        "url": url,
        "location": location,
        "source": source_name,
        "calendar": source_name,
    }

def fetch_growthzone_html(source: Dict, start_date: str, end_date: str) -> List[Dict]:
    """
    Signature standardized as (source, start_date, end_date).
    Strategy: collect detail links from the list page, then parse each detail (JSON-LD first).
    """
    base = source.get("url", "").strip()
    name = source.get("name") or source.get("id") or "GrowthZone"
    if not base:
        return []

    r = get(base)
    soup = BeautifulSoup(r.text, "html.parser")

    # Collect detail links
    links: Set[str] = set()
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "/events/details/" in href or "/events/details" in href:
            links.add(urljoin(base, href))
        elif re.search(r"/event[s]?/details", href, flags=re.I):
            links.add(urljoin(base, href))

    # If no detail links were found, attempt to use list-items (some GrowthZone skins)
    if not links:
        for a in soup.select(".event-title a, .list-item a, .event a"):
            href = a.get("href")
            if href:
                links.add(urljoin(base, href))

    events: List[Dict] = []
    for href in list(links)[:120]:  # cap to keep runtime safe
        try:
            ev = _parse_event_detail(href, name)
            if ev and ev.get("start_utc"):
                events.append(ev)
        except Exception:
            # continue best-effort
            continue

    return events
