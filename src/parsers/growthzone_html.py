# src/parsers/growthzone_html.py
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import List, Dict, Optional
import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "northwoods-events-bot/1.0 (+https://dsundt.github.io/northwoods-events-v2/)"
}

# mm-dd-yyyy in GrowthZone slugs, e.g. .../details/...-09-11-2025-13044
URL_DATE_RE = re.compile(r"(\d{2})-(\d{2})-(\d{4})")

def _iso(dt: Optional[datetime]) -> Optional[str]:
    if not dt:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

def _jsonld_events(soup: BeautifulSoup) -> List[dict]:
    out = []
    for tag in soup.find_all("script", attrs={"type": "application/ld+json"}):
        txt = tag.string or tag.text or ""
        if not txt.strip():
            continue
        try:
            data = json.loads(txt)
        except Exception:
            continue
        candidates = data if isinstance(data, list) else [data]
        for d in candidates:
            if isinstance(d, dict) and d.get("@type") in ("Event", "MusicEvent"):
                out.append(d)
    return out

def _meta_datetime(soup: BeautifulSoup, itemprop: str) -> Optional[datetime]:
    # GrowthZone often adds <meta itemprop="startDate" content="2025-09-13T18:00:00-05:00">
    m = soup.find("meta", attrs={"itemprop": itemprop})
    if m and m.get("content"):
        try:
            # Accept both date-only and ISO datetime
            val = m["content"].strip()
            if "T" in val:
                dt = datetime.fromisoformat(val.replace("Z", "+00:00"))
            else:
                dt = datetime.strptime(val, "%Y-%m-%d")
            return dt.astimezone(timezone.utc) if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except Exception:
            return None
    return None

def _extract_date_from_url(url: str) -> Optional[datetime]:
    m = URL_DATE_RE.search(url)
    if not m:
        return None
    mm, dd, yyyy = m.groups()
    try:
        dt = datetime(int(yyyy), int(mm), int(dd), tzinfo=timezone.utc)
        return dt
    except Exception:
        return None

def _clean_text(x: Optional[str]) -> Optional[str]:
    if not x:
        return None
    s = re.sub(r"\s+", " ", x).strip()
    return s or None

def _event_uid(prefix: str, url: str, title: str) -> str:
    # Stable-ish and readable; URL usually unique
    return f"{prefix}-{abs(hash((url, title)))% (10**19)}"

def _fetch(url: str) -> requests.Response:
    resp = requests.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    return resp

def _parse_detail(url: str) -> (Optional[datetime], Optional[datetime], Optional[str]):
    try:
        r = _fetch(url)
    except Exception:
        # If the detail fetch fails, best effort date from URL and no location
        return _extract_date_from_url(url), None, None

    soup = BeautifulSoup(r.text, "html.parser")

    # 1) JSON-LD
    for ev in _jsonld_events(soup):
        try:
            start_iso = ev.get("startDate")
            end_iso = ev.get("endDate")
            start = None
            end = None
            if start_iso:
                start = datetime.fromisoformat(start_iso.replace("Z", "+00:00"))
                if start.tzinfo is None:
                    start = start.replace(tzinfo=timezone.utc)
            if end_iso:
                end = datetime.fromisoformat(end_iso.replace("Z", "+00:00"))
                if end.tzinfo is None:
                    end = end.replace(tzinfo=timezone.utc)

            loc = None
            loc_obj = ev.get("location")
            if isinstance(loc_obj, dict):
                loc = loc_obj.get("name") or loc_obj.get("address") or None
                if isinstance(loc, dict):
                    # address can be a PostalAddress object
                    loc = loc.get("streetAddress") or loc.get("addressLocality") or None
            elif isinstance(loc_obj, str):
                loc = loc_obj

            return start, end, _clean_text(loc)
        except Exception:
            # Try next JSON-LD block
            pass

    # 2) <meta itemprop="startDate"/"endDate">
    start = _meta_datetime(soup, "startDate")
    end = _meta_datetime(soup, "endDate")

    # 3) Fall back to URL date if still missing
    if not start:
        start = _extract_date_from_url(url)

    # 4) Location fallbacks (common GrowthZone/ChamberMaster patterns)
    loc = None
    # Typical “Location” labeled field
    label = soup.find(lambda tag: tag.name in ("dt", "strong", "h4") and "location" in tag.get_text(" ").strip().lower())
    if label:
        nxt = label.find_next(["dd", "p", "div", "span"])
        loc = _clean_text(nxt.get_text(" ")) if nxt else None
    # Sometimes the venue name appears in a block with itemprop="name"
    if not loc:
        loc_tag = soup.find(attrs={"itemprop": "location"}) or soup.find(attrs={"itemprop": "name"})
        if loc_tag:
            loc = _clean_text(loc_tag.get_text(" "))

    return start, end, loc

def fetch_growthzone_html(url: str) -> List[Dict]:
    """
    Fetch GrowthZone calendar index, enumerate event detail pages, and return a LIST of event dicts.
    No tuple, no diagnostics — the caller expects a plain list.
    """
    # 1) Hit the calendar page and grab detail URLs
    resp = _fetch(url)
    soup = BeautifulSoup(resp.text, "html.parser")

    detail_urls = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "/events/details/" in href:
            # Normalize absolute URL
            if href.startswith("/"):
                base = "{uri.scheme}://{uri.netloc}".format(uri=requests.utils.urlparse(url))
                href = base + href
            # Avoid anchors/dupes
            href = href.split("#", 1)[0]
            if href not in detail_urls:
                detail_urls.append(href)

    events: List[Dict] = []
    # Cap to a reasonable number so one huge month doesn’t DoS the build
    for href in detail_urls[:300]:
        title = None
        try:
            # Get a title early from the link text if present
            # (We’ll also overwrite later if JSON-LD has a better name.)
            title = _clean_text(a.get_text(" ")) if (a := soup.find("a", href=lambda h: h and href in h)) else None
        except Exception:
            pass

        start_dt, end_dt, location = _parse_detail(href)

        # If we still have no title, fetch <title> from the detail page
        if not title:
            try:
                r = _fetch(href)
                dsoup = BeautifulSoup(r.text, "html.parser")
                # Prefer JSON-LD name
                jlds = _jsonld_events(dsoup)
                if jlds and isinstance(jlds[0], dict):
                    title = _clean_text(jlds[0].get("name"))
                if not title:
                    if dsoup.title and dsoup.title.string:
                        title = _clean_text(dsoup.title.string.replace(" - Event - ", " "))
            except Exception:
                pass

        # As a last resort, derive a title from the slug
        if not title:
            title = _clean_text(href.rsplit("/", 1)[-1].replace("-", " ").split("?")[0]) or "Untitled"

        ev = {
            "uid": _event_uid("gz", href, title),
            "title": title,
            "start_utc": _iso(start_dt),
            "end_utc": _iso(end_dt),
            "url": href,
            "location": location,
        }
        events.append(ev)

    return events
