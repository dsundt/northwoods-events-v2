# src/parsers/simpleview_html.py
from __future__ import annotations

import json
from typing import List, Dict, Optional
from datetime import datetime, timezone
import xml.etree.ElementTree as ET
import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "northwoods-events-bot/1.0 (+https://dsundt.github.io/northwoods-events-v2/)"
}

def _iso(dt: Optional[datetime]) -> Optional[str]:
    if not dt:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

def _fetch(url: str) -> requests.Response:
    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return r

def _jsonld_event(soup: BeautifulSoup) -> Optional[dict]:
    # Return the first JSON-LD Event block if present
    for tag in soup.find_all("script", attrs={"type": "application/ld+json"}):
        txt = (tag.string or tag.text or "").strip()
        if not txt:
            continue
        try:
            data = json.loads(txt)
        except Exception:
            continue
        blocks = data if isinstance(data, list) else [data]
        for b in blocks:
            if isinstance(b, dict) and b.get("@type") in ("Event", "MusicEvent"):
                return b
    return None

def _meta_datetime(soup: BeautifulSoup, itemprop: str) -> Optional[datetime]:
    m = soup.find("meta", attrs={"itemprop": itemprop})
    if m and m.get("content"):
        try:
            val = m["content"].strip()
            if "T" in val:
                dt = datetime.fromisoformat(val.replace("Z", "+00:00"))
            else:
                dt = datetime.strptime(val, "%Y-%m-%d")
            return dt.astimezone(timezone.utc) if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except Exception:
            return None
    return None

def _clean(s: Optional[str]) -> Optional[str]:
    if not s:
        return None
    return " ".join(s.split()).strip() or None

def _event_uid(prefix: str, url: str, title: str) -> str:
    return f"{prefix}-{abs(hash((url, title)))% (10**19)}"

def _scrape_event_page(link: str) -> Dict:
    start = end = None
    location = None
    title = None

    try:
        r = _fetch(link)
    except Exception:
        return {"title": None, "start": None, "end": None, "location": None}

    soup = BeautifulSoup(r.text, "html.parser")

    # Prefer JSON-LD Event
    ev = _jsonld_event(soup)
    if ev:
        title = _clean(ev.get("name")) or title
        start_iso = ev.get("startDate")
        end_iso = ev.get("endDate")
        try:
            if start_iso:
                start = datetime.fromisoformat(start_iso.replace("Z", "+00:00"))
                if start.tzinfo is None:
                    start = start.replace(tzinfo=timezone.utc)
        except Exception:
            start = None
        try:
            if end_iso:
                end = datetime.fromisoformat(end_iso.replace("Z", "+00:00"))
                if end.tzinfo is None:
                    end = end.replace(tzinfo=timezone.utc)
        except Exception:
            end = None

        loc = ev.get("location")
        if isinstance(loc, dict):
            location = _clean(loc.get("name") or loc.get("address"))
            if isinstance(location, dict):  # PostalAddress
                location = _clean(location.get("streetAddress") or location.get("addressLocality"))
        elif isinstance(loc, str):
            location = _clean(loc)

    # Meta fallbacks
    if not start:
        start = _meta_datetime(soup, "startDate")
    if not end:
        end = _meta_datetime(soup, "endDate")

    # Title/title fallback
    if not title:
        if soup.title and soup.title.string:
            title = _clean(soup.title.string)
    if not title:
        title = "Untitled"

    return {"title": title, "start": start, "end": end, "location": location}

def fetch_simpleview_html(url: str) -> List[Dict]:
    """
    Parse Simpleview RSS with stdlib XML, then enrich each item by scraping the event page.
    Returns a LIST of event dicts (no tuple).
    """
    resp = _fetch(url)
    # Some Simpleview feeds are not strict XML; be forgiving
    text = resp.text.strip()
    root = ET.fromstring(text)

    # Namespace-less RSS
    channel = root.find("channel") or root
    items = channel.findall("item")

    events: List[Dict] = []
    for it in items:
        link = (it.findtext("link") or "").strip()
        title = _clean(it.findtext("title"))

        # Enrich from event page JSON-LD/meta
        detail = _scrape_event_page(link) if link else {"title": title, "start": None, "end": None, "location": None}
        final_title = detail["title"] or title or "Untitled"

        ev = {
            "uid": _event_uid("sv", link, final_title),
            "title": final_title,
            "start_utc": _iso(detail["start"]),
            "end_utc": _iso(detail["end"]),
            "url": link or None,
            "location": detail["location"],
        }
        events.append(ev)

    return events
