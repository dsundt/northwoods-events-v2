# src/parsers/growthzone_html.py
from __future__ import annotations
from datetime import datetime
from typing import Dict, List, Tuple
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from dateutil import parser as dtp
from src.fetch import get, session

_DATE_IN_URL = re.compile(r"-([01]\d)-([0-3]\d)-(\d{4})-")

def _extract_date_from_url(url: str) -> datetime | None:
    m = _DATE_IN_URL.search(url)
    if not m:
        return None
    mm, dd, yyyy = m.groups()
    try:
        return dtp.parse(f"{yyyy}-{mm}-{dd}")
    except Exception:
        return None

def _extract_datetime_from_detail(detail_html: str) -> datetime | None:
    soup = BeautifulSoup(detail_html, "html.parser")

    # 1) Try <time datetime="">
    t = soup.select_one("time[datetime]")
    if t and t.has_attr("datetime"):
        try:
            return dtp.parse(t["datetime"])
        except Exception:
            pass

    # 2) Try JSON-LD (schema.org Event)
    for script in soup.select('script[type="application/ld+json"]'):
        try:
            import json
            data = json.loads(script.string or "")
            # may be dict or list
            items = data if isinstance(data, list) else [data]
            for it in items:
                if isinstance(it, dict) and it.get("@type") in ("Event", "MusicEvent", "Festival"):
                    if it.get("startDate"):
                        return dtp.parse(it["startDate"])
        except Exception:
            continue

    # 3) Try common label text (very tolerant)
    text = soup.get_text("\n", strip=True)
    m = re.search(r"(?:Date|When)\s*[:\-]\s*(.+)", text, re.I)
    if m:
        try:
            return dtp.parse(m.group(1), fuzzy=True)
        except Exception:
            pass
    return None

def fetch_growthzone_html(src: Dict, start: datetime, end: datetime) -> Tuple[List[Dict], Dict]:
    """
    Parse GrowthZone calendar. We read the month grid(s) page for anchors,
    then parse date from URL slug; if missing, we fetch the detail page.
    """
    base = src["url"]
    s = session()
    resp = get(base, s=s, retries=1)
    soup = BeautifulSoup(resp.text, "html.parser")

    anchors = soup.select('a[href*="/events/details/"], a[href*="/events/details"]')
    events: List[Dict] = []
    months_diag = []
    seen = set()

    for a in anchors:
        href = a.get("href")
        if not href:
            continue
        url_abs = urljoin(base, href)
        if url_abs in seen:
            continue
        seen.add(url_abs)

        title = a.get_text(strip=True) or "(untitled)"
        dt_guess = _extract_date_from_url(url_abs)
        if not dt_guess:
            # visit detail for time
            try:
                detail_resp = get(url_abs, s=s, retries=1)
                dt_guess = _extract_datetime_from_detail(detail_resp.text)
            except Exception:
                dt_guess = None

        start_utc = dt_guess.strftime("%Y-%m-%d %H:%M:%S") if dt_guess else None

        events.append({
            "uid": f"gz-{hash(url_abs)}@northwoods-v2",
            "title": title,
            "start_utc": start_utc,
            "end_utc": None,
            "url": url_abs,
            "location": None,
            "source": src["name"],
            "calendar": src["name"],
        })

    diag = {"ok": bool(events), "error": "" if events else "No GrowthZone events found", "diag": {"found": len(events)}}
    return events, diag
