# src/parsers/simpleview_html.py
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Dict, Tuple
from urllib.parse import urljoin
import json
import re

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


def _parse_event_ldjson(soup: BeautifulSoup) -> Dict | None:
    # Prefer JSON-LD with @type Event
    for sc in soup.find_all("script", {"type": "application/ld+json"}):
        try:
            data = json.loads(sc.string or "")
        except Exception:
            continue
        # handle both object and list
        blocks = data if isinstance(data, list) else [data]
        for blk in blocks:
            if isinstance(blk, dict) and blk.get("@type") in ("Event", ["Event"]):
                name = blk.get("name") or ""
                start = blk.get("startDate")
                end = blk.get("endDate") or start
                location = None
                loc = blk.get("location")
                if isinstance(loc, dict):
                    location = loc.get("name") or None
                return {
                    "title": _clean(name),
                    "start": start,
                    "end": end,
                    "location": location,
                }
    return None


def fetch_simpleview_html(src: Dict) -> Tuple[List[Dict], Dict]:
    """
    Crawl Simpleview:
    1) Load events index.
    2) Collect anchors containing '/event/'.
    3) For each detail page, parse JSON-LD Event (preferred).
    4) Filter out past events and fix relative URLs.
    """
    source = Source(
        id=src.get("id") or src["name"].lower().replace(" ", "-"),
        name=src["name"],
        url=src["url"],
        type=src["type"],
    )

    diag = {"source": source.id, "page_used": source.url, "notes": [], "count": 0}
    events: List[Dict] = []

    r = _get(source.url)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")

    anchors = soup.select('a[href*="/event/"]')
    hrefs = []
    for a in anchors:
        href = a.get("href") or ""
        if "/event/" in href:
            full = urljoin(source.url, href)
            hrefs.append(full)

    # Deduplicate & cap to avoid over-fetching
    seen = set()
    hrefs_unique = []
    for h in hrefs:
        if h not in seen:
            seen.add(h)
            hrefs_unique.append(h)
    hrefs = hrefs_unique[:120]

    for ev_url in hrefs:
        try:
            rr = _get(ev_url)
            if rr.status_code != 200:
                continue
            ss = BeautifulSoup(rr.text, "html.parser")
            meta = _parse_event_ldjson(ss)

            title = None
            start_iso = None
            end_iso = None
            location = None

            if meta:
                title = meta["title"]
                if meta["start"]:
                    try:
                        start_iso = dtparse.parse(meta["start"]).astimezone(timezone.utc).isoformat()
                    except Exception:
                        start_iso = None
                if meta["end"]:
                    try:
                        end_iso = dtparse.parse(meta["end"]).astimezone(timezone.utc).isoformat()
                    except Exception:
                        end_iso = None
                location = meta.get("location")
            else:
                # Fallback: try to scrape visible date strings
                text = _clean(ss.get_text(" ", strip=True))
                # Example: "September 28, 2025 10:00 AM"
                m = re.search(
                    r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)\.?\s+\d{1,2},\s+\d{4}(?:\s+\d{1,2}:\d{2}\s*(AM|PM))?",
                    text,
                    flags=re.IGNORECASE,
                )
                if m:
                    try:
                        start_iso = dtparse.parse(m.group(0)).replace(tzinfo=timezone.utc).isoformat()
                        end_iso = start_iso
                    except Exception:
                        pass

                h1 = ss.find(["h1", "h2"])
                if h1:
                    title = _clean(h1.get_text())

            if not title or not start_iso:
                continue

            # Filter out past events
            if dtparse.parse(start_iso) < datetime.now(timezone.utc):
                continue

            events.append(
                {
                    "source_id": source.id,
                    "title": title,
                    "start": start_iso,
                    "end": end_iso or start_iso,
                    "url": ev_url,  # absolute via urljoin above
                    "location": location,
                    "all_day": False,
                }
            )
        except Exception as e:
            diag["notes"].append(f"detail fail {ev_url}: {e}")

    diag["count"] = len(events)
    return events, diag
