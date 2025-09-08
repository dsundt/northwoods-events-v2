# src/parsers/simpleview_html.py
from typing import List, Dict, Any, Optional
from xml.etree import ElementTree as ET
from dateutil import parser as dtp
from datetime import datetime
from bs4 import BeautifulSoup
import html
import json
import re

from src.fetch import get

ISO_RE = r"\d{4}-\d{2}-\d{2}(?:[ T]\d{2}:\d{2}(?::\d{2})?)?(?:Z|[+-]\d{2}:?\d{2})?"

def _text(el: Optional[ET.Element], tag: str) -> Optional[str]:
    if el is None:
        return None
    t = el.findtext(tag)
    return t.strip() if t else None

def _dtstr(dt: Optional[datetime]) -> Optional[str]:
    return dt.strftime("%Y-%m-%d %H:%M:%S") if dt else None

def _jsonld_event_blocks(soup: BeautifulSoup) -> List[Dict[str, Any]]:
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
            evs = []
            if obj.get("@type") == "Event":
                evs = [obj]
            elif isinstance(obj.get("@graph"), list):
                evs = [x for x in obj["@graph"] if isinstance(x, dict) and x.get("@type") == "Event"]
            for ev in evs:
                start_s = ev.get("startDate")
                end_s   = ev.get("endDate")
                loc = None
                loc_obj = ev.get("location")
                if isinstance(loc_obj, dict):
                    loc = loc_obj.get("name") or loc_obj.get("address") or None
                try:
                    start_dt = dtp.parse(start_s) if start_s else None
                except Exception:
                    start_dt = None
                try:
                    end_dt = dtp.parse(end_s) if end_s else None
                except Exception:
                    end_dt = None
                out.append({
                    "start_utc": _dtstr(start_dt),
                    "end_utc": _dtstr(end_dt),
                    "location": loc,
                })
    return out

def _fallback_dates_locations(soup: BeautifulSoup) -> Dict[str, Optional[str]]:
    # time/meta microdata
    start_dt = end_dt = None
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
                    pass
                break
    for sel in [
        'time[itemprop="endDate"]',
        'meta[itemprop="endDate"]',
        'meta[property="endDate"]',
        'meta[name="endDate"]',
    ]:
        el = soup.select_one(sel)
        if el:
            val = el.get("datetime") or el.get("content")
            if val:
                try:
                    end_dt = dtp.parse(val)
                except Exception:
                    pass
            break

    # If still missing, search for an ISO date anywhere in the HTML
    if not start_dt:
        m = re.search(ISO_RE, soup.text)
        if m:
            try:
                start_dt = dtp.parse(m.group(0))
            except Exception:
                pass

    # Location blocks
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

    return {
        "start_utc": _dtstr(start_dt) if start_dt else None,
        "end_utc": _dtstr(end_dt) if end_dt else None,
        "location": loc,
    }

def _enrich_from_detail(url: str) -> Dict[str, Optional[str]]:
    try:
        r = get(url)
        soup = BeautifulSoup(r.text, "html.parser")
        # 1) JSON-LD
        jl = _jsonld_event_blocks(soup)
        if jl:
            # take first block
            return jl[0]
        # 2) Fallback microdata/text
        return _fallback_dates_locations(soup)
    except Exception:
        return {"start_utc": None, "end_utc": None, "location": None}

def _plain_text(s: str) -> str:
    s = html.unescape(s or "")
    return BeautifulSoup(s, "html.parser").get_text(" ", strip=True)

def _guess_date_from_text(*texts: str) -> Optional[datetime]:
    blob = "  ".join([_plain_text(t or "") for t in texts if t])
    try:
        return dtp.parse(blob, fuzzy=True)
    except Exception:
        return None

def fetch_simpleview_html(url: str, start_utc: str = None, end_utc: str = None) -> List[Dict[str, Any]]:
    r = get(url)
    text = r.text or ""
    if "<rss" not in text[:2000].lower():
        return []  # defensive

    root = ET.fromstring(text)
    channel = root.find("channel")
    if channel is None:
        return []

    out: List[Dict[str, Any]] = []
    for item in channel.findall("item"):
        title = _text(item, "title") or "Event"
        link  = _text(item, "link")
        desc  = _text(item, "description") or ""
        # pubDate is publish time; not reliable for event start
        start_dt = _guess_date_from_text(title, desc)

        enrich = _enrich_from_detail(link) if link else {"start_utc": None, "end_utc": None, "location": None}
        start_utc_val = enrich["start_utc"] or _dtstr(start_dt)
        end_utc_val   = enrich["end_utc"] or None
        location_val  = enrich["location"] or None

        uid = f"sv-{hash((title, start_utc_val or '', link or ''))}"
        out.append({
            "uid": uid,
            "title": title,
            "start_utc": start_utc_val,
            "end_utc": end_utc_val,
            "url": link,
            "location": location_val,
        })

    # Keep only titled items
    return [e for e in out if e.get("title")]
