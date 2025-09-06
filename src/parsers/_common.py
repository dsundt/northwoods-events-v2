# Path: src/parsers/_common.py
# Small shared helpers for parsers. No new deps beyond existing requirements.

from __future__ import annotations
import json
import re
from typing import Any, Dict, Iterable, List, Optional, Tuple
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup
from dateutil import parser as dtparse

def _strip(s: Optional[str]) -> Optional[str]:
    if s is None:
        return None
    s = str(s).strip()
    return s or None

def _parse_dt(value: Optional[str]) -> Optional[str]:
    """Parse many date formats into 'YYYY-MM-DD HH:MM:SS' (naive)."""
    if not value:
        return None
    try:
        dt = dtparse.parse(value)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return None

def _mk_uid(prefix: str, raw_id: Any) -> str:
    base = f"{prefix}-{raw_id}".replace(" ", "-")
    return f"{base}@northwoods-v2"

def _join_loc(parts: Iterable[Optional[str]]) -> Optional[str]:
    parts_clean = [p.strip() for p in parts if p and p.strip()]
    return " | ".join(parts_clean) if parts_clean else None

def normalize_event(
    *,
    uid_prefix: str,
    raw_id: Any,
    title: Optional[str],
    url: Optional[str],
    start: Optional[str],
    end: Optional[str],
    location: Optional[str],
    calendar: str,
    source_name: str,
) -> Optional[Dict[str, Any]]:
    title = _strip(title)
    url = _strip(url)
    start_utc = _parse_dt(start)
    end_utc = _parse_dt(end) or start_utc  # if missing end, mirror start

    # Require at least title + start
    if not title or not start_utc:
        return None

    return {
        "uid": _mk_uid(uid_prefix, raw_id or title),
        "title": title,
        "start_utc": start_utc,
        "end_utc": end_utc,
        "url": url,
        "location": _strip(location),
        "source": source_name,
        "calendar": calendar,
    }

def extract_jsonld_events(html: str) -> List[Dict[str, Any]]:
    """
    Extract JSON-LD Event objects from HTML. Supports top-level, list, and @graph.
    Returns a list of raw JSON items with at least @type == 'Event'.
    """
    soup = BeautifulSoup(html, "html.parser")
    out: List[Dict[str, Any]] = []

    def _collect(obj: Any):
        if isinstance(obj, dict):
            # Handle @graph
            if "@graph" in obj and isinstance(obj["@graph"], list):
                for node in obj["@graph"]:
                    _collect(node)
                return
            # Handle type(s)
            t = obj.get("@type")
            if isinstance(t, list):
                if any(str(x).lower() == "event" for x in t):
                    out.append(obj)
            elif isinstance(t, str):
                if t.lower() == "event":
                    out.append(obj)
            # Sometimes Events are nested under "itemListElement"
            ile = obj.get("itemListElement")
            if isinstance(ile, list):
                for node in ile:
                    _collect(node)
        elif isinstance(obj, list):
            for node in obj:
                _collect(node)

    for tag in soup.find_all("script", {"type": "application/ld+json"}):
        txt = (tag.string or "").strip()
        if not txt:
            continue
        try:
            data = json.loads(txt)
        except Exception:
            # Some sites embed invalid JSON; try to salvage by removing trailing commas
            try:
                txt2 = re.sub(r",(\s*[}\]])", r"\1", txt)
                data = json.loads(txt2)
            except Exception:
                continue
        _collect(data)
    return out

def jsonld_to_norm(
    items: List[Dict[str, Any]],
    *,
    uid_prefix: str,
    calendar: str,
    source_name: str
) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for it in items:
        raw_id = it.get("@id") or it.get("identifier") or it.get("url") or it.get("name")
        title = it.get("name")
        url = it.get("url")
        start = it.get("startDate")
        end = it.get("endDate")

        location = None
        loc = it.get("location")
        if isinstance(loc, dict):
            # location can be Place -> address (PostalAddress) or name
            loc_name = loc.get("name")
            addr = loc.get("address")
            if isinstance(addr, dict):
                location = _join_loc([
                    loc_name,
                    addr.get("streetAddress"),
                    addr.get("addressLocality"),
                    addr.get("addressRegion"),
                    addr.get("postalCode"),
                ])
            else:
                location = loc_name
        elif isinstance(loc, str):
            location = loc

        ev = normalize_event(
            uid_prefix=uid_prefix,
            raw_id=raw_id,
            title=title,
            url=url,
            start=start,
            end=end,
            location=location,
            calendar=calendar,
            source_name=source_name,
        )
        if ev:
            out.append(ev)
    return out
