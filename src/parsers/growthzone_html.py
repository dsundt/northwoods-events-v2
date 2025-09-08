# src/parsers/growthzone_html.py
from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple, Union
from datetime import datetime
from zoneinfo import ZoneInfo
from urllib.parse import urljoin
import hashlib
import requests
from bs4 import BeautifulSoup

UA = "Mozilla/5.0 (X11; Linux x86_64) NorthwoodsEventsBot/2.0 (+github actions)"
TZ = ZoneInfo("America/Chicago")

def _coerce_url(source: Union[str, Dict[str, Any]]) -> str:
    if isinstance(source, str):
        return source
    if isinstance(source, dict):
        return (source.get("url") or "").strip()
    return str(source).strip()

def _get_html(url: str) -> str:
    r = requests.get(url, headers={"User-Agent": UA}, timeout=20)
    r.raise_for_status()
    return r.text

def _text_keep_br(el) -> str:
    if not el:
        return ""
    for br in el.select("br"):
        br.replace_with(", ")
    return " ".join(el.get_text(" ", strip=True).split())

def _to_utc_str(iso_like: Optional[str]) -> Optional[str]:
    if not iso_like:
        return None
    try:
        dt = datetime.fromisoformat(iso_like.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=TZ)
        return dt.astimezone(ZoneInfo("UTC")).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return None

def _extract_dates(soup: BeautifulSoup) -> Tuple[Optional[str], Optional[str]]:
    # Prefer schema.org itemprops/time tags on GrowthZone detail pages
    start_node = soup.select_one('meta[itemprop="startDate"], time[itemprop="startDate"], time[datetime]')
    end_node   = soup.select_one('meta[itemprop="endDate"], time[itemprop="endDate"]')

    start_raw = (start_node.get("content") if start_node and start_node.has_attr("content")
                 else (start_node.get("datetime") if start_node else None))
    end_raw   = (end_node.get("content") if end_node and end_node.has_attr("content")
                 else (end_node.get("datetime") if end_node else None))

    return _to_utc_str(start_raw), _to_utc_str(end_raw)

def _extract_location(soup: BeautifulSoup) -> Optional[str]:
    """
    STRICT per your request:
      div.mn-event-section.mn-event-location > div.mn-event-content
      and prefer the inner .mn-raw block if present.
    No 'Location:' label, just the content (br -> ', ').
    """
    content = soup.select_one("div.mn-event-section.mn-event-location div.mn-event-content")
    if not content:
        return None
    raw = content.select_one(".mn-raw")
    if raw:
        return _text_keep_br(raw)
    return _text_keep_br(content)

def _title(soup: BeautifulSoup) -> str:
    h1 = soup.select_one("h1, .mn-event-title")
    if h1:
        return " ".join(h1.get_text(" ", strip=True).split())
    og = soup.select_one('meta[property="og:title"]')
    return (og.get("content") if og else "") or "Untitled Event"

def _uid(title: str, url: str, start_utc: Optional[str]) -> str:
    key = f"{title}|{url}|{start_utc or ''}".encode("utf-8")
    return "gz-" + hashlib.md5(key).hexdigest()

def fetch_growthzone_html(source: Union[str, Dict[str, Any]],
                          start_date: Optional[datetime] = None,
                          end_date: Optional[datetime] = None) -> List[Dict[str, Any]]:
    """
    Rhinelander (GrowthZone) — crawl calendar page for detail links,
    then parse each detail page for title, true start/end, and STRICT location block.
    Accepts either a full source dict or a plain URL string.
    """
    cal_url = _coerce_url(source)
    if not cal_url:
        return []

    html = _get_html(cal_url)
    soup = BeautifulSoup(html, "html.parser")

    links: List[str] = []
    seen = set()
    for a in soup.select('a[href*="/events/details/"]'):
        href = (a.get("href") or "").strip()
        if not href:
            continue
        u = urljoin(cal_url, href)
        if u not in seen:
            seen.add(u)
            links.append(u)

    events: List[Dict[str, Any]] = []
    for u in links:
        try:
            dhtml = _get_html(u)
            dsoup = BeautifulSoup(dhtml, "html.parser")

            title = _title(dsoup)
            start_utc, end_utc = _extract_dates(dsoup)
            location = _extract_location(dsoup)

            events.append({
                "uid": _uid(title, u, start_utc),
                "title": title,
                "start_utc": start_utc,
                "end_utc": end_utc,
                "url": u,
                "location": location,
            })
        except Exception:
            # skip pages that fail—keeps the run resilient
            continue

    return events
