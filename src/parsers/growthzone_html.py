# src/parsers/growthzone_html.py

import hashlib
import json
import re
from datetime import datetime
from typing import List, Dict, Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)


def _isoish(dt: Optional[str]) -> Optional[str]:
    if not dt:
        return None
    try:
        # Prefer dateutil if present; otherwise light parse.
        from dateutil import parser as dparser  # type: ignore
        return dparser.parse(dt).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        m = re.search(r"^\s*(\d{4}-\d{2}-\d{2})", dt)
        if m:
            return f"{m.group(1)} 00:00:00"
        return None


def _jsonld_events(soup: BeautifulSoup) -> List[Dict]:
    out: List[Dict] = []

    def handle(obj):
        if isinstance(obj, list):
            for x in obj:
                handle(x)
            return
        if not isinstance(obj, dict):
            return

        typ = obj.get("@type") or obj.get("type")
        if isinstance(typ, list):
            typ = typ[0]

        if typ and "Event" in str(typ):
            name = obj.get("name") or obj.get("headline")
            start = _isoish(obj.get("startDate") or obj.get("start"))
            end = _isoish(obj.get("endDate") or obj.get("end"))

            loc = None
            loc_obj = obj.get("location")
            if isinstance(loc_obj, dict):
                loc_name = loc_obj.get("name")
                addr = loc_obj.get("address")
                addr_str = None
                if isinstance(addr, dict):
                    parts = [
                        addr.get("streetAddress"),
                        addr.get("addressLocality"),
                        addr.get("addressRegion"),
                    ]
                    parts = [p for p in parts if p]
                    if parts:
                        addr_str = ", ".join(parts)
                loc = " - ".join([x for x in [loc_name, addr_str] if x])

            out.append(
                {"title": name, "start_utc": start, "end_utc": end, "location": loc}
            )
            return

        # search nested structures / graphs
        for v in obj.values():
            handle(v)

    for tag in soup.find_all("script", attrs={"type": "application/ld+json"}):
        raw = tag.string or tag.text
        if not raw:
            continue
        try:
            data = json.loads(raw)
        except Exception:
            continue
        handle(data)

    return out


def fetch_growthzone_html(url: str, max_events: int = 200, timeout: int = 30) -> List[Dict]:
    """
    Returns a *list* of event dicts (never a tuple).
    Scrapes /events/calendar, follows /events/details/* pages, pulls JSON-LD.
    """
    s = requests.Session()
    s.headers.update({"User-Agent": UA})

    r = s.get(url, timeout=timeout)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")

    # GrowthZone detail links look like /events/details/<slug-or-id>
    links = set()
    for a in soup.select('a[href*="/events/details/"]'):
        href = a.get("href")
        if not href:
            continue
        links.add(urljoin(url, href))

    events: List[Dict] = []
    for link in list(links)[:max_events]:
        try:
            rr = s.get(link, timeout=timeout)
            rr.raise_for_status()
            ss = BeautifulSoup(rr.text, "html.parser")

            found = _jsonld_events(ss)
            if found:
                for e in found:
                    if not e
