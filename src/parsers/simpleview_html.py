from __future__ import annotations
from typing import List, Dict, Any, Set
from urllib.parse import urljoin
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

def _ev_from_ld(ld: dict, source: dict) -> Dict[str, Any] | None:
    if not isinstance(ld, dict) or ld.get("@type") != "Event":
        return None
    title = ld.get("name") or ""
    url = ld.get("url")
    sd = _coerce_utc(ld.get("startDate"))
    ed = _coerce_utc(ld.get("endDate"))

    loc = ""
    loc_obj = ld.get("location")
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

def _parse_ld_json_blocks(html: str, base_url: str, source: dict) -> List[Dict[str, Any]]:
    soup = BeautifulSoup(html, "html.parser")
    out: List[Dict[str, Any]] = []
    for tag in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(tag.string or "null")
        except Exception:
            continue
        if isinstance(data, dict) and data.get("@type") == "Event":
            ev = _ev_from_ld(data, source)
            if ev: out.append(ev)
        elif isinstance(data, dict) and "@graph" in data and isinstance(data["@graph"], list):
            for node in data["@graph"]:
                ev = _ev_from_ld(node, source)
                if ev: out.append(ev)
        elif isinstance(data, list):
            for node in data:
                ev = _ev_from_ld(node, source)
                if ev: out.append(ev)
    return out

def fetch_simpleview_html(source: dict, start_date: str, end_date: str) -> List[Dict[str, Any]]:
    """
    Simpleview listing often lacks structured dates per item, but detail pages do.
    Strategy:
      1) Fetch listing and collect candidate event URLs.
      2) Visit each detail page and parse JSON-LD Event.
      3) Normalize to UTC and return.
    Also fixes previously-seen 'invalid URLs' by urljoin with the base.
    """
    base = source.get("url")
    listing = get(base).text
    soup = BeautifulSoup(listing, "html.parser")

    # Candidate detail links (avoid nav/filters)
    candidates: Set[str] = set()
    for a in soup.select("a[href]"):
        href = a.get("href")
        text = (a.get_text(strip=True) or "").lower()
        if not href:
            continue
        # Heuristic: Simpleview event URLs typically contain "/event/" or "/events/"
        if "/event/" in href and "submit" not in href and "search" not in href:
            candidates.add(urljoin(base, href))

    events: List[Dict[str, Any]] = []
    for href in list(candidates)[:80]:  # safety bound
        try:
            detail = get(href).text
        except Exception:
            continue
        evs = _parse_ld_json_blocks(detail, href, source)
        if evs:
            # Ensure canonical detail URL
            for ev in evs:
                if not ev.get("url"):
                    ev["url"] = href
            events.extend(evs)

    # Optional window filter (only if dates are valid)
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
