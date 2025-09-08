# src/parsers/tec_html.py
from __future__ import annotations
from typing import Any, Dict, List, Optional
from datetime import datetime
from zoneinfo import ZoneInfo
import hashlib
import re

import requests
from bs4 import BeautifulSoup

UA = "Mozilla/5.0 (X11; Linux x86_64) NorthwoodsEventsBot/2.0 (+github actions)"
TZ = ZoneInfo("America/Chicago")

def _get_html(url: str) -> str:
    r = requests.get(url, headers={"User-Agent": UA}, timeout=20)
    r.raise_for_status()
    return r.text

def _first(soup: BeautifulSoup, css: str):
    el = soup.select_one(css)
    return el

def _text(el) -> str:
    if not el:
        return ""
    # keep <br> as comma+space
    for br in el.select("br"):
        br.replace_with(", ")
    return " ".join(el.get_text(" ", strip=True).split())

def _parse_iso_local_to_utc(s: Optional[str]) -> Optional[str]:
    if not s:
        return None
    # TEC usually provides ISO in meta/time; let fromisoformat handle offsets if present.
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=TZ)
        return dt.astimezone(ZoneInfo("UTC")).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return None

def _extract_dates(soup: BeautifulSoup) -> (Optional[str], Optional[str]):
    # Prefer schema.org itemprops or time[datetime]
    for sel in [
        'meta[itemprop="startDate"]',
        'time[itemprop="startDate"]',
        'time.tribe-events-start-date',
        'time.tribe-events-single-event-time',
    ]:
        m = soup.select_one(sel)
        if m:
            start = m.get("content") or m.get("datetime")
            if start:
                # end?
                e = None
                for sel2 in ['meta[itemprop="endDate"]', 'time[itemprop="endDate"]', 'time.tribe-events-end-date']:
                    n = soup.select_one(sel2)
                    if n:
                        e = n.get("content") or n.get("datetime")
                        break
                return _parse_iso_local_to_utc(start), _parse_iso_local_to_utc(e)
    # Fallback: look for ISO-ish patterns in the HTML (last resort)
    m = re.search(r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}[:\d{2}]*(?:[+-]\d{2}:\d{2}|Z)?)', soup.get_text(" ", strip=True))
    if m:
        return _parse_iso_local_to_utc(m.group(1)), None
    return None, None

def _extract_location(soup: BeautifulSoup) -> Optional[str]:
    # Common TEC selectors
    for sel in [
        '[itemprop="location"] [itemprop="name"]',
        ".tribe-events-venue .tribe-venue",
        ".tribe-events-venue",
        ".tribe-venue",
    ]:
        t = _text(_first(soup, sel))
        if t:
            return t
    # Address lines
    parts = []
    for sel in [".tribe-street-address", ".tribe-locality", ".tribe-region", ".tribe-postal-code"]:
        q = _first(soup, sel)
        if q:
            parts.append(_text(q))
    if parts:
        return ", ".join([p for p in parts if p])
    return None

def _event_uid(summary: str, url: str, start_utc: Optional[str]) -> str:
    base = f"{summary}|{url}|{start_utc or ''}".encode("utf-8")
    return "tec-" + hashlib.md5(base).hexdigest()

def fetch_tec_html(source: Dict[str, Any],
                   start_date: Optional[datetime] = None,
                   end_date: Optional[datetime] = None) -> List[Dict[str, Any]]:
    """
    St. Germain: parse server-rendered TEC HTML (month or list view).
    We collect event links from the calendar page, then open each detail page
    to extract start/end + location reliably.
    """
    cal_url = source.get("url") or ""
    html = _get_html(cal_url)
    soup = BeautifulSoup(html, "html.parser")

    # Broad but safe set of link selectors across TEC variants
    link_sel = ",".join([
        "a.tribe-events-calendar-list__event-title-link",
        "a.tribe-events-calendar-month__calendar-event-title-link",
        "a.tribe-event-url",
        'a[href*="/event/"]',
    ])
    urls = []
    for a in soup.select(link_sel):
        href = (a.get("href") or "").strip()
        if href and href not in urls:
            urls.append(href)

    events: List[Dict[str, Any]] = []
    for u in urls:
        try:
            dhtml = _get_html(u)
            dsoup = BeautifulSoup(dhtml, "html.parser")
            title = _text(_first(dsoup, "h1, .tribe-events-single-event-title, .tribe-events-single-event-title__text"))
            if not title:
                # try og:title
                m = _first(dsoup, 'meta[property="og:title"]')
                title = (m.get("content") if m else "") or "Untitled Event"

            start_utc, end_utc = _extract_dates(dsoup)
            loc = _extract_location(dsoup)

            events.append({
                "uid": _event_uid(title, u, start_utc),
                "title": title,
                "start_utc": start_utc,
                "end_utc": end_utc,
                "url": u,
                "location": loc,
            })
        except Exception:
            # Skip bad detail pages; continue
            continue

    return events
