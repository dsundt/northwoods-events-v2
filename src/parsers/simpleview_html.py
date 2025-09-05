# src/parsers/growthzone_html.py
from __future__ import annotations

import datetime as dt
from typing import List, Dict, Any, Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

def _to_iso(dt_s: Optional[str]) -> Optional[str]:
    if not dt_s:
        return None
    dt_s = dt_s.strip()
    # GrowthZone often exposes ISO-ish strings in time/@datetime or data-* attrs
    try:
        d = dt.datetime.fromisoformat(dt_s.replace("Z", "+00:00"))
        return d.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return None

def fetch_growthzone_html(source: dict, start_date: str, end_date: str) -> List[Dict[str, Any]]:
    """
    Parse GrowthZone 'events' pages (e.g., https://business.rhinelanderchamber.com/events/).
    We look for cards with time elements or data attributes that provide start/end.
    """
    url = source.get("url")
    name = source.get("name") or source.get("id") or "GrowthZone"
    if not url:
        return []

    out: List[Dict[str, Any]] = []
    page_url = url
    seen = set()

    # Crawl a few pages by following "Next" if present
    for page in range(1, 5):
        resp = requests.get(page_url, timeout=30)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        cards = soup.select("[itemtype*='Event'], .gz-event, .chamber-master-event, .card")
        if not cards:
            cards = soup.select(".event, .event-list-item")

        for c in cards:
            # Title + link
            a = c.select_one("a[href*='/events/'], a.event-title, h3 a, .card-title a")
            title = (a.get_text(strip=True) if a else None) or c.select_one("h3, h4")
            title = title.get_text(strip=True) if hasattr(title, "get_text") else (title or "(untitled)")
            href = a.get("href") if a and a.has_attr("href") else None
            href = urljoin(page_url, href) if href else None
            eid = href or title

            # Datetimes
            start = None
            end = None
            # Prefer <time datetime="...">
            t_start = c.select_one("time[datetime]")
            if t_start and t_start.has_attr("datetime"):
                start = _to_iso(t_start["datetime"])
            t_end = c.select_one("time[datetime].end, time.end")
            if t_end and t_end.has_attr("datetime"):
                end = _to_iso(t_end["datetime"])

            # Fallback: GrowthZone sometimes uses data-* on container
            if not start:
                for attr in ("data-start", "data-startdate", "data-start-time", "data-begin"):
                    if c.has_attr(attr):
                        start = _to_iso(c[attr])
                        if start:
                            break
            if not end:
                for attr in ("data-end", "data-enddate", "data-end-time", "data-finish"):
                    if c.has_attr(attr):
                        end = _to_iso(c[attr])
                        if end:
                            break

            # Location
            loc = None
            loc_el = c.select_one("[itemprop='location'], .location, .event-location, .card-subtitle")
            if loc_el:
                loc = loc_el.get_text(" ", strip=True)

            uid = f"{eid}@northwoods-v2"
            if uid in seen:
                continue
            seen.add(uid)

            out.append({
                "uid": uid,
                "title": title,
                "start_utc": start,
                "end_utc": end,
                "url": href,
                "location": loc,
                "source": name,
                "calendar": name,
            })

        # Next page?
        next_link = soup.find("a", string=lambda s: s and s.strip().lower().startswith("next"))
        if not next_link or not next_link.has_attr("href"):
            break
        page_url = urljoin(page_url, next_link["href"])

    return out
