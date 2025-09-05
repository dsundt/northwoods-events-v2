# src/parsers/simpleview_html.py
from __future__ import annotations

import datetime as dt
from typing import List, Dict, Any, Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

def _iso(s: Optional[str]) -> Optional[str]:
    if not s:
        return None
    try:
        d = dt.datetime.fromisoformat(s.replace("Z", "+00:00"))
        return d.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return None

def fetch_simpleview_html(source: dict, start_date: str, end_date: str) -> List[Dict[str, Any]]:
    """
    Parse Simpleview event listings (e.g., https://www.minocqua.org/events/).
    Looks for schema.org or meta[itemprop] with startDate/endDate; falls back to known classes.
    """
    url = source.get("url")
    name = source.get("name") or source.get("id") or "Simpleview"
    if not url:
        return []

    out: List[Dict[str, Any]] = []
    page_url = url
    seen = set()

    for page in range(1, 5):
        resp = requests.get(page_url, timeout=30)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        cards = soup.select("[itemtype*='Event'], .sv-event-card, .event-details, .listing")
        if not cards:
            cards = soup.select(".event, .entry, article")

        for c in cards:
            # Title/link
            a = c.select_one("a[href*='/event/'], a[href*='/events/'], h3 a, .card-title a")
            title = (a.get_text(strip=True) if a else None) or c.select_one("h3, h2")
            title = title.get_text(strip=True) if hasattr(title, "get_text") else (title or "(untitled)")
            href = a.get("href") if a and a.has_attr("href") else None
            href = urljoin(page_url, href) if href else None
            eid = href or title

            # Datetimes via schema.org
            s_meta = c.select_one("meta[itemprop='startDate']")
            e_meta = c.select_one("meta[itemprop='endDate']")
            start = _iso(s_meta.get("content")) if s_meta and s_meta.has_attr("content") else None
            end = _iso(e_meta.get("content")) if e_meta and e_meta.has_attr("content") else None

            # Other hints
            if not start:
                t = c.select_one("time[datetime]")
                if t and t.has_attr("datetime"):
                    start = _iso(t["datetime"])

            # Location
            loc = None
            loc_el = c.select_one("[itemprop='location'], .location, .event-location, .sv-event-venue")
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
        nxt = soup.find("a", attrs={"rel": "next"})
        if not nxt or not nxt.has_attr("href"):
            break
        page_url = urljoin(page_url, nxt["href"])

    return out
