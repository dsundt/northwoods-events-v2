# src/parsers/growthzone_html.py
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Dict, Tuple
import re
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from dateutil import parser as dtparse


@dataclass
class Source:
    id: str
    name: str
    url: str
    type: str


USER_AGENT = "northwoods-events-v2 (+https://dsundt.github.io/northwoods-events-v2/)"


def _get(url: str, timeout: int = 30) -> requests.Response:
    return requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=timeout)


def _clean(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()


def fetch_growthzone_html(src: Dict) -> Tuple[List[Dict], Dict]:
    """
    Parse GrowthZone events. Strategy:
    - If landing on /events/calendar (grid), follow "Events List View" -> /events/search
    - Parse list view items: title, date line, details URL
    """
    source = Source(
        id=src.get("id") or src["name"].lower().replace(" ", "-"),
        name=src["name"],
        url=src["url"],
        type=src["type"],
    )

    diag = {"source": source.id, "page_used": None, "notes": [], "count": 0}
    events: List[Dict] = []

    # 1) Fetch landing page
    r = _get(source.url)
    r.raise_for_status()
    html = r.text
    soup = BeautifulSoup(html, "html.parser")

    # 2) Prefer List View if available
    list_href = None
    # anchor with visible text "Events List View" (GrowthZone)
    for a in soup.find_all("a"):
        t = _clean(a.get_text())
        href = a.get("href") or ""
        if "events/search" in href or t.lower() == "events list view":
            list_href = urljoin(source.url, href)
            break

    # If the landing page is already list view or we didn't locate the link,
    # try a direct guess of /events/search; otherwise stay on given URL.
    candidates = []
    if list_href:
        candidates.append(list_href)
    elif "/events/search" in source.url:
        candidates.append(source.url)
    else:
        # common GrowthZone pattern
        base = source.url.rstrip("/")
        candidates.append(base.replace("/events/calendar", "/events/search"))

        # last resort: try /events/search directly off domain
        if "/events/" in base and "/search" not in base:
            root = base.split("/events/")[0]
            candidates.append(urljoin(root + "/", "/events/search"))

    # Ensure we at least try the original page as a fallback
    candidates.append(source.url)

    used_url = None
    list_soup = None
    for u in candidates:
        if not u or u == "None":
            continue
        try:
            rr = _get(u)
            if rr.status_code != 200:
                continue
            ss = BeautifulSoup(rr.text, "html.parser")
            # Heuristic: list view usually has many details links
            links = ss.select('a[href*="/events/details/"]')
            if links:
                used_url = u
                list_soup = ss
                break
        except Exception as e:
            diag["notes"].append(f"probe failed {u}: {e}")

    if not list_soup:
        # Fall back to the landing soup; we'll still try to parse something
        used_url = source.url
        list_soup = soup

    diag["page_used"] = used_url

    # 3) Extract items
    # GrowthZone list view typically renders items with anchors to /events/details/<slug>/<id>
    items = list_soup.select('a[href*="/events/details/"]')
    for a in items:
        title = _clean(a.get_text())
        href = urljoin(used_url, a.get("href") or "")
        # The date line is often near the anchor, sometimes in the parent container
        container = a.find_parent(["li", "div", "article"]) or a.parent

        text_blob = _clean(container.get_text(" ", strip=True))
        # Look for Month Day, Year pattern (with optional weekday/time)
        # Examples: "Monday Sep 1, 2025", "Sep 1, 2025 5:00 PM"
        m = re.search(
            r"(?:(Mon|Tue|Wed|Thu|Fri|Sat|Sun)\s+)?"
            r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)\.?\s+\d{1,2},\s+\d{4}(?:\s+\d{1,2}:\d{2}\s*(AM|PM))?",
            text_blob,
            flags=re.IGNORECASE,
        )

        start_dt = None
        if m:
            try:
                start_dt = dtparse.parse(m.group(0), fuzzy=True)
            except Exception:
                start_dt = None

        if not start_dt:
            # As a fallback, parse any ISO-like date in the blob
            m2 = re.search(r"\d{4}-\d{2}-\d{2}(?:[T\s]\d{2}:\d{2}(:\d{2})?)?", text_blob)
            if m2:
                try:
                    start_dt = dtparse.parse(m2.group(0), fuzzy=True)
                except Exception:
                    start_dt = None

        # If still unknown, skip (we don't want date-less entries)
        if not start_dt:
            diag["notes"].append(f"skip (no date): {title}")
            continue

        # Normalize TZ (naive -> UTC)
        if start_dt.tzinfo is None:
            start_dt = start_dt.replace(tzinfo=timezone.utc)

        ev = {
            "source_id": source.id,
            "title": title,
            "start": start_dt.isoformat(),
            "end": start_dt.isoformat(),
            "url": href,
            "location": None,
            "all_day": False,
        }
        events.append(ev)

    diag["count"] = len(events)
    return events, diag
