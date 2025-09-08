# src/parsers/simpleview_html.py
from __future__ import annotations

import json
import re
from datetime import date, datetime
from typing import Any, Dict, List, Tuple
from urllib.parse import urljoin

import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup  # type: ignore
from dateutil import parser as dtparse  # type: ignore
from zoneinfo import ZoneInfo

from src.fetch import get
from src.models import Event

_TZ = ZoneInfo("America/Chicago")
_RE_SPC = re.compile(r"\s+")

def _clean(s: str | None) -> str | None:
    return _RE_SPC.sub(" ", s).strip() if s else None

def _parse_rss_links(xml_text: str) -> List[str]:
    links: List[str] = []
    try:
        root = ET.fromstring(xml_text)
    except Exception:
        return links

    # RSS 2.0
    for item in root.findall(".//item"):
        link = item.findtext("link")
        if link:
            links.append(link)

    # Atom
    ATOM_NS = "{http://www.w3.org/2005/Atom}"
    for entry in root.findall(f".//{ATOM_NS}entry"):
        link_el = entry.find(f"{ATOM_NS}link")
        if link_el is not None:
            href = link_el.attrib.get("href")
            if href:
                links.append(href)

    # De-dupe, keep order
    seen: set[str] = set()
    out: List[str] = []
    for l in links:
        if l in seen:
            continue
        seen.add(l)
        out.append(l)
    return out

def _jsonld_events(soup: BeautifulSoup) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
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
                        out.append(n)
    return out

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

def _text_after_label(soup: BeautifulSoup, label: str) -> str | None:
    # Typical “Date”, “Time”, “Location” blocks
    lab = soup.find(string=re.compile(rf"^\s*{re.escape(label)}\s*:?\s*$", re.I))
    if lab and lab.parent:
        for sib in lab.parent.next_siblings:
            t = _clean(getattr(sib, "get_text", lambda *_: str(sib))(" ", strip=True) if hasattr(sib, "get_text") else str(sib))
            if t:
                return t
    full = soup.get_text("\n", strip=True)
    m = re.search(rf"{label}\s*:?\s*(.+?)(?:\n[A-Z][a-zA-Z]+:|\Z)", full, re.I | re.S)
    return _clean(m.group(1)) if m else None

def _parse_visible_dt(date_txt: str | None, time_txt: str | None) -> tuple[datetime | None, datetime | None]:
    if not date_txt:
        return None, None
    try:
        d = dtparse.parse(date_txt).date()
    except Exception:
        m = re.search(r"[A-Za-z]+ \d{1,2}, \d{4}", date_txt)
        if not m:
            return None, None
        d = dtparse.parse(m.group(0)).date()

    start_local = None
    end_local = None
    times = re.findall(r"\d{1,2}:\d{2}\s*[AP]M", time_txt or "")
    if times:
        start_local = dtparse.parse(f"{d.isoformat()} {times[0]}").replace(tzinfo=_TZ)
        if len(times) > 1:
            end_local = dtparse.parse(f"{d.isoformat()} {times[1]}").replace(tzinfo=_TZ)
    else:
        start_local = datetime(d.year, d.month, d.day, 0, 0, tzinfo=_TZ)

    return start_local.astimezone(ZoneInfo("UTC")), end_local.astimezone(ZoneInfo("UTC")) if end_local else None

def _hydrate_detail(url: str) -> Event | None:
    r = get(url)
    soup = BeautifulSoup(r.text, "html.parser")

    title = None
    h1 = soup.find("h1")
    if h1:
        title = _clean(h1.get_text(" ", strip=True))
    if not title and soup.title:
        title = _clean(soup.title.get_text(strip=True))

    # Prefer JSON-LD
    nodes = _jsonld_events(soup)
    if nodes:
        return _event_from_jsonld(nodes[0], url, title)

    # Fallback: visible fields
    date_txt = _text_after_label(soup, "Date")
    time_txt = _text_after_label(soup, "Time")
    loc_txt  = _text_after_label(soup, "Location")
    start_utc, end_utc = _parse_visible_dt(date_txt, time_txt)

    return Event(
        title=title or "Event",
        start_utc=start_utc,
        end_utc=end_utc,
        url=url,
        location=_clean(loc_txt),
        description=None,
        source_meta={"jsonld": False},
    )

def fetch_simpleview_html(url: str, start_date: date, end_date: date) -> Tuple[List[Event], Dict[str, Any]]:
    diag: Dict[str, Any] = {"feed_or_list_url": url, "links": 0, "hydrated": 0, "errors": 0}
    events: List[Event] = []

    links: List[str] = []
    if "/event/rss" in url:
        # Parse RSS/Atom without external deps
        feed_text = get(url).text
        links = _parse_rss_links(feed_text)
    else:
        # Fallback: collect anchors from listing page
        soup = BeautifulSoup(get(url).text, "html.parser")
        seen: set[str] = set()
        for a in soup.select("a[href*='/event/']"):
            href = a.get("href")
            if not href:
                continue
            full = urljoin(url, href)
            if full not in seen:
                seen.add(full)
                links.append(full)

    diag["links"] = len(links)

    for link in links:
        try:
            ev = _hydrate_detail(link)
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
