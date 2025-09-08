# src/parsers/growthzone_html.py
from __future__ import annotations

import re
import json
from typing import Any, Dict, List, Optional
from datetime import datetime
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from dateutil import parser as dtparse
from zoneinfo import ZoneInfo

UA = "northwoods-events-bot/1.0 (+https://github.com/dsundt/northwoods-events-v2)"

def _soup(url: str) -> BeautifulSoup:
    r = requests.get(url, headers={"User-Agent": UA}, timeout=30)
    r.raise_for_status()
    return BeautifulSoup(r.text, "html.parser")

def _flatten_jsonld(obj: Any) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    if isinstance(obj, dict):
        if obj.get("@type"):
            out.append(obj)
        if "@graph" in obj and isinstance(obj["@graph"], list):
            for n in obj["@graph"]:
                if isinstance(n, dict):
                    out.append(n)
    elif isinstance(obj, list):
        for n in obj:
            if isinstance(n, dict):
                out.extend(_flatten_jsonld(n))
    return out

def _first_event_jsonld(soup: BeautifulSoup) -> Optional[Dict[str, Any]]:
    for tag in soup.find_all("script", {"type": "application/ld+json"}):
        raw = tag.string or ""
        try:
            data = json.loads(raw)
        except Exception:
            continue
        nodes = _flatten_jsonld(data)
        for node in nodes:
            t = str(node.get("@type", "")).lower()
            if t in ("event", "musicevent", "theaterevent", "sportsEvent".lower()):
                return node
            # GrowthZone sometimes labels ‘Event’ via additional types
            if isinstance(node.get("@type"), list) and any(str(x).lower() == "event" for x in node["@type"]):
                return node
    return None

def _parse_dt(val: Any, tz: ZoneInfo) -> Optional[str]:
    # val may be str or list[str]
    if isinstance(val, list) and val:
        val = val[0]
    if not val or not isinstance(val, str):
        return None
    try:
        dt = dtparse.parse(val)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=tz)
        return dt.astimezone(ZoneInfo("UTC")).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return None

def _extract_location_dom(soup: BeautifulSoup) -> Optional[str]:
    sec = soup.select_one("div.mn-event-section.mn-event-location div.mn-event-content")
    if not sec:
        return None
    candidate = sec.select_one("div.mn-raw.mn-print-url") or sec.select_one("[itemprop='name']")
    text = (candidate.get_text("\n", strip=True) if candidate else sec.get_text("\n", strip=True))
    text = re.sub(r"^\s*Location\s*:\s*", "", text, flags=re.I)
    parts = [p.strip() for p in re.split(r"[\r\n]+", text) if p.strip() and p.strip().lower() != "get directions"]
    return ", ".join(parts) if parts else None

def _extract_dates_dom(soup: BeautifulSoup, tz: ZoneInfo) -> (Optional[str], Optional[str]):
    # Prefer microdata <time itemprop="startDate" content="...">
    start_t = soup.select_one('time[itemprop="startDate"]')
    end_t   = soup.select_one('time[itemprop="endDate"]')
    start = _parse_dt(start_t.get("content") if start_t else None, tz)
    end   = _parse_dt(end_t.get("content") if end_t else None, tz)
    if start or end:
        return start, end
    # Fallback: parse readable “When” block under date/time section
    blk = soup.select_one("div.mn-event-section.mn-event-date-time") or soup.find(text=re.compile(r"\bWhen\b", re.I))
    if blk:
        text = blk.get_text(" ", strip=True) if hasattr(blk, "get_text") else str(blk)
        # Try first two date-like tokens
        dates = re.findall(r"\b(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)?\.?,?\s*\w+\s+\d{1,2},\s*\d{4}(?:\s+\d{1,2}:\d{2}\s*(?:AM|PM))?", text, flags=re.I)
        if dates:
            start = _parse_dt(dates[0], tz) or start
            if len(dates) > 1:
                end = _parse_dt(dates[1], tz) or end
    return start, end

def _discover_event_links(calendar_url: str, soup: BeautifulSoup) -> List[str]:
    links = set()
    for a in soup.select("a[href*='/events/details/']"):
        href = a.get("href") or ""
        links.add(urljoin(calendar_url, href))
    # Handle “More…” pagination if present
    for a in soup.select("a[href*='calendar?'][href*='p=']"):
        href = a.get("href") or ""
        links.add(urljoin(calendar_url, href))
    return sorted(links)

def fetch_growthzone_html(source: Dict[str, Any], start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
    """
    Rhinelander-specific hardening:
    - JSON-LD (preferred) for start/end
    - DOM fallback for dates when JSON-LD is missing
    - Location strictly from mn-event-location content block
    - Always returns a list
    """
    cal_url = source["url"].rstrip("/")
    tz = ZoneInfo(source.get("timezone") or "America/Chicago")

    events: List[Dict[str, Any]] = []
    try:
        cal_soup = _soup(cal_url)
    except Exception:
        return events

    detail_links = _discover_event_links(cal_url, cal_soup)
    seen = set()

    for url in detail_links:
        if url in seen:
            continue
        seen.add(url)
        try:
            s = _soup(url)
        except Exception:
            continue

        node = _first_event_jsonld(s) or {}
        title = (node.get("name") if isinstance(node, dict) else None) or None

        start_utc = _parse_dt((node or {}).get("startDate"), tz)
        end_utc   = _parse_dt((node or {}).get("endDate"), tz)
        if not start_utc and not end_utc:
            s2, e2 = _extract_dates_dom(s, tz)
            start_utc, end_utc = s2, e2

        # Location (only the requested block)
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
