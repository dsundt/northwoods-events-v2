from __future__ import annotations

from typing import Any, Dict, List, Tuple
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from dateutil import parser as dtparse
from src.fetch import get


def _coerce_dt(s: str | None) -> str | None:
    if not s:
        return None
    try:
        dt = dtparse.parse(s)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return None


def _jsonld_events(html: str) -> List[Dict[str, Any]]:
    soup = BeautifulSoup(html, "html.parser")
    out: List[Dict[str, Any]] = []
    for tag in soup.find_all("script", {"type": "application/ld+json"}):
        try:
            import json
            data = json.loads(tag.string or "{}")
            if isinstance(data, dict):
                data = [data]
            for item in data:
                if isinstance(item, dict) and item.get("@type") in ("Event", ["Event"]):
                    out.append(item)
        except Exception:
            continue
    return out


def fetch_simpleview_html(source: Dict[str, Any], start_date: str | None = None, end_date: str | None = None, **_) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Simpleview sites (e.g., Minocqua) often render event cards in HTML list pages and
    include JSON-LD on the detail page. We:
      1) Collect event links from the list
      2) Visit detail pages and extract JSON-LD Event (name, startDate, endDate, location)
    """
    base = source["url"].rstrip("/") + "/"
    source_name = source.get("name") or source.get("id") or "Simpleview"

    # Minocqua events root typically is the page itself
    list_url = base
    lresp = get(list_url)
    lsoup = BeautifulSoup(lresp.text, "html.parser")

    # Capture unique event links from cards/tiles
    links: List[str] = []
    for a in lsoup.select("a[href*='/event/'], a[href*='events/']"):
        href = a.get("href", "")
        # Skip non-event internal anchors
        if href and ("/event/" in href or href.rstrip("/").endswith("/events")):
            if "/events/" in href and "/event/" not in href:
                continue  # likely category page, not an event
            links.append(urljoin(base, href))
    # de-dup
    seen = set()
    uniq_links = []
    for h in links:
        if h not in seen:
            uniq_links.append(h)
            seen.add(h)

    events: List[Dict[str, Any]] = []
    diag_pages: List[str] = []

    for href in uniq_links:
        try:
            dresp = get(href)
            dhtml = dresp.text
            diag_pages.append(href)
            jd = _jsonld_events(dhtml)
            if not jd:
                # Sometimes Simpleview nests JSON-LD in arrays; fallback to basic scrape
                dsoup = BeautifulSoup(dhtml, "html.parser")
                title = (dsoup.select_one("h1") or dsoup.title or "").get_text(strip=True)
                time_node = dsoup.select_one("time[datetime]")
                start_utc = _coerce_dt(time_node.get("datetime")) if time_node else None
                loc_node = dsoup.select_one("[itemprop='address'], .address, .event-venue, .venue")
                location = " ".join(loc_node.get_text(" ", strip=True).split()) if loc_node else None
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
                continue

            ev = jd[0]
            title = (ev.get("name") or "").strip()
            url = ev.get("url") or href
            start_utc = _coerce_dt(ev.get("startDate"))
            end_utc = _coerce_dt(ev.get("endDate"))

            location = None
            loc = ev.get("location")
            if isinstance(loc, dict):
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
        except Exception:
            continue

    return events, {"ok": True, "error": "", "diag": {"list_url": list_url, "details": diag_pages, "count": len(events)}}
