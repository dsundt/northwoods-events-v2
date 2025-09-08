# src/parsers/simpleview_html.py
from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Iterable, List, Optional, Tuple
from urllib.parse import urljoin, urlparse, unquote

from bs4 import BeautifulSoup
from dateutil import parser as dp
import feedparser

from src.http import get
from src.models import Event


RANGE_SPLIT = re.compile(r"\s*[-–]\s*")


def _json_ld_event(soup: BeautifulSoup) -> Tuple[Optional[datetime], Optional[datetime], Optional[str], Optional[str]]:
    for s in soup.select('script[type="application/ld+json"]'):
        try:
            data = json.loads(s.string or "")
        except Exception:
            continue

        candidates = []
        if isinstance(data, dict):
            if data.get("@type") == "Event":
                candidates = [data]
            elif "@graph" in data and isinstance(data["@graph"], list):
                candidates = [x for x in data["@graph"] if isinstance(x, dict) and x.get("@type") == "Event"]
        elif isinstance(data, list):
            candidates = [x for x in data if isinstance(x, dict) and x.get("@type") == "Event"]

        for ev in candidates:
            start = ev.get("startDate")
            end = ev.get("endDate")
            loc = ev.get("location")
            loc_name = None
            if isinstance(loc, dict):
                loc_name = loc.get("name") or (isinstance(loc.get("address"), dict) and loc["address"].get("name"))
            elif isinstance(loc, str):
                loc_name = loc
            uid = ev.get("identifier") or ev.get("@id") or ev.get("url")
            return (dp.parse(start) if start else None, dp.parse(end) if end else None, loc_name, uid)
    return (None, None, None, None)


def _meta_dates(soup: BeautifulSoup) -> Tuple[Optional[datetime], Optional[datetime]]:
    # Some Simpleview themes publish itemprops
    start = soup.select_one('meta[itemprop="startDate"]')
    end = soup.select_one('meta[itemprop="endDate"]')
    s = dp.parse(start["content"]) if start and start.get("content") else None
    e = dp.parse(end["content"]) if end and end.get("content") else None
    return s, e


def _parse_text_dates(soup: BeautifulSoup) -> Tuple[Optional[datetime], Optional[datetime]]:
    # Scrape conspicuous date/value lines
    candidates = []
    for sel in [
        ".event-date", ".eventDates", ".event-details", ".details", ".event-info", ".event__meta",
        ".event-content", ".event-summary", ".event-information"
    ]:
        for blk in soup.select(sel):
            t = blk.get_text(" ", strip=True)
            if t and any(k in t.lower() for k in ["date", "dates", "time", "when"]):
                candidates.append(t)

    for txt in candidates:
        if RANGE_SPLIT.search(txt):
            parts = RANGE_SPLIT.split(txt)
            if len(parts) == 2:
                try:
                    return dp.parse(parts[0], fuzzy=True), dp.parse(parts[1], fuzzy=True)
                except Exception:
                    pass
        try:
            return dp.parse(txt, fuzzy=True), None
        except Exception:
            continue
    return None, None


def _venue_guess(soup: BeautifulSoup) -> Optional[str]:
    # Try common venue/address wrappers
    for sel in [
        ".venue-name", ".event-venue", ".location", ".event-location", ".address", ".eventMeta__location"
    ]:
        el = soup.select_one(sel)
        if el:
            txt = el.get_text(" ", strip=True)
            if txt:
                return txt
    # Fallback: first address-like block
    for el in soup.find_all(["address", "p", "div"]):
        txt = el.get_text(" ", strip=True)
        if txt and re.search(r"\d{3,5}\s+\w+", txt):
            return txt
    return None


def fetch_simpleview_html(source) -> Iterable[Event]:
    """
    Use RSS for discovery, then hydrate by visiting each detail page to
    collect canonical dates and venue.
    """
    feed_url = source.url
    if not feed_url.lower().endswith(".rss") and "/rss" not in feed_url.lower():
        # allow both .../event/rss and .../event/rss/
        if not feed_url.endswith("/"):
            feed_url += "/"
        feed_url = urljoin(feed_url, "")  # normalize

    fp = feedparser.parse(feed_url)
    events: List[Event] = []

    for entry in fp.entries:
        raw_url = entry.get("link") or entry.get("id") or ""
        url = unquote(raw_url)

        title = (entry.get("title") or "").strip() or "Untitled"
        # Fetch detail page
        try:
            r = get(url)
            r.raise_for_status()
            soup = BeautifulSoup(r.text, "html.parser")
        except Exception:
            # We still emit something, but without dates/location
            events.append(Event(
                uid=f"sv-{hash((title, url))}",
                title=title,
                start_utc=None,
                end_utc=None,
                url=url,
                location=None,
                source=source.name,
                calendar=source.name,
            ))
            continue

        s_dt, e_dt, venue, uid = _json_ld_event(soup)
        if not s_dt and not e_dt:
            s2, e2 = _meta_dates(soup)
            s_dt = s_dt or s2
            e_dt = e_dt or e2
        if not s_dt and not e_dt:
            s3, e3 = _parse_text_dates(soup)
            s_dt = s_dt or s3
            e_dt = e_dt or e3

        if not venue:
            venue = _venue_guess(soup)

        ev = Event(
            uid=str(uid or f"sv-{hash((title, s_dt.isoformat() if s_dt else 'na', url))}"),
            title=title,
            start_utc=s_dt,
            end_utc=e_dt,
            url=url,
            location=venue,
            source=source.name,
            calendar=source.name,
        )
        events.append(ev)

    return events
