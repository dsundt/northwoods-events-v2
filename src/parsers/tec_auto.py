from __future__ import annotations
from typing import List, Dict, Any, Tuple
from bs4 import BeautifulSoup
from dateutil import parser as dtp
from urllib.parse import urlencode

from src.fetch import get
from src.parsers.tec_rest import fetch_tec_rest
from src.util import absurl, parse_first_jsonld_event, sanitize_event

LIST_PATH = "/events/?eventDisplay=list"

def _collect_event_links(list_url: str, pages: int = 3) -> List[str]:
    links: List[str] = []
    for p in range(1, pages + 1):
        url = f"{list_url}&page={p}" if "?" in list_url else f"{list_url}?page={p}"
        resp = get(url)
        soup = BeautifulSoup(resp.text, "html.parser")
        for a in soup.select("a.tribe-events-calendar-list__event-title-link, a.tribe-events-calendar-list__event-title, a.tribe-event-title, a.tribe-common-anchor-thin"):
            href = a.get("href")
            if href:
                links.append(absurl(url, href))
    # de-dupe
    return list(dict.fromkeys(links))

def _html_fallback(base_url: str, days_ahead: int) -> Tuple[List[dict], dict]:
    # Use list page(s) to find event detail pages; parse JSON-LD on details
    diag = {"fallback": "html", "list_pages": [], "detail_sample": None}
    list_url = absurl(base_url, LIST_PATH)
    links = _collect_event_links(list_url, pages=4)
    events = []
    for i, href in enumerate(links):
        try:
            r = get(href)
            soup = BeautifulSoup(r.text, "html.parser")
            j = parse_first_jsonld_event(soup, href)
            if j:
                events.append(j)
                if diag["detail_sample"] is None:
                    diag["detail_sample"] = href
        except Exception:
            continue
    return events, diag

def fetch_tec_auto(source: dict, start_iso: str, end_iso: str) -> Tuple[List[dict], dict]:
    # Try TEC REST; if 404 or hard fail, do HTML fallback
    try:
        items, diag = fetch_tec_rest(source, start_iso, end_iso)
        return items, diag
    except Exception as e:
        # fall back
        html_items, hdiag = _html_fallback(source["url"], source.get("days_ahead", 120))
        # Normalize
        normd = []
        for ev in html_items:
            norm = sanitize_event(ev, source["name"], source["name"])
            if norm:
                normd.append(norm)
        return normd, {"error": str(e), **hdiag}
