# src/parsers/stgermain_wp.py
from __future__ import annotations
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Set
from urllib.parse import urljoin

from .growthzone_html import (
    _clean_text, _parse_stgermain_dates, _parse_stgermain_location, _page_h1
)

def fetch_stgermain_wp(source, session=None, start_date=None, end_date=None, logger=None) -> List[Dict[str, Any]]:
    base = source.get("url")
    name = source.get("name") or "St. Germain Chamber (WP)"
    if not base: return []
    own_session = False
    if session is None:
        import requests
        session = requests.Session()
        own_session = True
    try:
        # Crawl archive pages (1..5)
        to_visit = [base] + [urljoin(base, f"page/{i}/") for i in range(2, 6)]
        links: Set[str] = set()
        for url in to_visit:
            try:
                if logger: logger.debug(f"[stgermain_wp] GET {url}")
                r = session.get(url, timeout=30)
                if not r.ok: continue
                for m in re.finditer(r'href=["\'](https?://(?:www\.)?st-germain\.com/(?:event|events)/[^"\']+)["\']', r.text, flags=re.I):
                    links.add(m.group(1))
            except Exception as e:
                if logger: logger.warning(f"[stgermain_wp] error on {url}: {e}")
                continue

        out: List[Dict[str, Any]] = []
        for href in sorted(links):
            try:
                if logger: logger.debug(f"[stgermain_wp] detail GET {href}")
                r = session.get(href, timeout=30)
                if not r.ok: continue
                html = r.text
                title = _page_h1(html) or "(untitled)"
                sect = re.search(r'(?is)(<h2[^>]*>\s*Event\s*Info\s*</h2>.*?)(?:<h2|\Z)', html)
                blob = sect.group(1) if sect else html
                start_iso, end_iso = _parse_stgermain_dates(blob)
                if not start_iso:
                    start_iso, end_iso = _parse_stgermain_dates(html)
                if not start_iso:
                    continue
                loc = _parse_stgermain_location(html)
                ev = {
                    "title": title,
                    "start": start_iso, "end": end_iso,
                    "start_utc": start_iso, "end_utc": end_iso,
                    "location": loc,
                    "url": href,
                    "source": name,
                    "_source": "stgermain_wp",
                }
                if start_date and end_date:
                    try:
                        dt = datetime.fromisoformat(start_iso.split("+")[0])
                    except Exception:
                        try:
                            dt = datetime.strptime(start_iso[:10], "%Y-%m-%d")
                        except Exception:
                            dt = None
                    if dt and (start_date <= dt <= end_date):
                        out.append(ev)
                    elif not dt:
                        out.append(ev)
                else:
                    out.append(ev)
            except Exception as e:
                if logger: logger.warning(f"[stgermain_wp] error parsing {href}: {e}")
                continue
        if logger: logger.debug(f"[stgermain_wp] parsed events: {len(out)}")
        return out
    finally:
        if own_session:
            try: session.close()
            except Exception: pass
