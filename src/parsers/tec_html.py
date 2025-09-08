# src/parsers/tec_html.py
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from dateutil import parser as dtparse
from zoneinfo import ZoneInfo
import re

UA = "northwoods-events-bot/1.0 (+https://github.com/dsundt/northwoods-events-v2)"

def _soup(url: str) -> BeautifulSoup:
    r = requests.get(url, headers={"User-Agent": UA}, timeout=30)
    r.raise_for_status()
    return BeautifulSoup(r.text, "html.parser")

def _month_urls(base_url: str, start_date: datetime, end_date: datetime, cap: int = 6) -> List[str]:
    urls: List[str] = []
    cur = datetime(start_date.year, start_date.month, 1)
    last = datetime(end_date.year, end_date.month, 1)
    while cur <= last and len(urls) < cap:
        urls.append(f"{base_url.rstrip('/')}/?tribe-bar-date={cur.strftime('%Y-%m-%d')}")
        y = cur.year + (1 if cur.month == 12 else 0)
        m = 1 if cur.month == 12 else cur.month + 1
        cur = datetime(y, m, 1)
    return urls or [base_url]

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

def _pick_event_node(nodes: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    for n in nodes:
        t = n.get("@type")
        if isinstance(t, list):
            if any(str(x).lower() == "event" for x in t):
                return n
        elif isinstance(t, str) and t.lower() == "event":
            return n
    # Sometimes EventSeries is present; not reliable for one-off dates
    return None

def _parse_dt(val: Any, tz: ZoneInfo) -> Optional[str]:
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

def _discover_event_links(cal_soup: BeautifulSoup, base_url: str) -> List[str]:
    links = set()
    # List view titles
    for a in cal_soup.select("a.tribe-events-calendar-list__event-title-link, a.tribe-events-event-url"):
        href = a.get("href")
        if href:
            links.add(urljoin(base_url, href))
    # Month grid tiles
    for a in cal_soup.select(".tribe-events-calendar-month__calendar-event-title a, a.tribe-events-calendar-month__calendar-event-link"):
        href = a.get("href")
        if href:
            links.add(urljoin(base_url, href))
    # Card grid (some themes)
    for a in cal_soup.select("article.tribe-common-g-row a[href*='/event/']"):
        href = a.get("href")
        if href:
            links.add(urljoin(base_url, href))
    return sorted(links)

def _extract_dates_dom(soup: BeautifulSoup, tz: ZoneInfo) -> Tuple[Optional[str], Optional[str]]:
    # TEC often has <time class="tribe-events-c-datetime__start" datetime="...">
    st = soup.select_one("time.tribe-events-c-datetime__start, time.dt-start, time[itemprop='startDate']")
    et = soup.select_one("time.tribe-events-c-datetime__end, time.dt-end, time[itemprop='endDate']")
    s = _parse_dt(st.get("datetime") or st.get("content") if st else None, tz)
    e = _parse_dt(et.get("datetime") or et.get("content") if et else None, tz)
    if s or e:
        return s, e
    # last ditch: scan readable block
    blk = soup.select_one(".tribe-events-single-event-datetime, .tribe-events-c-datetime")
    if blk:
        text = blk.get_text(" ", strip=True)
        dates = re.findall(r"\w+\s+\d{1,2},\s*\d{4}(?:\s+\d{1,2}:\d{2}\s*(?:AM|PM))?", text, flags=re.I)
        if dates:
            s = s or _parse_dt(dates[0], tz)
            if len(dates) > 1:
                e = e or _parse_dt(dates[1], tz)
    return s, e

def _extract_location(soup: BeautifulSoup) -> Optional[str]:
    # Prefer venue group
    meta = soup.select_one(".tribe-events-meta-group--venue, .tribe-events-meta-group-details")
    if meta:
        text = meta.get_text("\n", strip=True)
        parts = [p.strip() for p in text.splitlines() if p.strip()]
        # Remove leading labels like "Venue" or "Location"
        while parts and re.match(r"^(venue|location)\s*:?$", parts[0], flags=re.I):
            parts.pop(0)
        return ", ".join(parts) if parts else None
    return None

def fetch_tec_html(source: Dict[str, Any], start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
    """
    St. Germain (TEC) via HTML:
    - Iterate month views (no REST, no ICS)
    - Pull JSON-LD Event when present; fallback to DOM for dates and venue
    """
    base_url = source["url"].rstrip("/")
    tz = ZoneInfo(source.get("timezone") or "America/Chicago")

    events: List[Dict[str, Any]] = []
    seen: set[str] = set()

    month_urls = _month_urls(base_url, start_date, end_date, cap=6)
    for murl in month_urls:
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

            # JSON-LD first
            node = None
            for tag in s.find_all("script", {"type": "application/ld+json"}):
                try:
                    data = json.loads(tag.string or "")
                except Exception:
                    continue
                nodes = _flatten_jsonld(data)
                node = _pick_event_node(nodes)
                if node:
                    break

            title = (node or {}).get("name")
            start_utc = _parse_dt((node or {}).get("startDate"), tz)
            end_utc   = _parse_dt((node or {}).get("endDate"), tz)

            if not start_utc and not end_utc:
                s2, e2 = _extract_dates_dom(s, tz)
                start_utc, end_utc = s2, e2

            # Location (JSON-LD venue if present)
            location = None
            loc = (node or {}).get("location")
            if isinstance(loc, dict):
                parts = [loc.get("name")]
                addr = loc.get("address")
                if isinstance(addr, dict):
                    for k in ("streetAddress", "addressLocality", "addressRegion"):
                        if addr.get(k):
                            parts.append(addr.get(k))
                location = ", ".join([p for p in parts if p])
            if not location:
                location = _extract_location(s)

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
