# src/parsers/simpleview_html.py
from __future__ import annotations

import json
from datetime import timezone
from typing import Any, Dict, List
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from dateutil import parser as dtp


def _to_utc(s: str | None) -> str | None:
    if not s:
        return None
    try:
        return dtp.parse(s).astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return None


def fetch_simpleview_html(url: str, start_date: str, end_date: str) -> List[Dict[str, Any]]:
    """
    Simpleview list page scraper.

    Strategy:
      1) Prefer JSON-LD <script type="application/ld+json"> blocks (many SV sites include schema.org/Event).
      2) Fallback to obvious card links + nearby dates.
    """
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    html = r.text
    base = "{uri.scheme}://{uri.netloc}/".format(uri=urlparse(url))
    soup = BeautifulSoup(html, "html.parser")

    events: List[Dict[str, Any]] = []

    # JSON-LD
    for tag in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(tag.string or "")
        except Exception:
            continue

        def iter_ev(obj):
            if isinstance(obj, dict):
                if obj.get("@type") == "Event":
                    yield obj
                for v in obj.values():
                    yield from iter_ev(v)
            elif isinstance(obj, list):
                for x in obj:
                    yield from iter_ev(x)

        for e in iter_ev(data):
            name = (e.get("name") or "").strip()
            if not name:
                continue
            loc = e.get("location")
            location = None
            if isinstance(loc, dict):
                location = loc.get("name") or loc.get("address")
            url_e = e.get("url")
            if isinstance(url_e, list):
                url_e = url_e[0] if url_e else None
            if url_e:
                url_e = urljoin(base, url_e)
            events.append({
                "uid": f"{(e.get('identifier') or hash(url_e)%10**8)}-sv@northwoods-v2",
                "title": name,
                "start_utc": _to_utc(e.get("startDate")),
                "end_utc": _to_utc(e.get("endDate")),
                "url": url_e,
                "location": location,
                "source": "",
                "calendar": "",
                "source_id": "",
            })

    if events:
        return events

    # Fallback: pick card anchors with obvious date siblings
    for a in soup.select("a"):
        title = a.get_text(strip=True)
        href = a.get("href", "").strip()
        if not title or not href:
            continue
        href = urljoin(base, href)
        date_el = a.find_previous("time") or a.find_next("time")
        iso = date_el.get("datetime") if date_el and date_el.has_attr("datetime") else (date_el.get_text(strip=True) if date_el else None)
        start_utc = _to_utc(iso)
        if start_utc:
            events.append({
                "uid": f"{hash(href)%10**8}-sv@northwoods-v2",
                "title": title,
                "start_utc": start_utc,
                "end_utc": None,
                "url": href,
                "location": None,
                "source": "",
                "calendar": "",
                "source_id": "",
            })

    return events
