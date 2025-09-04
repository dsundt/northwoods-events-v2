# src/parsers/simpleview_html.py

from __future__ import annotations

from typing import Dict, List, Set
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from dateutil import parser as dtp
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
        items = data if isinstance(data, list) else [data]
        for it in items:
            if isinstance(it, dict) and it.get("@type") in ("Event","MusicEvent","TheaterEvent","ExhibitionEvent"):
                out.append(it)
    return out

def _to_utc(s: str) -> str | None:
    try:
        return dtp.parse(s).isoformat()
    except Exception:
        return None

def _parse_detail(url: str, source_name: str) -> Dict | None:
    r = get(url)
    soup = BeautifulSoup(r.text, "html.parser")
    jl = _jsonld_events(soup)

    title = None
    start = end = None
    location = None

    # Prefer JSON-LD
    if jl:
        for it in jl:
            title = title or it.get("name")
            start = start or it.get("startDate")
            end = end or it.get("endDate")
            loc = it.get("location")
            if isinstance(loc, dict):
                location = location or loc.get("name") or loc.get("addressLocality")
    # Minimal fallbacks
    if not title:
        h = soup.select_one("h1, .event-title, .page-title")
        title = h.get_text(" ", strip=True) if h else None
    if not location:
        v = soup.select_one(".venue, .location, [itemprop='location']")
        location = v.get_text(" ", strip=True) if v else None

    if not start:
        # Try to find a date block with text
        dt_node = soup.select_one(".date, .event-date, .dates")
        if dt_node:
            try: start = dtp.parse(dt_node.get_text(" ", strip=True), fuzzy=True).isoformat()
            except Exception: pass
    if not end:
        end = start

    if not (title and start):
        return None

    return {
        "uid": f"{hash(url)}@northwoods-v2",
        "title": title,
        "start_utc": _to_utc(start),
        "end_utc": _to_utc(end) or _to_utc(start),
        "url": url,
        "location": location,
        "source": source_name,
        "calendar": source_name,
    }

def fetch_simpleview_html(source: Dict, start_date: str, end_date: str) -> List[Dict]:
    """
    Signature standardized as (source, start_date, end_date).
    Collect detail URLs from the listing, then parse each via JSON-LD.
    """
    base = source.get("url", "").strip()
    name = source.get("name") or source.get("id") or "Simpleview"
    if not base:
        return []

    r = get(base)
    soup = BeautifulSoup(r.text, "html.parser")

    links: Set[str] = set()
    # Simpleview detail URLs often contain /event/ or /events/
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if re.search(r"/event[s]?/", href, flags=re.I):
            links.add(urljoin(base, href))

    events: List[Dict] = []
    for href in list(links)[:150]:
        try:
            ev = _parse_detail(href, name)
            if ev and ev.get("start_utc"):
                events.append(ev)
        except Exception:
            continue

    return events
