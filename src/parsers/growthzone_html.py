# src/parsers/growthzone_html.py
"""
GrowthZone HTML parser (Rhinelander).

Surgical fixes:
- Match signature (source, start_date, end_date)
- Parse the calendar listing page to collect event detail links
- Visit each detail page and extract title, date/time, location, url
- Filter to the requested date window (inclusive)
- Produce event dicts compatible with the rest of the pipeline

Notes:
- GrowthZone detail pages typically contain "Date and Time" text like:
  "Thursday Sep 4, 2025 8:00 AM — 5:00 PM CDT"
- We parse that robustly; if end is missing, use start as end
"""

import re
from datetime import datetime, timezone
from urllib.parse import urljoin, urlparse
from dateutil import parser as dtparse
import requests
from bs4 import BeautifulSoup

def _try_parse_dt(dt_text):
    # Strip double spaces and odd unicode dashes/timezones to improve parsing
    text = re.sub(r"\s+", " ", dt_text).strip()
    # Remove timezone abbreviations (CDT/CST) so dateutil doesn't mis-guess
    text = re.sub(r"\b([A-Z]{2,4})\b", "", text).replace("—", "-").strip()
    try:
        return dtparse.parse(text, fuzzy=True)
    except Exception:
        return None

def _bounded(start_dt, window_start, window_end):
    return (start_dt is None) or (window_start is None) or (window_end is None) or (window_start <= start_dt <= window_end)

def _to_iso_naive(dt_obj):
    if not dt_obj:
        return None
    # Keep naive local time as ISO-like "YYYY-MM-DD HH:MM:SS"
    return dt_obj.replace(tzinfo=None).strftime("%Y-%m-%d %H:%M:%S")

def _normalize_event(source, title, start_dt, end_dt, url, location):
    # Deterministic uid: hash the URL path so we don't leak randomness
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

def _extract_datetime_block(soup):
    """
    Look for a block labeled 'Date and Time' and pull the line following it.
    """
    # GrowthZone often uses <h3> or <h2> headings:
    headers = soup.find_all(text=re.compile(r"Date\s+and\s+Time", re.I))
    for hdr in headers:
        # Get a nearby element with the actual dates
        parent = hdr.parent
        # Try sibling text
        cand = None
        for nxt in [parent.find_next_sibling(), parent.find_next()]:
            if nxt and nxt.get_text(strip=True):
                cand = nxt.get_text(" ", strip=True)
                break
        if cand:
            return cand
    # Fallback: scan visible text for a likely date phrase with month name
    body_text = soup.get_text(" ", strip=True)
    m = re.search(r"(Mon|Tue|Wed|Thu|Fri|Sat|Sun)\w*\s+[A-Za-z]{3,9}\s+\d{1,2},\s+\d{4}.*", body_text)
    if m:
        return m.group(0)
    return None

def _extract_location(soup):
    # Prefer a labeled "Location" section; else the venue link block
    loc_hdrs = soup.find_all(text=re.compile(r"Location", re.I))
    for hdr in loc_hdrs:
        parent = hdr.parent
        for nxt in [parent.find_next_sibling(), parent.find_next()]:
            if nxt and nxt.get_text(strip=True):
                return nxt.get_text(" ", strip=True)
    # Fallback: any element with class or aria-label indicating address
    addr = soup.find(attrs={"aria-label": re.compile("address", re.I)})
    if addr:
        return addr.get_text(" ", strip=True)
    return None

def fetch_growthzone_html(source, start_date, end_date):
    """
    Parse the GrowthZone calendar listing + detail pages and return normalized events.
    """
    base_url = source.get("url", "").strip()
    if not base_url:
        return []

    session = requests.Session()
    session.headers.update({"User-Agent": "northwoods-events-v2 (+github)"})

    # Parse date window (YYYY-MM-DD) if provided
    window_start = dtparse.parse(start_date).replace(tzinfo=None) if start_date else None
    window_end = dtparse.parse(end_date).replace(tzinfo=None) if end_date else None

    # 1) Load listing page
    resp = session.get(base_url, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    # 2) Collect unique event detail links
    links = set()
    for a in soup.select('a[href*="/events/details/"], a[href*="/events/"]'):
        href = a.get("href") or ""
        # Normalize and filter to same host
        full = urljoin(base_url, href)
        if "/events/" in full and "/calendar" not in full and "/map" not in full:
            links.add(full)
    # Guardrail: don’t spider too much
    detail_urls = list(links)[:200]

    events = []
    for url in detail_urls:
        try:
            r = session.get(url, timeout=30)
            r.raise_for_status()
            d = BeautifulSoup(r.text, "html.parser")

            # Title
            title_tag = d.find("h1") or d.find("h2")
            title = title_tag.get_text(" ", strip=True) if title_tag else "Untitled"

            # Date/time
            dt_block = _extract_datetime_block(d)
            start_dt = None
            end_dt = None
            if dt_block:
                # Try to split on a range separator first
                parts = re.split(r"[–—-]{1,2}| to ", dt_block)
                if parts:
                    start_dt = _try_parse_dt(parts[0])
                    if len(parts) > 1:
                        # If the end part lacks a date, combine date from start
                        end_text = parts[1].strip()
                        if start_dt:
                            # Inject start date if end has only time
                            date_prefix = start_dt.strftime("%B %d, %Y ")
                            if re.search(r"\d{1,2}:\d{2}", end_text) and not re.search(r"\d{4}", end_text):
                                end_text = f"{date_prefix}{end_text}"
                        end_dt = _try_parse_dt(end_text)
            # Filter by window
            if start_dt and not _bounded(start_dt, window_start, window_end):
                continue

            # Location
            location = _extract_location(d)

            events.append(_normalize_event(source, title, start_dt, end_dt, url, location))
        except Exception:
            # Skip noisy failures; your report.json will reflect counts
            continue

    return events
