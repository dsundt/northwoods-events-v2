# src/parsers/tec_html.py
from __future__ import annotations

from typing import Any, Dict, List, Optional
from datetime import datetime
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup
from dateutil import parser as dtparse
from zoneinfo import ZoneInfo
import json

UA = "northwoods-events-bot/1.0 (+https://github.com/dsundt/northwoods-events-v2)"

def _soup(url: str) -> BeautifulSoup:
    resp = requests.get(url, headers={"User-Agent": UA}, timeout=30)
    resp.raise_for_status()
    return BeautifulSoup(resp.text, "html.parser")

def _month_urls(base_url: str, start_date: datetime, end_date: datetime) -> List[str]:
    # TEC supports `?tribe-bar-date=YYYY-MM-01`
    urls: List[str] = []
    cur = datetime(start_date.year, start_date.month, 1)
    last = datetime(end_date.year, end_date.month, 1)
    while cur <= last and len(urls) < 6:  # safety cap
        urls.append(f"{base_url.rstrip('/')}/?tribe-bar-date={cur.strftime('%Y-%m-%d')}")
        # increment by one month
        y = cur.year + (1 if cur.month == 12 else 0)
        m = 1 if cur.month == 12 else cur.month + 1
        cur = datetime(y, m, 1)
    return urls or [base_url]

def _extract_jsonld_event(soup: BeautifulSoup) -> Optional[Dict[str, Any]]:
    for tag in soup.find_all("script", {"type": "application/ld+json"}):
        try:
            data = json.loads(tag.string or "")
        except Exception:
            continue
        if isinstance(data, dict) and data.get("@type") == "Event":
            return data
        if isinstance(data, list):
            for node in data:
                if isinstance(node, dict) and node.get("@type") == "Event":
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

def _discover_event_links(calendar_soup: BeautifulSoup, base_url: str) -> List[str]:
    links = set()
    # TEC list view
    for a in calendar_soup.select("a.tribe-events-calendar-list__event-title-link, a.tribe-events-event-url"):
        href = a.get("href")
        if href:
            links.add(urljoin(base_url, href))
    # TEC month grid view
    for a in calendar_soup.select(".tribe-events-calendar-month__calendar-event-title a, a.tribe-events-calendar-month__calendar-event-link"):
        href = a.get("href")
        if href:
            links.add(urljoin(base_url, href))
    return sorted(links)

def fetch_tec_html(source: Dict[str, Any], start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
    """
    HTML-based TEC parser (for St. Germain).
    Crawls month pages (using `?tribe-bar-date=`) and parses JSON-LD on each event page
    for authoritative start/end and venue. No ICS and no TEC REST calls.
    """
    base_url = source["url"].rstrip("/")
    tz = ZoneInfo(source.get("timezone") or "America/Chicago")

    events: List[Dict[str, Any]] = []
    seen = set()

    for murl in _month_urls(base_url, start_date, end_date):
        try:
            cal_soup = _soup(murl)
        except Exception:
            continue

        for link in _discover_event_links(cal_soup, base_url):
            if link in seen:
                continue
            seen.add(link)

            try:
                s = _soup(link)
            except Exception:
                continue

            node = _extract_jsonld_event(s) or {}
            title = node.get("name") if isinstance(node, dict) else None
            start_utc = _parse_dt(node.get("startDate") if isinstance(node, dict) else None, tz)
            end_utc   = _parse_dt(node.get("endDate") if isinstance(node, dict) else None, tz)

            # Location: prefer JSON-LD if present
            location = None
            loc = node.get("location") if isinstance(node, dict) else None
            if isinstance(loc, dict):
                parts = [loc.get("name")]
                addr = loc.get("address")
                if isinstance(addr, dict):
                    for k in ("streetAddress", "addressLocality", "addressRegion"):
                        if addr.get(k):
                            parts.append(addr.get(k))
                location = ", ".join([p for p in parts if p])

            if not location:
                # fallback: TEC venue meta group
                meta = s.select_one(".tribe-events-meta-group--venue, .tribe-events-meta-group-details")
                if meta:
                    text = meta.get_text("\n", strip=True)
                    location = ", ".join([p.strip() for p in text.splitlines() if p.strip()])

            uid = f"tec-{abs(hash((link, title or '')))}"
            events.append({
                "uid": uid,
                "title": title,
                "start_utc": start_utc,
                "end_utc": end_utc,
                "url": link,
                "location": location,
            })

    return events
