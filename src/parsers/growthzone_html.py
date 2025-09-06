# src/parsers/growthzone_html.py
from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any, Dict, List, Tuple, Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from dateutil import parser as dtp

DEFAULT_TIMEOUT = 20


def _http_get(url: str, timeout: int = DEFAULT_TIMEOUT) -> requests.Response:
    headers = {
        "User-Agent": "northwoods-events-v2 (+https://github.com/dsundt/northwoods-events-v2)"
    }
    r = requests.get(url, headers=headers, timeout=timeout)
    r.raise_for_status()
    return r


def _to_utc_string(dt: datetime) -> str:
    if dt.tzinfo is not None:
        dt = dt.astimezone(tz=None)
    return dt.replace(tzinfo=None).strftime("%Y-%m-%d %H:%M:%S")


def _parse_event_detail(detail_url: str) -> Optional[Dict[str, Any]]:
    """
    Open a GrowthZone event detail page and extract JSON-LD Event (date/time, location).
    """
    try:
        html = _http_get(detail_url).text
    except Exception:
        return None

    soup = BeautifulSoup(html, "html.parser")

    # Prefer JSON-LD
    for tag in soup.select('script[type="application/ld+json"]'):
        try:
            data = json.loads(tag.string or "{}")
        except Exception:
            continue
        items = data if isinstance(data, list) else [data]
        for it in items:
            if not isinstance(it, dict):
                continue
            if it.get("@type") not in ("Event", "MusicEvent", "TheaterEvent"):
                continue

            title = (it.get("name") or "").strip() or "(untitled)"
            start = it.get("startDate")
            end = it.get("endDate")
            loc = it.get("location")
            loc_name = None
            if isinstance(loc, dict):
                loc_name = loc.get("name") or None
                if not loc_name:
                    adr = loc.get("address")
                    if isinstance(adr, dict):
                        loc_name = ", ".join([adr.get(k, "") for k in ("streetAddress", "addressLocality")]).strip(", ") or None

            ev = {
                "uid": f"{detail_url}@growthzone",
                "title": title,
                "url": detail_url,
                "location": loc_name,
            }
            if start:
                try:
                    ev["start_utc"] = _to_utc_string(dtp.parse(start))
                except Exception:
                    pass
            if end:
                try:
                    ev["end_utc"] = _to_utc_string(dtp.parse(end))
                except Exception:
                    pass

            return ev

    # Minimal fallback: try to scrape common labels if JSON-LD missing
    title = soup.select_one("h1, .event-title, .page-title")
    title_text = title.get_text(strip=True) if title else "(untitled)"
    ev = {"uid": f"{detail_url}@growthzone", "title": title_text, "url": detail_url, "location": None}

    # look for time labels
    time_el = soup.find(string=re.compile(r"(Date|Time)", re.I))
    if time_el:
        try:
            dt_guess = dtp.parse(time_el.strip(), fuzzy=True)
            ev["start_utc"] = _to_utc_string(dt_guess)
        except Exception:
            pass

    # location label
    loc_el = soup.find(string=re.compile(r"(Location|Venue|Address)", re.I))
    if loc_el:
        loc_container = loc_el.parent if hasattr(loc_el, "parent") else None
        if loc_container:
            loc_text = loc_container.get_text(" ", strip=True)
            ev["location"] = loc_text

    return ev


def fetch_growthzone_html(source: Dict[str, Any], start_date: Optional[str] = None, end_date: Optional[str] = None
                          ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Crawl GrowthZone listing page to collect detail URLs, then parse JSON-LD from each detail page.
    This fills accurate dates and locations (fixing 'no dates, no locations').
    """
    base_url = source.get("url", "").strip()
    diag: Dict[str, Any] = {"strategy": "growthzone-html+jsonld", "base_url": base_url}
    events: List[Dict[str, Any]] = []

    try:
        html = _http_get(base_url).text
    except Exception as e:
        return [], {"ok": False, "error": f"GET listing failed: {e}", "diag": diag}

    soup = BeautifulSoup(html, "html.parser")
    links: List[str] = []

    # GrowthZone detail links usually include '/events/details/'
    for a in soup.select("a[href]"):
        href = a["href"]
        if not href:
            continue
        if re.search(r"/events/details/", href):
            links.append(urljoin(base_url, href))

    links = list(dict.fromkeys(links))  # dedupe
    diag["detail_links_found"] = len(links)

    for href in links:
        ev = _parse_event_detail(href)
        if not ev:
            continue

        # Window filter (best-effort)
        try:
            if start_date and "start_utc" in ev:
                if dtp.parse(ev["start_utc"]).date() < dtp.parse(start_date).date():
                    continue
            if end_date and "start_utc" in ev:
                if dtp.parse(ev["start_utc"]).date() > dtp.parse(end_date).date():
                    continue
        except Exception:
            pass

        events.append(ev)

    diag["events_parsed"] = len(events)
    return events, {"ok": True, "diag": diag}
