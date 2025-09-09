# src/parsers/stgermain_wp.py
from __future__ import annotations

import re
from datetime import datetime
from typing import Dict, List, Optional, Set
from urllib.parse import urljoin

def _clean_text(s: str) -> str:
    from html import unescape
    s = re.sub(r"(?is)<script[^>]*>.*?</script>|<style[^>]*>.*?</style>", "", s)
    s = re.sub(r"(?is)<br\s*/?>|</p>", "\n", s)
    s = re.sub(r"(?is)<[^>]+>", "", s)
    return unescape(s).strip()

def _page_h1(html: str) -> Optional[str]:
    m = re.search(r"(?is)<h1[^>]*>(.*?)</h1>", html)
    return _clean_text(m.group(1)) if m else None

MONTHS = {m: i for i, m in enumerate(
    ["January","February","March","April","May","June","July","August","September","October","November","December"], 1)}

def _parse_date_time(text: str) -> tuple[Optional[str], Optional[str]]:
    t = _clean_text(text)
    # ranges like: October 4 – 6, 2025
    m = re.search(r'(?i)\b([A-Z][a-z]+)\s+(\d{1,2})(?:st|nd|rd|th)?\s*(?:–|-|to|&)\s*(\d{1,2}).*?,\s*(\d{4})', t)
    if m:
        mon, d1, d2, y = m.groups()
        M = MONTHS.get(mon)
        if M:
            s = datetime(int(y), M, int(d1)).isoformat()
            e = datetime(int(y), M, int(d2)).isoformat()
            return s, e
    # single: September 20, 2025
    m = re.search(r'(?i)\b([A-Z][a-z]+)\s+(\d{1,2})(?:st|nd|rd|th)?,\s*(\d{4})', t)
    if m:
        mon, d, y = m.groups()
        M = MONTHS.get(mon)
        if M:
            s = datetime(int(y), M, int(d)).isoformat()
            return s, None
    return None, None

def fetch_stgermain_wp(source, session=None, start_date=None, end_date=None, logger=None) -> List[Dict[str, str]]:
    base = source.get("url") or "https://st-germain.com/events/"
    name = source.get("name") or "St. Germain Chamber (WP)"
    own_session = False
    if session is None:
        import requests
        session = requests.Session()
        own_session = True
    try:
        archive_pages = [base] + [urljoin(base, f"page/{i}/") for i in range(2, 6)]
        links: Set[str] = set()
        for url in archive_pages:
            try:
                r = session.get(url, timeout=30)
                if not r.ok:
                    continue
                for m in re.finditer(r'href=["\'](https?://(?:www\.)?st-germain\.com/(?:event|events)/[^"\']+)["\']', r.text, flags=re.I):
                    links.add(m.group(1))
            except Exception:
                continue

        out: List[Dict[str, str]] = []
        for href in sorted(links):
            try:
                r = session.get(href, timeout=30)
                if not r.ok:
                    continue
                html = r.text
                title = _page_h1(html) or "(untitled)"
                # Prefer Event Info section if present
                sect = re.search(r'(?is)(<h2[^>]*>\s*Event\s*Info\s*</h2>.*?)(?:<h2|\Z)', html)
                blob = sect.group(1) if sect else html
                start_iso, end_iso = _parse_date_time(blob)
                if not start_iso:
                    start_iso, end_iso = _parse_date_time(html)
                if not start_iso:
                    continue
                # Location span you identified
                loc_m = re.search(r'(?is)<span[^>]*class="[^"]*x-text-content-text-primary[^"]*"[^>]*>(.*?)</span>', html)
                loc = _clean_text(loc_m.group(1)) if loc_m else None

                ev = {
                    "title": title,
                    "start": start_iso, "end": end_iso,
                    "start_utc": start_iso, "end_utc": end_iso,
                    "location": loc,
                    "url": href,
                    "source": name,
                    "_source": "stgermain_wp",
                }
                # Window filter (naive)
                if start_date and end_date:
                    try:
                        dt = datetime.fromisoformat(start_iso.split("+")[0])
                        if start_date <= dt <= end_date:
                            out.append(ev)
                    except Exception:
                        out.append(ev)
                else:
                    out.append(ev)
            except Exception:
                continue

        if logger:
            try: logger.debug(f"[stgermain_wp] parsed events: {len(out)}")
            except Exception: pass
        return out
    finally:
        if own_session:
            try: session.close()
            except Exception: pass
