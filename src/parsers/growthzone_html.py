# src/parsers/growthzone_html.py
# DROP-IN REPLACEMENT — robust GrowthZone parser
#
# Public API (unchanged):
#   fetch_growthzone_html(source: dict, start_date, end_date) -> (events: list[dict], diag: dict)
#
# Notes:
# - Pulls the listing URL from source["url"] (prevents InvalidSchema).
# - First tries JSON-LD (schema.org/Event), then falls back to common GrowthZone HTML.
# - Returns events with "start"/"end" as datetime (UTC); location/title/url filled.
# - main.py should be doing final normalization/serialization to strings for report.json and ICS.

from __future__ import annotations

import json
import re
from datetime import datetime, date, time
from typing import List, Dict, Tuple, Optional

import requests
from bs4 import BeautifulSoup
from dateutil import parser as dtparser
from dateutil import tz

UTC = tz.UTC
LOCAL_TZ = tz.gettz("America/Chicago")

def _coerce_date(d) -> date:
    if isinstance(d, date) and not isinstance(d, datetime):
        return d
    if isinstance(d, datetime):
        return d.date()
    return dtparser.isoparse(str(d)).date()

def _to_utc(dtobj: datetime) -> datetime:
    if isinstance(dtobj, date) and not isinstance(dtobj, datetime):
        dtobj = datetime.combine(dtobj, time(0, 0))
    if dtobj.tzinfo is None:
        dtobj = dtobj.replace(tzinfo=LOCAL_TZ)
    return dtobj.astimezone(UTC)

def _within_window(start_utc: datetime, end_utc: Optional[datetime], sd: date, ed: date) -> bool:
    ws = datetime.combine(sd, time(0, 0, tzinfo=UTC))
    we = datetime.combine(ed, time(23, 59, 59, tzinfo=UTC))
    s = start_utc
    e = end_utc or start_utc
    return not (e < ws or s > we)

def _get(url: str, timeout: int = 25) -> requests.Response:
    resp = requests.get(url, headers={"User-Agent": "northwoods-v2/1.0"}, timeout=timeout)
    resp.raise_for_status()
    return resp

def _jsonld_events(soup: BeautifulSoup) -> List[Dict]:
    out: List[Dict] = []
    for tag in soup.find_all("script", {"type": "application/ld+json"}):
        try:
            data = json.loads(tag.string.strip()) if tag.string else None
        except Exception:
            continue
        if not data:
            continue

        items = data if isinstance(data, list) else [data]
        for item in items:
            typ = (item.get("@type") or "").lower()
            if typ == "event" or (isinstance(item.get("@type"), list) and "Event" in item.get("@type")):
                out.append(item)
            # Some GrowthZone pages wrap events in an ItemList
            if (item.get("@type") == "ItemList") and "itemListElement" in item:
                for el in item.get("itemListElement") or []:
                    ev = el.get("item") if isinstance(el, dict) else None
                    if isinstance(ev, dict) and (ev.get("@type") == "Event"):
                        out.append(ev)
    return out

def _parse_jsonld_event(ev: Dict) -> Dict:
    name = (ev.get("name") or "").strip()
    url = (ev.get("url") or "").strip() or None
    # startDate / endDate may be ISO strings
    s_raw = ev.get("startDate")
    e_raw = ev.get("endDate")

    start_utc = _to_utc(dtparser.isoparse(s_raw)) if s_raw else None
    end_utc = _to_utc(dtparser.isoparse(e_raw)) if e_raw else None

    loc = None
    loc_obj = ev.get("location")
    if isinstance(loc_obj, dict):
        loc = (loc_obj.get("name") or "").strip() or None
        if not loc:
            addr = loc_obj.get("address")
            if isinstance(addr, dict):
                parts = [addr.get(k) for k in ("streetAddress", "addressLocality", "addressRegion")]
                loc = ", ".join([p for p in parts if p]) or None
    elif isinstance(loc_obj, str):
        loc = loc_obj.strip() or None

    return {
        "id": ("gz-" + str(abs(hash(f"{name}|{s_raw}|{url or ''}")))) if name or s_raw else None,
        "title": name or url or "Event",
        "start": start_utc,
        "end": end_utc,
        "location": loc,
        "url": url,
        "tz": "UTC",
    }

# Fallback HTML selectors (common GrowthZone patterns)
_CARD_SEL = ".gz-event, .event, .card, .events-list .item, .EventList .EventList-item"

def _html_events(soup: BeautifulSoup) -> List[Dict]:
    out: List[Dict] = []

    # Try explicit time tags first
    for el in soup.select(_CARD_SEL):
        title_el = el.select_one("a, h3, .title, .event-title")
        title = (title_el.get_text(strip=True) if title_el else "").strip()

        url = None
        if title_el and title_el.name == "a" and title_el.has_attr("href"):
            url = title_el["href"]

        # common date containers
        when_text = ""
        time_el = el.find(["time"])
        if time_el and time_el.has_attr("datetime"):
            when_text = time_el["datetime"]
        elif time_el:
            when_text = time_el.get_text(" ", strip=True)

        if not when_text:
            dt_el = el.select_one(".date, .event-date, .EventDate, .When")
            when_text = dt_el.get_text(" ", strip=True) if dt_el else ""

        start_utc = None
        end_utc = None
        if when_text:
            try:
                # Handles most “2025-09-05 19:00” / ISO strings
                start_utc = _to_utc(dtparser.parse(when_text, fuzzy=True))
            except Exception:
                start_utc = None

        # location
        loc = None
        loc_el = el.select_one(".location, .event-location, .Venue, .where")
        if loc_el:
            loc = loc_el.get_text(" ", strip=True) or None

        if title or start_utc or url:
            out.append({
                "id": "gz-" + str(abs(hash(f"{title}|{(start_utc.isoformat() if start_utc else '')}|{url or ''}"))),
                "title": title or url or "Event",
                "start": start_utc,
                "end": end_utc,
                "location": loc,
                "url": url,
                "tz": "UTC",
            })

    return out

def fetch_growthzone_html(source: Dict, start_date, end_date) -> Tuple[List[Dict], Dict]:
    """
    GrowthZone listing fetcher (St. Germain / Rhinelander).
    Reads URL from source["url"]. Returns (events, diag).
    """
    sd = _coerce_date(start_date)
    ed = _coerce_date(end_date)

    url = (source.get("url") or "").strip()
    if not url:
        return [], {"ok": False, "error": "Missing source.url for GrowthZone", "diag": {}}

    diag = {"ok": True, "error": "", "diag": {"url": url}}
    try:
        r = _get(url)
    except Exception as e:
        return [], {"ok": False, "error": f"GET failed: {e}", "diag": {"url": url}}

    soup = BeautifulSoup(r.text, "html.parser")

    # Prefer JSON-LD
    items = _jsonld_events(soup)
    events: List[Dict] = []
    for it in items:
        try:
            ev = _parse_jsonld_event(it)
            if not ev.get("start"):
                continue
            if _within_window(ev["start"], ev.get("end"), sd, ed):
                events.append(ev)
        except Exception:
            continue

    # Fallback: HTML cards if JSON-LD is empty
    if not events:
        for ev in _html_events(soup):
            if ev.get("start") and _within_window(ev["start"], ev.get("end"), sd, ed):
                events.append(ev)

    diag["diag"]["found"] = len(events)
    return events, diag
