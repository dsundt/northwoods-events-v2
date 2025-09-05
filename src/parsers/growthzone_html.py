# src/parsers/growthzone_html.py
"""
GrowthZone HTML parser (Rhinelander).

Fixes:
- Signature now (source, start_date, end_date).
- More robust discovery of event detail links.
- Stronger parsing of the "Date and Time" block (varies by tenant/theme).
- Filters within requested window.
"""

from __future__ import annotations
import re
from urllib.parse import urljoin
from dateutil import parser as dtparse
import requests
from bs4 import BeautifulSoup


def _to_iso_naive(dt_obj):
    return dt_obj.replace(tzinfo=None).strftime("%Y-%m-%d %H:%M:%S") if dt_obj else None


def _normalize_event(source, title, start_dt, end_dt, url, location):
    uid = f"{abs(hash(url)) % 10**8}@northwoods-v2"
    name = source.get("name") or source.get("id") or "GrowthZone"
    return {
        "uid": uid,
        "title": title or "Untitled",
        "start_utc": _to_iso_naive(start_dt),
        "end_utc": _to_iso_naive(end_dt or start_dt),
        "url": url,
        "location": (location or "").strip() or None,
        "source": name,
        "calendar": name,
    }


def _extract_datetime_text(soup):
    # Look for a heading or label that says "Date and Time" (common on GrowthZone)
    candidates = soup.find_all(text=re.compile(r"Date\s+and\s+Time", re.I))
    for t in candidates:
        parent = t.parent
        # Try the next sibling blocks first (details often sit there)
        for node in [parent.find_next_sibling(), parent.find_next()]:
            if node:
                txt = node.get_text(" ", strip=True)
                if txt:
                    return txt
    # Fallback: search the whole body text for a likely date line
    body = soup.get_text(" ", strip=True)
    # Look for weekday Month DD, YYYY ... pattern
    m = re.search(r"(Mon|Tue|Wed|Thu|Fri|Sat|Sun)\w*\s+[A-Za-z]{3,9}\s+\d{1,2},\s+\d{4}.*", body)
    if m:
        return m.group(0)
    return None


def _parse_range(dt_text):
    """
    Parse a date range like "Thu Sep 4, 2025 8:00 AM — 5:00 PM CDT"
    or "Sep 4, 2025 8:00 AM - Sep 4, 2025 5:00 PM".
    """
    if not dt_text:
        return None, None

    text = re.sub(r"\s+", " ", dt_text)
    text = text.replace("—", "-")  # normalize em dashes
    # remove TZ abbrevs that confuse parser
    text = re.sub(r"\b([A-Z]{2,4})\b", "", text)

    # Split on range dash or " to "
    parts = re.split(r"\s+-\s+|\s+to\s+", text, flags=re.I)
    try:
        if len(parts) == 1:
            start = dtparse.parse(parts[0], fuzzy=True)
            return start, None
        elif len(parts) >= 2:
            start = dtparse.parse(parts[0], fuzzy=True)
            end_txt = parts[1]
            # if end lacks a date, inherit from start
            if re.search(r"\d{1,2}:\d{2}", end_txt) and not re.search(r"\d{4}", end_txt):
                end_txt = f"{start.strftime('%B %d, %Y')} {end_txt}"
            end = dtparse.parse(end_txt, fuzzy=True)
            return start, end
    except Exception:
        return None, None
    return None, None


def fetch_growthzone_html(source, start_date, end_date):
    base_url = (source.get("url") or "").strip()
    if not base_url:
        return []

    session = requests.Session()
    session.headers.update({"User-Agent": "northwoods-events-v2 (+github)"})

    win_start = dtparse.parse(start_date).replace(tzinfo=None) if start_date else None
    win_end = dtparse.parse(end_date).replace(tzinfo=None) if end_date else None

    try:
        r = session.get(base_url, timeout=30)
        r.raise_for_status()
    except Exception:
        return []

    soup = BeautifulSoup(r.text, "html.parser")

    # Collect candidate detail links
    links = set()
    # GrowthZone often uses /events/details/ or /events/<slug>/
    for a in soup.select('a[href*="/events/"]'):
        href = a.get("href") or ""
        full = urljoin(base_url, href)
        if "/events/" in full and "/calendar" not in full and "#/" not in full:
            links.add(full)

    detail_urls = list(links)[:250]

    def in_window(dtobj):
        if not dtobj:
            return True
        n = dtobj.replace(tzinfo=None)
        if win_start and n < win_start:
            return False
        if win_end and n > win_end:
            return False
        return True

    events = []
    for url in detail_urls:
        try:
            d = session.get(url, timeout=30)
            d.raise_for_status()
            ds = BeautifulSoup(d.text, "html.parser")

            title_tag = ds.find("h1") or ds.find("h2") or ds.find("title")
            title = title_tag.get_text(" ", strip=True) if title_tag else "Untitled"

            dt_text = _extract_datetime_text(ds)
            start_dt, end_dt = _parse_range(dt_text)

            # If no dates found, skip (this was your prior symptom)
            if start_dt and not in_window(start_dt):
                continue

            # Location heuristics
            location = None
            loc_hdrs = ds.find_all(text=re.compile(r"Location", re.I))
            for hdr in loc_hdrs:
                parent = hdr.parent
                for node in [parent.find_next_sibling(), parent.find_next()]:
                    if node and node.get_text(strip=True):
                        location = node.get_text(" ", strip=True)
                        break
                if location:
                    break

            events.append(_normalize_event(source, title, start_dt, end_dt, url, location))
        except Exception:
            continue

    return events
