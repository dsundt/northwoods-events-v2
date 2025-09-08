# src/parsers/tec_html.py
from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple, Union
from datetime import datetime
from zoneinfo import ZoneInfo
from urllib.parse import urljoin
import hashlib
import re
import requests
from bs4 import BeautifulSoup

UA = "Mozilla/5.0 (X11; Linux x86_64) NorthwoodsEventsBot/2.0 (+github actions)"
TZ = ZoneInfo("America/Chicago")

def _coerce_url(source: Union[str, Dict[str, Any]]) -> str:
    if isinstance(source, str):
        return source
    if isinstance(source, dict):
        # support either 'url' or 'calendar_url' keys if present
        return (source.get("url")
                or source.get("calendar_url")
                or "").strip()
    return str(source).strip()

def _get_html(url: str) -> str:
    r = requests.get(url, headers={"User-Agent": UA}, timeout=20)
    r.raise_for_status()
    return r.text

def _first(soup: BeautifulSoup, css: str):
    return soup.select_one(css)

def _text(el) -> str:
    if not el:
        return ""
    for br in el.select("br"):
        br.replace_with(", ")
    return " ".join(el.get_text(" ", strip=True).split())

def _to_utc_str(iso_like: Optional[str]) -> Optional[str]:
    if not iso_like:
        return None
    try:
        dt = datetime.fromisoformat(iso_like.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=TZ)
        return dt.astimezone(ZoneInfo("UTC")).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return None

def _extract_dates(soup: BeautifulSoup) -> Tuple[Optional[str], Optional[str]]:
    # Highest-fidelity paths first
    for sel_start in [
        'meta[itemprop="startDate"]',
        'time[itemprop="startDate"]',
        'time.tribe-events-start-date',
        'time.tribe-events-single-event-time',
    ]:
        m = soup.select_one(sel_start)
        if m:
            start_raw = m.get("content") or m.get("datetime")
            # paired end
            end_raw = None
            for sel_end in [
                'meta[itemprop="endDate"]',
                'time[itemprop="endDate"]',
                'time.tribe-events-end-date',
            ]:
                n = soup.select_one(sel_end)
                if n:
                    end_raw = n.get("content") or n.get("datetime")
                    break
            return _to_utc_str(start_raw), _to_utc_str(end_raw)

    # Fallback: search an ISO-ish token anywhere in body text (last resort)
    m = re.search(
        r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}[:\d{2}]*(?:[+-]\d{2}:\d{2}|Z)?)',
        soup.get_text(" ", strip=True),
    )
    if m:
        return _to_utc_str(m.group(1)), None
    return None, None

def _extract_location(soup: BeautifulSoup) -> Optional[str]:
    # Common TEC venue selectors
    for sel in [
        '[itemprop="location"] [itemprop="name"]',
        ".tribe-events-venue .tribe-venue",
        ".tribe-events-venue",
        ".tribe-venue",
    ]:
        t = _text(_first(soup, sel))
        if t:
            return t

    # Address pieces as fallback
    parts = []
    for sel in [".tribe-street-address", ".tribe-locality", ".tribe-region", ".tribe-postal-code"]:
        q = _first(soup, sel)
        if q:
            parts.append(_text(q))
    return ", ".join([p for p in parts if p]) if parts else None

def _uid(summary: str, url: str, start_utc: Optional[str]) -> str:
    base = f"{summary}|{url}|{start_utc or ''}".encode("utf-8")
    return "tec-" + hashlib.md5(base).hexdigest()

def fetch_tec_html(source: Union[str, Dict[str, Any]],
                   start_date: Optional[datetime] = None,
                   end_date: Optional[datetime] = None) -> List[Dict[str, Any]]:
    """
    St. Germain (TEC) — scrape the calendar page for event links,
    then open each detail page for reliable title/date/location.
    Accepts either a full source dict or a plain URL string.
    """
    cal_url = _coerce_url(source)
    if not cal_url:
        return []

    html = _get_html(cal_url)
    soup = BeautifulSoup(html, "html.parser")

    # Gather event links from multiple TEC list/month variants
    link_sel = ",".join([
        "a.tribe-events-calendar-list__event-title-link",
        "a.tribe-events-calendar-month__calendar-event-title-link",
        "a.tribe-event-url",
        'a[href*="/event/"]',
    ])
    seen = set()
    urls: List[str] = []
    for a in soup.select(link_sel):
        href = (a.get("href") or "").strip()
        if not href:
            continue
        u = urljoin(cal_url, href)
        if u not in seen:
            seen.add(u)
            urls.append(u)

    events: List[Dict[str, Any]] = []
    for u in urls:
        try:
            dhtml = _get_html(u)
            dsoup = BeautifulSoup(dhtml, "html.parser")

            title = _text(_first(dsoup, "h1, .tribe-events-single-event-title, .tribe-events-single-event-title__text"))
            if not title:
                og = _first(dsoup, 'meta[property="og:title"]')
                title = (og.get("content") if og else "") or "Untitled Event"

            start_utc, end_utc = _extract_dates(dsoup)
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
            # skip any bad detail page
            continue

    return events
