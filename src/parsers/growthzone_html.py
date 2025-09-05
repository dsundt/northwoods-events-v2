# src/parsers/growthzone_html.py
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, List
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from dateutil import parser as dtp


def _json_ld_events(soup: BeautifulSoup) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for tag in soup.find_all("script", type="application/ld+json"):
        try:
            payload = json.loads(tag.string or "")
        except Exception:
            continue

        def collect(obj):
            if isinstance(obj, dict):
                typ = obj.get("@type")
                if typ == "Event" and (obj.get("name") or obj.get("startDate")):
                    out.append(obj)
                for v in obj.values():
                    collect(v)
            elif isinstance(obj, list):
                for x in obj:
                    collect(x)

        collect(payload)
    return out


def _to_utc_str(dt_str: str | None) -> str | None:
    if not dt_str:
        return None
    try:
        return dtp.parse(dt_str).astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return None


def _norm_ld(e: Dict[str, Any], base: str, source_name: str, source_id: str) -> Dict[str, Any]:
    url = e.get("url")
    if isinstance(url, list):
        url = url[0] if url else None
    if url and isinstance(url, str):
        url = urljoin(base, url)

    loc = e.get("location")
    if isinstance(loc, dict):
        location = loc.get("name") or loc.get("address") or None
    else:
        location = loc

    return {
        "uid": f"{(e.get('identifier') or e.get('name') or 'gzevent')}-gz@northwoods-v2",
        "title": (e.get("name") or "").strip(),
        "start_utc": _to_utc_str(e.get("startDate")),
        "end_utc": _to_utc_str(e.get("endDate")),
        "url": url,
        "location": location,
        "source": source_name,
        "calendar": source_name,
        "source_id": source_id,
    }


def fetch_growthzone_html(url: str, start_date: str, end_date: str) -> List[Dict[str, Any]]:
    """
    GrowthZone HTML scraper with JSON-LD first, HTML fallback.
    """
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    html = r.text
    base = "{uri.scheme}://{uri.netloc}/".format(uri=urlparse(url))
    soup = BeautifulSoup(html, "html.parser")

    events: List[Dict[str, Any]] = []

    # 1) Prefer JSON-LD (most GrowthZone installs provide it)
    lds = _json_ld_events(soup)
    for e in lds:
        events.append(_norm_ld(e, base, "", ""))

    if events:
        return events

    # 2) Lightweight HTML heuristic fallback (date + title + link)
    for card in soup.select("[class*='event'] a"):
        title = card.get_text(strip=True)
        href = urljoin(base, card.get("href", "").strip())
        # Try to locate a nearby date element
        date_el = card.find_previous(lambda t: t.name in ("time", "span", "div") and ("date" in " ".join(t.get("class", [])) or "time" in " ".join(t.get("class", []))))
        start_utc = _to_utc_str(date_el.get("datetime") if date_el and date_el.has_attr("datetime") else (date_el.get_text(strip=True) if date_el else None))
        if title and href and start_utc:
            events.append({
                "uid": f"{hash(href)%10**8}-gz@northwoods-v2",
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
