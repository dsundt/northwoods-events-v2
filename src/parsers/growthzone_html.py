# src/parsers/growthzone_html.py
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional
from datetime import datetime
import requests
from bs4 import BeautifulSoup
from dateutil import parser as dtparse
from zoneinfo import ZoneInfo
import json
from urllib.parse import urljoin

UA = "northwoods-events-bot/1.0 (+https://github.com/dsundt/northwoods-events-v2)"

def _soup(url: str) -> BeautifulSoup:
    resp = requests.get(url, headers={"User-Agent": UA}, timeout=30)
    resp.raise_for_status()
    return BeautifulSoup(resp.text, "html.parser")

def _jsonld_event(soup: BeautifulSoup) -> Optional[Dict[str, Any]]:
    # GrowthZone usually embeds JSON-LD with @type Event on detail pages.
    for tag in soup.find_all("script", {"type": "application/ld+json"}):
        try:
            data = json.loads(tag.string or "")
        except Exception:
            continue
        if isinstance(data, dict) and data.get("@type") in ("Event", "event"):
            return data
        if isinstance(data, list):
            for node in data:
                if isinstance(node, dict) and node.get("@type") in ("Event", "event"):
                    return node
    return None

def _parse_dt(val: Optional[str], tz: ZoneInfo) -> Optional[str]:
    if not val:
        return None
    try:
        dt = dtparse.parse(val)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=tz)
        dt_utc = dt.astimezone(ZoneInfo("UTC"))
        return dt_utc.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return None

def _extract_location_dom(soup: BeautifulSoup) -> Optional[str]:
    """
    ONLY return the human-entered location block under:
      div.mn-event-section.mn-event-location > div.mn-event-content > (div.mn-raw.mn-print-url or text)
    Strip any 'Location:' label and collapse line breaks to a tidy single line.
    """
    sec = soup.select_one("div.mn-event-section.mn-event-location div.mn-event-content")
    if not sec:
        return None
    inner = sec.select_one("div.mn-raw.mn-print-url") or sec.select_one("[itemprop='name']")
    text = (inner.get_text("\n", strip=True) if inner else sec.get_text("\n", strip=True))
    # Guarantee we never render the label itself:
    text = re.sub(r"^\s*Location\s*:\s*", "", text, flags=re.I)
    # Remove stray helper text like "Get Directions" if present
    parts = [p.strip() for p in re.split(r"[\r\n]+", text) if p.strip() and p.strip().lower() != "get directions"]
    return ", ".join(parts) if parts else None

def _discover_event_links(calendar_url: str, soup: BeautifulSoup) -> List[str]:
    links = set()
    for a in soup.select("a[href*='/events/details/']"):
        href = a.get("href") or ""
        links.add(urljoin(calendar_url, href))
    return sorted(links)

def fetch_growthzone_html(source: Dict[str, Any], start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
    """
    GrowthZone HTML fetcher focused on Rhinelander fixes:
    - Dates via JSON-LD on the detail page (what's already working)
    - Location strictly from the mn-event-location section (no page-wide bleed)
    - Returns a LIST to avoid 'returned non-list' errors
    """
    cal_url = source["url"].rstrip("/")
    tz = ZoneInfo(source.get("timezone") or "America/Chicago")

    cal_soup = _soup(cal_url)
    detail_links = _discover_event_links(cal_url, cal_soup)

    events: List[Dict[str, Any]] = []
    for url in detail_links:
        try:
            s = _soup(url)
        except Exception:
            continue

        node = _jsonld_event(s) or {}
        title = node.get("name") if isinstance(node, dict) else None
        start_utc = _parse_dt(node.get("startDate") if isinstance(node, dict) else None, tz)
        end_utc   = _parse_dt(node.get("endDate") if isinstance(node, dict) else None, tz)

        # Only the location block requested
        location = _extract_location_dom(s)

        uid = f"gz-{abs(hash((url, title or '')))}"
        events.append({
            "uid": uid,
            "title": title,
            "start_utc": start_utc,
            "end_utc": end_utc,
            "url": url,
            "location": location,
        })

    return events
