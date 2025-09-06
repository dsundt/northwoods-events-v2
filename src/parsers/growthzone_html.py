from __future__ import annotations

from typing import Any, Dict, List, Tuple
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from dateutil import parser as dtparse
from src.fetch import get


def _jsonld_events(html: str) -> List[Dict[str, Any]]:
    soup = BeautifulSoup(html, "html.parser")
    results: List[Dict[str, Any]] = []
    for tag in soup.find_all("script", {"type": "application/ld+json"}):
        try:
            import json
            data = json.loads(tag.string or "{}")
            # Sometimes it’s a list, sometimes a dict
            if isinstance(data, dict):
                data = [data]
            for item in data:
                if isinstance(item, dict) and item.get("@type") in ("Event", ["Event"]):
                    results.append(item)
        except Exception:
            continue
    return results


def _coerce_dt(s: str | None) -> str | None:
    if not s:
        return None
    try:
        dt = dtparse.parse(s)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return None


def fetch_growthzone_html(source: Dict[str, Any], start_date: str | None = None, end_date: str | None = None, **_) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Parse GrowthZone list -> follow to detail -> read JSON-LD Event for reliable dates & location.
    """
    base = source["url"].rstrip("/") + "/"
    source_name = source.get("name") or source.get("id") or "GrowthZone"
    list_url = base  # e.g., https://business.rhinelanderchamber.com/events/

    list_resp = get(list_url)
    lsoup = BeautifulSoup(list_resp.text, "html.parser")

    # Find links to event detail pages (pattern commonly includes '/events/details/')
    links = []
    for a in lsoup.select("a[href]"):
        href = a.get("href", "")
        if "/events/details/" in href:
            links.append(urljoin(base, href))

    events: List[Dict[str, Any]] = []
    diag_links: List[str] = []

    for href in dict.fromkeys(links):  # de-dup while preserving order
        try:
            dresp = get(href)
            dhtml = dresp.text
            diag_links.append(href)
            jd = _jsonld_events(dhtml)
            if jd:
                ev = jd[0]
                title = (ev.get("name") or "").strip()
                url = ev.get("url") or href
                start_utc = _coerce_dt(ev.get("startDate"))
                end_utc = _coerce_dt(ev.get("endDate"))
                location = None
                loc = ev.get("location")
                if isinstance(loc, dict):
                    # schema.org Place/PostalAddress
                    parts = []
                    n = loc.get("name")
                    if n:
                        parts.append(n)
                    addr = loc.get("address")
                    if isinstance(addr, dict):
                        for k in ("streetAddress", "addressLocality", "addressRegion", "postalCode"):
                            v = addr.get(k)
                            if v:
                                parts.append(v)
                    location = ", ".join([p for p in parts if p])

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
            else:
                # Fallback: scrape common date/location containers
                dsoup = BeautifulSoup(dhtml, "html.parser")
                title = (dsoup.select_one("h1") or dsoup.title or "").get_text(strip=True)
                date_text = dsoup.select_one(".event-date, .date, .dtstart, time")
                start_utc = _coerce_dt(date_text.get("datetime")) if date_text and date_text.has_attr("datetime") else None
                # try text parse if no datetime attribute
                if not start_utc and date_text:
                    start_utc = _coerce_dt(date_text.get_text(" ", strip=True))
                location_node = dsoup.select_one(".event-location, .location, [itemprop='address'], .address")
                location = None
                if location_node:
                    location = " ".join(location_node.get_text(" ", strip=True).split())

                events.append({
                    "uid": f"{abs(hash(href)) & 0xffffffff}@northwoods-v2",
                    "title": title,
                    "url": href,
                    "start_utc": start_utc,
                    "end_utc": None,
                    "location": location,
                    "source": source_name,
                    "calendar": source_name,
                })
        except Exception:
            continue

    return events, {"ok": True, "error": "", "diag": {"list_url": list_url, "detail_pages": diag_links, "count": len(events)}}
