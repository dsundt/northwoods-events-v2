from __future__ import annotations
from typing import List, Dict, Any
from urllib.parse import urljoin
from datetime import datetime
from dateutil import parser as dtp, tz
import json
from bs4 import BeautifulSoup

from src.fetch import get

CENTRAL = tz.gettz("America/Chicago")

def _coerce_utc(dt_str: str | None) -> str | None:
    if not dt_str:
        return None
    try:
        d = dtp.parse(dt_str)
        if d.tzinfo is None:
            d = d.replace(tzinfo=CENTRAL)
        return d.astimezone(tz.UTC).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return None

def _make_uid(source_id: str, url: str | None, title: str | None, start_utc: str | None) -> str:
    base = f"{source_id}|{url or title or ''}|{start_utc or ''}"
    return f"{abs(hash(base))}@northwoods-v2"

def _from_ld(block: dict, source: dict) -> Dict[str, Any] | None:
    if not isinstance(block, dict) or block.get("@type") != "Event":
        return None
    title = block.get("name") or ""
    url = block.get("url")
    sd = _coerce_utc(block.get("startDate"))
    ed = _coerce_utc(block.get("endDate"))
    loc = ""
    loc_obj = block.get("location")
    if isinstance(loc_obj, dict):
        loc = loc_obj.get("name") or loc_obj.get("address") or ""
        if isinstance(loc_obj.get("address"), dict):
            a = loc_obj["address"]
            loc = a.get("streetAddress") or a.get("addressLocality") or loc
    if not title or not sd:
        return None
    return {
        "uid": _make_uid(source["id"], url, title, sd),
        "title": title,
        "start_utc": sd,
        "end_utc": ed,
        "url": url,
        "location": loc or None,
        "source": source["name"],
        "calendar": source["name"],
    }

def fetch_growthzone_html(source: dict, start_date: str, end_date: str) -> List[Dict[str, Any]]:
    """
    GrowthZone HTML scraper:
      1) Parse listing page JSON-LD Event blocks.
      2) Fallback: read <time datetime> and the nearest anchor for title+url.
    Ensures dates are captured (previous issue) and normalized to UTC.
    """
    url = source.get("url")
    resp = get(url)
    soup = BeautifulSoup(resp.text, "html.parser")

    events: List[Dict[str, Any]] = []

    # 1) JSON-LD (GrowthZone frequently outputs Event schema)
    for tag in soup.find_all("script", type="application/ld+json"):
        txt = tag.string or ""
        try:
            data = json.loads(txt)
        except Exception:
            continue
        if isinstance(data, dict):
            if data.get("@type") == "Event":
                ev = _from_ld(data, source)
                if ev: events.append(ev)
            elif "@graph" in data and isinstance(data["@graph"], list):
                for node in data["@graph"]:
                    ev = _from_ld(node, source)
                    if ev: events.append(ev)
        elif isinstance(data, list):
            for node in data:
                ev = _from_ld(node, source)
                if ev: events.append(ev)

    # 2) Heuristic fallback: <time datetime> + adjacent <a>
    if not events:
        for row in soup.select("time[datetime]"):
            dt_iso = row.get("datetime")
            title = None
            href = None
            # Look nearby for the event link
            a = row.find_next("a")
            if a and a.get_text(strip=True):
                title = a.get_text(strip=True)
                href = urljoin(url, a.get("href"))
            sd = _coerce_utc(dt_iso)
            if title and sd:
                events.append({
                    "uid": _make_uid(source["id"], href, title, sd),
                    "title": title,
                    "start_utc": sd,
                    "end_utc": None,
                    "url": href,
                    "location": None,
                    "source": source["name"],
                    "calendar": source["name"],
                })

    # Window filter if both dates provided
    try:
        if start_date and end_date:
            lo = dtp.parse(start_date).replace(tzinfo=tz.UTC)
            hi = dtp.parse(end_date).replace(tzinfo=tz.UTC)
            def in_win(ev):
                su = ev.get("start_utc")
                if not su: return False
                d = dtp.parse(su).replace(tzinfo=tz.UTC)
                return lo <= d <= hi
            events = [e for e in events if in_win(e)]
    except Exception:
        pass

    return events
