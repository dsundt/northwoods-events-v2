# src/parsers/simpleview_html.py
from typing import List, Dict, Any, Optional
from xml.etree import ElementTree as ET
from dateutil import parser as dtp
from datetime import datetime
from bs4 import BeautifulSoup
import html
import re
import json

from src.fetch import get

def _text(el: Optional[ET.Element], tag: str) -> Optional[str]:
    if el is None:
        return None
    t = el.findtext(tag)
    return t.strip() if t else None

def _dtstr(dt: Optional[datetime]) -> Optional[str]:
    return dt.strftime("%Y-%m-%d %H:%M:%S") if dt else None

def _enrich_from_detail(url: str) -> Dict[str, Optional[str]]:
    """Fetch event detail and extract start/end/location from JSON-LD if present."""
    try:
        r = get(url)
        soup = BeautifulSoup(r.text, "html.parser")
        for s in soup.select('script[type="application/ld+json"]'):
            try:
                data = json.loads((s.string or "").strip())
            except Exception:
                continue
            items = data if isinstance(data, list) else [data]
            for obj in items:
                if isinstance(obj, dict):
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
                        return {
                            "start_utc": _dtstr(start_dt),
                            "end_utc": _dtstr(end_dt),
                            "location": loc,
                        }
    except Exception:
        pass
    return {"start_utc": None, "end_utc": None, "location": None}

def _guess_date_from_text(s: str) -> Optional[datetime]:
    s = html.unescape(s or "")
    s = BeautifulSoup(s, "html.parser").get_text(" ", strip=True)
    try:
        return dtp.parse(s, fuzzy=True)
    except Exception:
        return None

def fetch_simpleview_html(url: str, start_utc: str = None, end_utc: str = None) -> List[Dict[str, Any]]:
    # RSS feed expected at url
    r = get(url)
    text = r.text or ""
    if "<rss" not in text[:2000].lower():
        # Not RSS? Try to enrich by scraping page-level JSON-LD (fallback)
        # (kept for safety, but Minocqua's /event/rss/ is RSS.)
        return []

    root = ET.fromstring(text)
    channel = root.find("channel")
    if channel is None:
        return []

    out: List[Dict[str, Any]] = []
    for item in channel.findall("item"):
        title = _text(item, "title") or "Event"
        link  = _text(item, "link")
        desc  = _text(item, "description") or ""

        # Try to find a date in RSS fields first (pubDate often exists, but that’s publish time)
        start_dt = None
        # Some Simpleview feeds embed dates in description
        start_dt = _guess_date_from_text(desc) or _guess_date_from_text(title)

        # If we still don't have a date (or want better location), enrich from the detail page
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

    return [e for e in out if e.get("title")]
