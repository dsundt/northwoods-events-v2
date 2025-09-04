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

def _event_from_ld(item: dict, source: dict) -> Dict[str, Any]:
    name = item.get("name") or ""
    url = item.get("url")
    sd = item.get("startDate")
    ed = item.get("endDate")

    loc = ""
    loc_obj = item.get("location")
    if isinstance(loc_obj, dict):
        loc = loc_obj.get("name") or loc_obj.get("address") or ""
        if isinstance(loc_obj.get("address"), dict):
            addr = loc_obj["address"]
            loc = addr.get("streetAddress") or addr.get("addressLocality") or loc

    start_utc = _coerce_utc(sd)
    end_utc = _coerce_utc(ed)
    uid = _make_uid(source["id"], url, name, start_utc)

    return {
        "uid": uid,
        "title": name,
        "start_utc": start_utc,
        "end_utc": end_utc,
        "url": url,
        "location": loc or None,
        "source": source["name"],
        "calendar": source["name"],
    }

def fetch_tec_html(source: dict, start_date: str, end_date: str) -> List[Dict[str, Any]]:
    """
    HTML fallback for The Events Calendar sites where REST is disabled.
    Strategy:
      1) Load listing URL (source['url']), parse any JSON-LD Event blocks.
      2) If nothing found, heuristically parse <time datetime> + surrounding anchors.
    Keeps a 3-arg signature, even if dates are only used for post-filtering.
    """
    url = source.get("url")
    resp = get(url)
    soup = BeautifulSoup(resp.text, "html.parser")

    events: List[Dict[str, Any]] = []

    # 1) JSON-LD blocks (robust across TEC skins)
    for tag in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(tag.string or "null")
        except Exception:
            continue
        # Could be a single Event, a list, or a graph
        candidates = []
        if isinstance(data, dict):
            if data.get("@type") == "Event":
                candidates = [data]
            elif "@graph" in data and isinstance(data["@graph"], list):
                candidates = [n for n in data["@graph"] if isinstance(n, dict) and n.get("@type") == "Event"]
        elif isinstance(data, list):
            candidates = [n for n in data if isinstance(n, dict) and n.get("@type") == "Event"]

        for item in candidates:
            ev = _event_from_ld(item, source)
            if ev["title"] and (ev["start_utc"] or ev["end_utc"]):
                events.append(ev)

    # 2) Heuristic fallback if JSON-LD not present
    if not events:
        # TEC often renders <time class="tribe-events-c-small-date__start-time" datetime="...">
        for ev_wrap in soup.select("[class*='tribe-events']"):
            time_el = ev_wrap.find("time")
            a_el = ev_wrap.find("a")
            title = (a_el.get_text(strip=True) if a_el else "").strip()
            href = urljoin(url, a_el["href"]) if a_el and a_el.has_attr("href") else None
            dt_val = None
            if time_el and time_el.has_attr("datetime"):
                dt_val = time_el["datetime"]
            elif time_el and time_el.string:
                dt_val = time_el.string.strip()
            start_utc = _coerce_utc(dt_val)
            if title and start_utc:
                events.append({
                    "uid": _make_uid(source["id"], href, title, start_utc),
                    "title": title,
                    "start_utc": start_utc,
                    "end_utc": None,
                    "url": href,
                    "location": None,
                    "source": source["name"],
                    "calendar": source["name"],
                })

    # Post-filter by requested window if we have valid UTCs
    if start_date or end_date:
        try:
            start_boundary = dtp.parse(start_date).replace(tzinfo=tz.UTC)
            end_boundary = dtp.parse(end_date).replace(tzinfo=tz.UTC)
            def in_window(ev):
                su = ev.get("start_utc")
                if not su: return False
                d = dtp.parse(su).replace(tzinfo=tz.UTC)
                return start_boundary <= d <= end_boundary
            events = [e for e in events if in_window(e)]
        except Exception:
            pass

    return events
