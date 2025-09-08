# src/parsers/growthzone_html.py
# GrowthZone/ChamberMaster HTML parser with guarded fallbacks and St. Germain cross-domain handling.
# Key guarantees:
# - Accepts (url) only (the pipeline wraps to 3-arg but passes only url).
# - Uses src.fetch.get() for consistent UA/timeout/retries.
# - Returns events with keys: title, start_utc, end_utc, location, url, source.
# - Never mutates global behavior for other sources; St. Germain-specific path is gated by host match.
from __future__ import annotations

import re
import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Set
from urllib.parse import urljoin, urlparse

from src.fetch import get

_STGER_HOST = "stgermainwi.chambermaster.com"
_STGER_OUTBOUND_HOST = "st-germain.com"

_DETAIL_ABS = re.compile(r'href=["\'](https?://[^"\']*/events/details/[^"\']+)["\']', re.I)
_DETAIL_REL = re.compile(r'href=["\'](/events/details/[^"\']+)["\']', re.I)
_STGER_OUTBOUND = re.compile(r'href=["\'](https?://st-germain\.com/events/[^"\']+)["\']', re.I)

_JSONLD_RE = re.compile(r'(?is)<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>')

def _extract_gz_detail_links(html: str, base_url: str) -> Set[str]:
    links: Set[str] = set()
    for m in _DETAIL_ABS.finditer(html):
        links.add(m.group(1))
    for m in _DETAIL_REL.finditer(html):
        links.add(urljoin(base_url, m.group(1)))
    return links

def _extract_stgermain_outbound(html: str) -> Set[str]:
    links: Set[str] = set()
    for m in _STGER_OUTBOUND.finditer(html):
        links.add(m.group(1))
    return links

def _events_root_same_host(u: str) -> str:
    p = urlparse(u)
    root = f"{p.scheme}://{p.netloc}"
    path = p.path or ""
    if "/events" in path:
        root += path.split("/events", 1)[0]
    return f"{root}/events"

def _month_seeds(n: int = 4) -> List[str]:
    first = datetime.utcnow().date().replace(day=1)
    ys, ms = first.year, first.month
    out: List[str] = []
    for i in range(n):
        yy = ys + (ms - 1 + i)//12
        mm = (ms - 1 + i)%12 + 1
        out.append(f"{yy:04d}-{mm:02d}-01")
    return out

def _jsonld_events(html: str) -> List[Dict[str, Any]]:
    evs: List[Dict[str, Any]] = []
    for sm in _JSONLD_RE.finditer(html):
        block = sm.group(1).strip()
        try:
            data = json.loads(block)
        except Exception:
            continue
        def _maybe(n: Dict[str, Any]):
            t = n.get("@type")
            ok = False
            if isinstance(t, list):
                ok = any(str(x).lower() == "event" for x in t)
            else:
                ok = str(t).lower() == "event"
            if ok:
                evs.append(n)
        if isinstance(data, dict):
            if "@type" in data:
                _maybe(data)
            g = data.get("@graph")
            if isinstance(g, list):
                for n in g:
                    if isinstance(n, dict):
                        _maybe(n)
        elif isinstance(data, list):
            for n in data:
                if isinstance(n, dict):
                    _maybe(n)
    return evs

def _norm_place(loc: Any) -> Optional[str]:
    if not loc:
        return None
    if isinstance(loc, dict):
        if loc.get("name"):
            return str(loc["name"])
        parts = [str(loc.get(k, "")).strip() for k in ("streetAddress","addressLocality","addressRegion")]
        joined = ", ".join([p for p in parts if p])
        return joined or json.dumps(loc)
    return str(loc)

def _parse_dates_from_text(html: str) -> (Optional[str], Optional[str]):
    """
    Minimal fallback for GrowthZone details when no JSON-LD exists.
    Looks for 'Date:' and 'Time:' labels in the HTML and returns
    start_utc/end_utc strings parsable by dateutil.
    """
    # Remove tags for a quick textual scan
    text = re.sub(r"(?is)<script[^>]*>.*?</script>|<style[^>]*>.*?</style>", "", html)
    text = re.sub(r"(?is)<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    # Date: September 1, 2025 | Time: 10:00 AM - 10:30 AM CDT
    m_date = re.search(r"\bDate:\s*([A-Za-z]{3,9}\s+\d{1,2},\s*\d{4})", text)
    m_time = re.search(r"\bTime:\s*([0-9]{1,2}:[0-9]{2}\s*(?:AM|PM))(?:\s*-\s*([0-9]{1,2}:[0-9]{2}\s*(?:AM|PM)))?(?:\s*([A-Z]{2,4}))?", text)
    start_s = end_s = None
    if m_date and m_time:
        d = m_date.group(1)
        t1 = m_time.group(1)
        tz = m_time.group(3) or ""
        start_s = f"{d} {t1} {tz}".strip()
        if m_time.group(2):
            end_s = f"{d} {m_time.group(2)} {tz}".strip()
    return start_s, end_s

def _detail_to_event(detail_html: str, page_url: str, source_name: str) -> Optional[Dict[str, Any]]:
    # Prefer JSON-LD
    jsonld = _jsonld_events(detail_html)
    if jsonld:
        # prefer first event node
        ev = jsonld[0]
        title = ev.get("name") or ev.get("headline") or "(untitled)"
        start_s = ev.get("startDate")
        end_s = ev.get("endDate")
        loc = _norm_place(ev.get("location"))
        return {
            "title": title,
            "start_utc": start_s,
            "end_
