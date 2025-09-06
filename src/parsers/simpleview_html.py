from __future__ import annotations

from typing import Any, Dict, List, Tuple
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from dateutil import parser as dtparse
from src.fetch import get
import json


def _parse_dt(s: str | None) -> str | None:
    if not s:
        return None
    try:
        dt = dtparse.parse(s)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return None


def _collect_jsonld_events(html: str) -> List[Dict[str, Any]]:
    soup = BeautifulSoup(html, "html.parser")
    out: List[Dict[str, Any]] = []
    for tag in soup.find_all("script", {"type": "application/ld+json"}):
        try:
            data = json.loads(tag.string or "{}")
            nodes = data if isinstance(data, list) else [data]
            for n in nodes:
                # Some Simpleview pages embed an @graph with multiple Events
                if isinstance(n, dict) and "@graph" in n and isinstance(n["@graph"], list):
                    for g in n["@graph"]:
                        if isinstance(g, dict) and g.get("@type") == "Event":
                            out.append(g)
                elif isinstance(n, dict) and n.get("@type") == "Event":
                    out.append(n)
        except Exception:
            continue
    return out


def _normalize_event(ev: Dict[str, Any], fallback_url: str, source_name: str) -> Dict[str, Any]:
    title = (ev.get("name") or "").strip()
    url = ev.get("url") or fallback_url
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

    return {
        "uid": f"{abs(hash(url)) & 0xffffffff}@northwoods-v2",
        "title": title,
        "url": url,
        "start_utc": start_utc,
        "end_utc": end_utc,
        "location": location,
        "source": source_name,
        "calendar": source_name,
    }


def fetch_simpleview_html(source: Dict[str, Any], start_date: str | None = None, end_date: str | None = None, **_) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Simpleview (Minocqua): first try JSON-LD on the LISTING page (often contains many Event objects).
    Then follow any '/event/' links and parse JSON-LD on details as fallback.
    """
    base = source["url"].rstrip("/") + "/"
    source_name = source.get("name") or source.get("id") or "Simpleview"

    list_url = base
    lresp = get(list_url)
    lhtml = lresp.text
    lsoup = BeautifulSoup(lhtml, "html.parser")

    events: List[Dict[str, Any]] = []

    # 1) JSON-LD batch on listing
    listing_jsonld = _collect_jsonld_events(lhtml)
    for ev in listing_jsonld:
        events.append(_normalize_event(ev, list_url, source_name))

    # 2) If still low yield, follow visible event links
    if len(events) < 10:
        links: List[str] = []
        for a in lsoup.select("a[href*='/event/']"):
            href = a.get("href", "")
            if "/event/" in href:
                links.append(urljoin(base, href))
        links = list(dict.fromkeys(links))

        visited: List[str] = []
        for href in links:
            try:
                dresp = get(href)
                dhtml = dresp.text
                visited.append(href)
                jds = _collect_jsonld_events(dhtml)
                if jds:
                    for ev in jds:
                        events.append(_normalize_event(ev, href, source_name))
                else:
                    # very light fallback off DOM if JSON-LD missing
                    dsoup = BeautifulSoup(dhtml, "html.parser")
                    title = (dsoup.select_one("h1") or dsoup.title or "").get_text(strip=True)
                    time_node = dsoup.select_one("time[datetime]")
                    start_utc = _parse_dt(time_node.get("datetime")) if time_node else None
                    loc_node = dsoup.select_one("[itemprop='address'], .address, .event-venue, .venue")
                    location = " ".join(loc_node.get_text(' ', strip=True).split()) if loc_node else None
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

        diag = {"list_url": list_url, "detail_followed": visited if links else [], "count": len(events)}
    else:
        diag = {"list_url": list_url, "jsonld_on_listing": len(listing_jsonld), "count": len(events)}

    return events, {"ok": True, "error": "", "diag": diag}
