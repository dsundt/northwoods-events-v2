# src/parsers/tec_html.py
from __future__ import annotations

import datetime as dt
from typing import List, Dict, Any, Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

def _fmt_dt_local(text: str) -> Optional[str]:
    """
    Best-effort: parse date/time fragments commonly found in TEC list HTML and
    normalize to "YYYY-MM-DD HH:MM:SS" in UTC if TZ can be inferred; otherwise keep local naive.
    """
    text = (text or "").strip()
    if not text:
        return None
    # Very defensive: try a few common formats
    fmts = [
        "%B %d @ %I:%M %p",     # "September 6 @ 10:00 am"
        "%B %d, %Y @ %I:%M %p", # "September 6, 2025 @ 10:00 am"
        "%Y-%m-%d %H:%M",
        "%B %d, %Y",
        "%Y-%m-%d",
    ]
    today_year = dt.datetime.utcnow().year
    for f in fmts:
        try:
            dt_obj = dt.datetime.strptime(text, f)
            # If no year provided, assume current or next year depending on month roll-over
            if "%Y" not in f:
                dt_obj = dt_obj.replace(year=today_year)
            return dt_obj.strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            continue
    return None

def fetch_tec_html(source: dict, start_date: str, end_date: str) -> List[Dict[str, Any]]:
    """
    HTML fallback for sites that do not expose (or block) TEC REST.
    Expects `source.url` to be a *list view* page like:
        https://oneidacountywi.com/festivals-events/?eventDisplay=list
        https://st-germain.com/events-calendar/?eventDisplay=list
    """
    url = source.get("url")
    name = source.get("name") or source.get("id") or "TEC HTML"
    if not url:
        return []

    out: List[Dict[str, Any]] = []
    page_url = url
    seen = set()

    # Crawl a few pages of list view (TEC uses ?eventDisplay=list&tribe_paged=2)
    for page in range(1, 5):
        resp = requests.get(page_url, timeout=30)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        cards = soup.select(".tribe-events-calendar-list__event, .tribe-common-g-row")
        if not cards:
            # Try legacy selectors
            cards = soup.select(".tribe-events-list-event, .tribe-events-calendar-list__event-row")
        for card in cards:
            # Title
            a = card.select_one("a.tribe-events-calendar-list__event-title-link, a.tribe-event-url, a.tribe-events-list-event-title, h3 a")
            title = (a.get_text(strip=True) if a else None) or "(untitled)"
            href = a.get("href") if a and a.has_attr("href") else None
            eid = href or title

            # Start/End
            start_el = card.select_one("[data-dtstart], time.tribe-event-date-start, time[datetime]")
            end_el = card.select_one("[data-dtend], time.tribe-event-date-end")
            start_text = start_el.get("datetime") if start_el and start_el.has_attr("datetime") else (start_el.get_text(" ", strip=True) if start_el else "")
            end_text = end_el.get("datetime") if end_el and end_el.has_attr("datetime") else (end_el.get_text(" ", strip=True) if end_el else "")

            start_norm = _fmt_dt_local(start_text)
            end_norm = _fmt_dt_local(end_text) if end_text else None

            # Location
            loc = None
            ven = card.select_one(".tribe-events-venue, .tribe-events-calendar-list__event-venue, .tribe-venue")
            if ven:
                loc = ven.get_text(" ", strip=True)

            uid = f"{eid}@northwoods-v2"
            if uid in seen:
                continue
            seen.add(uid)

            out.append({
                "uid": uid,
                "title": title,
                "start_utc": start_norm,
                "end_utc": end_norm,
                "url": href,
                "location": loc,
                "source": name,
                "calendar": name,
            })

        # Next page link
        next_link = soup.select_one("a.tribe-events-c-nav__next, a.tribe-events-nav-next, a.tribe-events-c-nav__next-link")
        if not next_link or not next_link.has_attr("href"):
            break
        page_url = urljoin(page_url, next_link["href"])

    return out
