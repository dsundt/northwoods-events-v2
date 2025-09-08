# src/parsers/growthzone_html.py
from __future__ import annotations

import json
import re
from datetime import datetime, date
from typing import Any, Dict, List, Tuple
from urllib.parse import urljoin

from bs4 import BeautifulSoup  # type: ignore
from dateutil import parser as dtparse  # type: ignore
from zoneinfo import ZoneInfo

from src.fetch import get
from src.models import Event

_TZ = ZoneInfo("America/Chicago")
_RE_SPC = re.compile(r"\s+")
_RE_DATE = re.compile(r"[A-Za-z]+ \d{1,2}, \d{4}")
_RE_TIME = re.compile(
    r"(?P<start>\d{1,2}:\d{2}\s*[AP]M)"
    r"(?:\s*-\s*(?P<end>\d{1,2}:\d{2}\s*[AP]M))?"
    r"(?:\s*[A-Z]{2,4})?"
)

def _clean(s: str | None) -> str | None:
    return _RE_SPC.sub(" ", s).strip() if s else None

def _text_after_label(soup: BeautifulSoup, label: str) -> str | None:
    # Try a “Label:” text node
    lab = soup.find(string=re.compile(rf"^\s*{re.escape(label)}\s*:?\s*$", re.I))
    if lab and lab.parent:
        for sib in lab.parent.next_siblings:
            t = _clean(getattr(sib, "get_text", lambda *_: str(sib))(" ", strip=True) if hasattr(sib, "get_text") else str(sib))
            if t:
                # stop if we hit next label
                if re.match(r"^\s*(Date|Time|Location|Contact|Fees)\s*:?\s*$", t, re.I):
                    break
                return t
    # Fallback: slice from full text
    full = soup.get_text("\n", strip=True)
    m = re.search(rf"{label}\s*:?\s*(.+?)(?:\n[A-Z][a-zA-Z]+:|\Z)", full, re.I | re.S)
    return _clean(m.group(1)) if m else None

def _parse_dt(date_txt: str | None, time_txt: str | None) -> tuple[datetime | None, datetime | None]:
    if not date_txt:
        return None, None
    m = _RE_DATE.search(date_txt)
    if not m:
        return None, None
    d = dtparse.parse(m.group(0)).date()

    start_local = None
    end_local = None
    mt = _RE_TIME.search(time_txt or "") or _RE_TIME.search(date_txt or "")
    if mt:
        s = mt.group("start")
        e = mt.group("end")
        start_local = dtparse.parse(f"{d.isoformat()} {s}").replace(tzinfo=_TZ)
        if e:
            end_local = dtparse.parse(f"{d.isoformat()} {e}").replace(tzinfo=_TZ)
    else:
        start_local = datetime(d.year, d.month, d.day, 0, 0, tzinfo=_TZ)

    return (
        start_local.astimezone(ZoneInfo("UTC")) if start_local else None,
        end_local.astimezone(ZoneInfo("UTC")) if end_local else None,
    )

def _event_from_jsonld(node: dict, url: str, title_fallback: str | None) -> Event:
    title = _clean(node.get("name")) or title_fallback or "Event"
    sd = node.get("startDate")
    ed = node.get("endDate")
    start_utc = dtparse.parse(sd).astimezone(ZoneInfo("UTC")) if sd else None
    end_utc = dtparse.parse(ed).astimezone(ZoneInfo("UTC")) if ed else None

    location_txt = None
    loc = node.get("location")
    if isinstance(loc, dict):
        nm = _clean(loc.get("name"))
        addr = loc.get("address")
        addr_txt = None
        if isinstance(addr, dict):
            parts = [
                _clean(addr.get("streetAddress")),
                _clean(addr.get("addressLocality")),
                _clean(addr.get("addressRegion")),
                _clean(addr.get("postalCode")),
            ]
            addr_txt = ", ".join([p for p in parts if p])
        location_txt = ", ".join([p for p in [nm, addr_txt] if p])

    return Event(
        title=title,
        start_utc=start_utc,
        end_utc=end_utc,
        url=url,
        location=location_txt,
        description=None,
        source_meta={"jsonld": True},
    )

def _parse_detail(html: str, url: str) -> Event | None:
    soup = BeautifulSoup(html, "html.parser")

    title = None
    h1 = soup.find("h1")
    if h1:
        title = _clean(h1.get_text(" ", strip=True))
    if not title and soup.title:
        title = _clean(soup.title.get_text(strip=True))

    # Prefer JSON-LD if present
    for tag in soup.find_all("script", {"type": "application/ld+json"}):
        try:
            data = json.loads(tag.string or "{}")
        except Exception:
            continue
        nodes = data
        if isinstance(data, dict) and "@graph" in data:
            nodes = data["@graph"]
        if isinstance(nodes, dict):
            nodes = [nodes]
        if isinstance(nodes, list):
            for n in nodes:
                if isinstance(n, dict):
                    t = n.get("@type")
                    if t == "Event" or (isinstance(t, list) and "Event" in t):
                        return _event_from_jsonld(n, url, title)

    # Fallback to visible fields
    date_txt = _text_after_label(soup, "Date")
    time_txt = _text_after_label(soup, "Time")
    loc_txt  = _text_after_label(soup, "Location")
    start_utc, end_utc = _parse_dt(date_txt, time_txt)

    return Event(
        title=title or "Event",
        start_utc=start_utc,
        end_utc=end_utc,
        url=url,
        location=_clean(loc_txt),
        description=None,
        source_meta={"jsonld": False},
    )

def fetch_growthzone_html(url: str, start_date: date, end_date: date) -> Tuple[List[Event], Dict[str, Any]]:
    diag: Dict[str, Any] = {"calendar_url": url, "collected": 0, "hydrated": 0, "errors": 0}
    events: List[Event] = []

    cal = get(url)
    soup = BeautifulSoup(cal.text, "html.parser")
    # Collect links to details pages
    anchors = soup.select("a[href*='/events/details/']")
    seen: set[str] = set()
    detail_urls: List[str] = []
    for a in anchors:
        href = a.get("href")
        if not href:
            continue
        full = urljoin(url, href)
        if full in seen:
            continue
        seen.add(full)
        detail_urls.append(full)
    diag["collected"] = len(detail_urls)

    for du in detail_urls:
        try:
            dr = get(du)
            ev = _parse_detail(dr.text, du)
            if not ev:
                continue
            if ev.start_utc and not (start_date <= ev.start_utc.date() <= end_date):
                continue
            events.append(ev)
            diag["hydrated"] += 1
        except Exception:
            diag["errors"] += 1
            continue

    return events, {"ok": True, "error": "", "diag": diag}
