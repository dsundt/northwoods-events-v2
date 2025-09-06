from __future__ import annotations

from typing import Any, Dict, List, Tuple
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from dateutil import parser as dtparse
from src.fetch import get
import json


def _jsonld_events(html: str) -> List[Dict[str, Any]]:
    soup = BeautifulSoup(html, "html.parser")
    out: List[Dict[str, Any]] = []
    for tag in soup.find_all("script", {"type": "application/ld+json"}):
        try:
            data = json.loads(tag.string or "{}")
            items = data if isinstance(data, list) else [data]
            for item in items:
                if isinstance(item, dict) and (item.get("@type") == "Event" or ("Event" in (item.get("@type") or []))):
                    out.append(item)
        except Exception:
            continue
    return out


def _parse_dt(text_or_iso: str | None) -> str | None:
    if not text_or_iso:
        return None
    try:
        dt = dtparse.parse(text_or_iso)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return None


def _fallback_dates(dsoup: BeautifulSoup) -> tuple[str | None, str | None]:
    # Try time tags
    tstart = dsoup.select_one("time[datetime], .dtstart, .event-date, .date")
    tend = dsoup.select_one("time[datetime].dtend, .dtend")
    s = tstart.get("datetime") if tstart and tstart.has_attr("datetime") else (tstart.get_text(" ", strip=True) if tstart else None)
    e = tend.get("datetime") if tend and tend.has_attr("datetime") else (tend.get_text(" ", strip=True) if tend else None)
    return _parse_dt(s), _parse_dt(e)


def _fallback_location(dsoup: BeautifulSoup) -> str | None:
    node = dsoup.select_one(".event-location, .location, [itemprop='address'], .address")
    if node:
        return " ".join(node.get_text(" ", strip=True).split())
    return None


def fetch_growthzone_html(source: Dict[str, Any], start_date: str | None = None, end_date: str | None = None, **_) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    base = source["url"].rstrip("/") + "/"
    source_name = source.get("name") or source.get("id") or "GrowthZone"
    list_url = base

    list_resp = get(list_url)
    lsoup = BeautifulSoup(list_resp.text, "html.parser")

    links = []
    for a in lsoup.select("a[href]"):
        href = a.get("href", "")
        if "/events/details/" in href:
            links.append(urljoin(base, href))
    links = list(dict.fromkeys(links))

    events: List[Dict[str, Any]] = []
    visited: List[str] = []

    for href in links:
        try:
            dresp = get(href)
            visited.append(href)
            dhtml = dresp.text
            dsoup = BeautifulSoup(dhtml, "html.parser")
            jd = _jsonld_events(dhtml)

            if jd:
                ev = jd[0]
                title = (ev.get("name") or "").strip()
                url = ev.get("url") or href
                start_utc = _parse_dt(ev.get("startDate"))
                end_utc = _parse_dt(ev.get("endDate"))
                location = None
                loc = ev.get("location")
                if isinstance(loc, dict):
                    parts = []
                    n = loc.get("name")
                    if n: parts.append(n)
                    addr = loc.get("address")
                    if isinstance(addr, dict):
                        for k in ("streetAddress", "addressLocality", "addressRegion", "postalCode"):
                            v = addr.get(k)
                            if v: parts.append(v)
                    location = ", ".join([p for p in parts if p])
            else:
                # Fallback to visible content
                title = (dsoup.select_one("h1") or dsoup.title or "").get_text(strip=True)
                start_utc, end_utc = _fallback_dates(dsoup)
                location = _fallback_location(dsoup)
                url = href

            # As a last-resort, ensure there is a start date (GrowthZone often sticks it in a labelled row)
            if not start_utc:
                label = dsoup.find(text=lambda t: isinstance(t, str) and "Date and Time" in t)
                if label:
                    val = label.parent.find_next().get_text(" ", strip=True)
                    start_utc = _parse_dt(val)

            events.append({
                "uid": f"{abs(hash(url)) & 0xffffffff}@northwoods-v2",
                "title": title,
                "url": url,
                "start_utc": start_utc,
                "end_utc": end_utc,
                "location": location,
                "source": source_name,
                "calendar": source_name,
            })
        except Exception:
            continue

    return events, {"ok": True, "error": "", "diag": {"list_url": list_url, "detail_pages": visited, "count": len(events)}}
