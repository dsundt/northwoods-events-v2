# src/parsers/growthzone_html.py
from __future__ import annotations
from typing import Any, Dict, List, Optional
from datetime import datetime
from zoneinfo import ZoneInfo
import hashlib
import requests
from bs4 import BeautifulSoup

UA = "Mozilla/5.0 (X11; Linux x86_64) NorthwoodsEventsBot/2.0 (+github actions)"
TZ = ZoneInfo("America/Chicago")

def _get_html(url: str) -> str:
    r = requests.get(url, headers={"User-Agent": UA}, timeout=20)
    r.raise_for_status()
    return r.text

def _text_keep_br(el) -> str:
    if not el:
        return ""
    for br in el.select("br"):
        br.replace_with(", ")
    return " ".join(el.get_text(" ", strip=True).split())

def _to_utc_str(iso: Optional[str]) -> Optional[str]:
    if not iso:
        return None
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=TZ)
        return dt.astimezone(ZoneInfo("UTC")).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return None

def _extract_dates(soup: BeautifulSoup):
    # GrowthZone detail pages typically expose schema.org time/itemprop
    start = None
    end = None
    n = soup.select_one('meta[itemprop="startDate"], time[itemprop="startDate"]')
    if n:
        start = n.get("content") or n.get("datetime")
    n2 = soup.select_one('meta[itemprop="endDate"], time[itemprop="endDate"]')
    if n2:
        end = n2.get("content") or n2.get("datetime")
    return _to_utc_str(start), _to_utc_str(end)

def _extract_location(soup: BeautifulSoup) -> Optional[str]:
    # EXACTLY the requested scope: div.mn-event-section.mn-event-location .mn-event-content
    block = soup.select_one("div.mn-event-section.mn-event-location div.mn-event-content")
    if not block:
        return None
    raw = block.select_one(".mn-raw")
    if raw:
        return _text_keep_br(raw)
    return _text_keep_br(block)

def _uid(title: str, url: str, start_utc: Optional[str]) -> str:
    key = f"{title}|{url}|{start_utc or ''}".encode("utf-8")
    return "gz-" + hashlib.md5(key).hexdigest()

def fetch_growthzone_html(source: Dict[str, Any],
                          start_date: Optional[datetime] = None,
                          end_date: Optional[datetime] = None) -> List[Dict[str, Any]]:
    """
    Rhinelander: crawl calendar page for detail links, then parse each detail page
    for true dates and the specific location block requested.
    """
    cal_url = source.get("url") or ""
    html = _get_html(cal_url)
    soup = BeautifulSoup(html, "html.parser")

    # Collect detail links
    links = []
    for a in soup.select('a[href*="/events/details/"]'):
        href = (a.get("href") or "").strip()
        if href and href not in links:
            links.append(href)

    events: List[Dict[str, Any]] = []
    for u in links:
        try:
            dhtml = _get_html(u)
            dsoup = BeautifulSoup(dhtml, "html.parser")

            # Title
            title = None
            h1 = dsoup.select_one("h1, .mn-event-title")
            if h1:
                title = " ".join(h1.get_text(" ", strip=True).split())
            if not title:
                og = dsoup.select_one('meta[property="og:title"]')
                title = (og.get("content") if og else "") or "Untitled Event"

            # Dates
            start_utc, end_utc = _extract_dates(dsoup)

            # Location (STRICT block only; no "Location:" label leakage)
            location = _extract_location(dsoup)

            events.append({
                "uid": _uid(title, u, start_utc),
                "title": title,
                "start_utc": start_utc,
                "end_utc": end_utc,
                "url": u,
                "location": location,
            })
        except Exception:
            continue

    return events
