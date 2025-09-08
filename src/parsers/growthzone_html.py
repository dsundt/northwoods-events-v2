# src/parsers/growthzone_html.py
from typing import List, Dict, Any, Optional, Tuple
from bs4 import BeautifulSoup
from dateutil import parser as dtp
from datetime import datetime
import json
import re
from urllib.parse import urljoin

from src.fetch import get

MONTHS_RE = r"(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)"
ISO_RE = r"\d{4}-\d{2}-\d{2}(?:[ T]\d{2}:\d{2}(?::\d{2})?)?(?:Z|[+-]\d{2}:?\d{2})?"

def _dtstr(dt: Optional[datetime]) -> Optional[str]:
    return dt.strftime("%Y-%m-%d %H:%M:%S") if dt else None

def _parse_ldjson_blocks(soup: BeautifulSoup) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for s in soup.select('script[type="application/ld+json"]'):
        try:
            raw = (s.string or "").strip()
            if not raw:
                continue
            data = json.loads(raw)
        except Exception:
            continue
        items = data if isinstance(data, list) else [data]
        for obj in items:
            if not isinstance(obj, dict):
                continue
            candidates = []
            if obj.get("@type") == "Event":
                candidates = [obj]
            elif isinstance(obj.get("@graph"), list):
                candidates = [x for x in obj["@graph"] if isinstance(x, dict) and x.get("@type") == "Event"]
            for ev in candidates:
                title = (ev.get("name") or "").strip()
                if not title:
                    continue
                start_s = ev.get("startDate")
                end_s   = ev.get("endDate")
                try:
                    start_dt = dtp.parse(start_s) if start_s else None
                except Exception:
                    start_dt = None
                try:
                    end_dt = dtp.parse(end_s) if end_s else None
                except Exception:
                    end_dt = None

                loc = None
                loc_obj = ev.get("location")
                if isinstance(loc_obj, dict):
                    loc = loc_obj.get("name") or loc_obj.get("address") or None

                url = ev.get("url") or None
                uid = ev.get("@id") or url or f"gz-{hash((title, start_s or '', url or ''))}"
                out.append({
                    "uid": str(uid),
                    "title": title,
                    "start_utc": _dtstr(start_dt),
                    "end_utc": _dtstr(end_dt),
                    "url": url,
                    "location": loc,
                })
    return out

def _first_text(soup: BeautifulSoup, selectors: List[str]) -> Optional[str]:
    for sel in selectors:
        el = soup.select_one(sel)
        if el:
            txt = el.get_text(" ", strip=True)
            if txt:
                return txt
    return None

def _extract_dates_microdata(soup: BeautifulSoup) -> Tuple[Optional[datetime], Optional[datetime]]:
    # time/meta microdata
    for sel in [
        'time[itemprop="startDate"]',
        'meta[itemprop="startDate"]',
        'time[datetime]',
        'meta[property="startDate"]',
        'meta[name="startDate"]',
    ]:
        el = soup.select_one(sel)
        if el:
            val = el.get("datetime") or el.get("content")
            if val:
                try:
                    start_dt = dtp.parse(val)
                except Exception:
                    start_dt = None
                # try to find matching end
                end_dt = None
                for sel2 in [
                    'time[itemprop="endDate"]',
                    'meta[itemprop="endDate"]',
                    'meta[property="endDate"]',
                    'meta[name="endDate"]',
                ]:
                    el2 = soup.select_one(sel2)
                    if el2:
                        v2 = el2.get("datetime") or el2.get("content")
                        if v2:
                            try:
                                end_dt = dtp.parse(v2)
                            except Exception:
                                end_dt = None
                        break
                return start_dt, end_dt

    # ISO timestamps buried in scripts/text
    m = re.search(ISO_RE, soup.text)
    if m:
        try:
            return dtp.parse(m.group(0)), None
        except Exception:
            pass

    # “Date and Time” block text (e.g., GrowthZone)
    block_text = None
    for el in soup.find_all(string=True):
        s = (el or "").strip().lower()
        if "date" in s and "time" in s:
            blk = el.parent
            if blk:
                txt = blk.get_text(" ", strip=True)
                if re.search(MONTHS_RE, txt, re.I):
                    block_text = txt
                    break
    if block_text:
        try:
            if " - " in block_text:
                left, right = block_text.split(" - ", 1)
                sdt = dtp.parse(left, fuzzy=True)
                try:
                    edt = dtp.parse(right, fuzzy=True, default=sdt)
                except Exception:
                    edt = None
                return sdt, edt
            return dtp.parse(block_text, fuzzy=True), None
        except Exception:
            pass

    return None, None

def _extract_location(soup: BeautifulSoup) -> Optional[str]:
    # Structured first
    loc = None
    for sel in [
        '[itemprop="location"] [itemprop="name"]',
        '[itemprop="location"] [itemprop="address"]',
        '[itemprop="location"]',
        "address",
        ".address",
        ".event-location",
        ".location",
        "#location",
    ]:
        el = soup.select_one(sel)
        if el:
            txt = el.get_text(" ", strip=True)
            if txt:
                loc = txt
                break

    if loc:
        return loc

    # Heuristic: a label “Location” then text
    for el in soup.find_all(string=True):
        s = (el or "").strip()
        if s and s.lower().startswith("location"):
            blk = el.parent
            if blk:
                txt = blk.get_text(" ", strip=True)
                if txt and len(txt) > len(s):
                    return txt[len(s):].strip(" :-")
    return None

def _parse_detail(url: str) -> List[Dict[str, Any]]:
    r = get(url)
    soup = BeautifulSoup(r.text, "html.parser")

    # 1) JSON-LD
    events = _parse_ldjson_blocks(soup)
    if events:
        # Backfill missing url
        for e in events:
            e.setdefault("url", url)
        return events

    # 2) Microdata & text fallbacks
    title_el = soup.select_one("h1, h2")
    title = title_el.get_text(strip=True) if title_el else None

    start_dt, end_dt = _extract_dates_microdata(soup)
    loc = _extract_location(soup)

    if title:
        return [{
            "uid": f"gz-{hash((title, _dtstr(start_dt) or '', url))}",
            "title": title,
            "start_utc": _dtstr(start_dt),
            "end_utc": _dtstr(end_dt),
            "url": url,
            "location": loc,
        }]
    return []

def _dedupe_preferring_dated(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    # key by (title, url) & prefer items that have start_utc
    best: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for e in items:
        key = ((e.get("title") or "").strip().lower(), e.get("url") or "")
        cur = best.get(key)
        if not cur:
            best[key] = e
            continue
        # prefer the one with a date; if both dated keep first
        if not cur.get("start_utc") and e.get("start_utc"):
            best[key] = e
    return list(best.values())

def fetch_growthzone_html(url: str, start_utc: str = None, end_utc: str = None) -> List[Dict[str, Any]]:
    r = get(url)
    soup = BeautifulSoup(r.text, "html.parser")

    # Collect detail links
    links = set()
    for a in soup.select('a[href*="/events/details"], a[href*="/event/details"]'):
        href = a.get("href")
        if not href:
            continue
        if href.startswith("/"):
            href = urljoin(url, href)
        links.add(href)

    events: List[Dict[str, Any]] = []
    for href in links:
        try:
            events.extend(_parse_detail(href))
        except Exception:
            continue

    # De-dupe, prefer entries that have dates
    events = _dedupe_preferring_dated([e for e in events if e.get("title")])

    return events
