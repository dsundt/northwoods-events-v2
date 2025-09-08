# src/parsers/growthzone_html.py
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, List, Optional, Tuple
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from dateutil import parser as dp

from src.http import get
from src.models import Event


MONTH_RX = r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*"
TIME_RX = r"([0-2]?\d:[0-5]\d(?:\s?[AP]M)?)"
RANGE_SPLIT = re.compile(r"\s*[-–]\s*")

@dataclass
class ParsedEvent:
    title: str
    url: str
    start: Optional[datetime]
    end: Optional[datetime]
    location: Optional[str]
    uid: Optional[str]


def _first_text(el) -> Optional[str]:
    return el.get_text(" ", strip=True) if el else None


def _parse_json_ld_event(soup: BeautifulSoup) -> Tuple[Optional[datetime], Optional[datetime], Optional[str], Optional[str]]:
    """
    Return (start, end, location_name, uid) if JSON-LD with @type Event is present.
    """
    for script in soup.select('script[type="application/ld+json"]'):
      try:
        data = json.loads(script.string or "")
      except Exception:
        continue

      # JSON-LD can be dict, list, or @graph
      candidates: List[dict] = []
      if isinstance(data, dict):
          if data.get("@type") == "Event":
              candidates = [data]
          elif "@graph" in data and isinstance(data["@graph"], list):
              candidates = [x for x in data["@graph"] if isinstance(x, dict) and x.get("@type") == "Event"]
      elif isinstance(data, list):
          candidates = [x for x in data if isinstance(x, dict) and x.get("@type") == "Event"]

      for ev in candidates:
          start = ev.get("startDate") or ev.get("start") or ev.get("start_time")
          end = ev.get("endDate") or ev.get("end") or ev.get("end_time")
          loc_name = None
          uid = ev.get("identifier") or ev.get("@id") or ev.get("url")

          loc = ev.get("location")
          if isinstance(loc, dict):
              loc_name = loc.get("name") or _first_text(BeautifulSoup(loc.get("address", ""), "html.parser"))
          elif isinstance(loc, str):
              loc_name = loc

          start_dt = dp.parse(start) if start else None
          end_dt = dp.parse(end) if end else None
          return (start_dt, end_dt, loc_name, uid)

    return (None, None, None, None)


def _parse_dt_block_text(txt: str) -> Tuple[Optional[datetime], Optional[datetime]]:
    """
    Example inputs (GrowthZone detail):
      "Wednesday Sep 11, 2025 5:30 PM - 7:30 PM CDT"
      "Thursday Sep 25, 2025"
      "Sep 05, 2025 - Sep 06, 2025"
    """
    txt = " ".join(txt.split())
    # If there's a clear range "… - …"
    if RANGE_SPLIT.search(txt):
        parts = RANGE_SPLIT.split(txt)
        if len(parts) == 2:
            try:
                s = dp.parse(parts[0], fuzzy=True)
                e = dp.parse(parts[1], fuzzy=True)
                return s, e
            except Exception:
                pass
    # Single date/time
    try:
        s = dp.parse(txt, fuzzy=True)
        return s, None
    except Exception:
        return None, None


def _fallback_details(soup: BeautifulSoup) -> Tuple[Optional[datetime], Optional[datetime], Optional[str]]:
    """
    Scrape common GrowthZone detail page panels if JSON-LD is unavailable.
    """
    # GrowthZone often uses definition lists or label/value blocks
    # Look for a block that contains "Date and Time"
    labels = soup.find_all(text=re.compile(r"Date\s*and\s*Time", re.I))
    start, end = None, None
    for lab in labels:
        # The value can be in the same parent or a sibling
        container = lab.parent
        # Consider next siblings or following elements
        candidates = []
        if container:
            candidates.extend(container.find_all_next(limit=3))
        txts = [t for t in ([_first_text(container)] if container else []) + [_first_text(c) for c in candidates] if t]
        txt = " ".join(t for t in txts if t and re.search(MONTH_RX, t, re.I))
        if txt:
            s, e = _parse_dt_block_text(txt)
            if s:
                start, end = s, e
                break

    # Location: look for a label "Location" and grab adjacent text
    loc = None
    loc_labels = soup.find_all(text=re.compile(r"Location", re.I))
    for lab in loc_labels:
        par = lab.parent
        nearby = []
        if par:
            # Most of the time the location name/address is the next block/anchor
            for sib in par.next_siblings:
                if getattr(sib, "name", None):
                    nearby.append(_first_text(sib))
                    if len(nearby) > 1:
                        break
        text = " ".join([t for t in nearby if t] or [])
        if text:
            # Trim obvious boilerplate
            loc = re.sub(r"\s{2,}", " ", text).strip()
            if loc:
                break

    return start, end, loc


def _clean_title(t: str) -> str:
    return re.sub(r"\s+", " ", (t or "").strip())


def fetch_growthzone_html(source) -> Iterable[Event]:
    """
    Expects `source.url` to be a GrowthZone calendar _month_ URL or the
    /events/calendar listing. We will traverse to event detail pages.
    """
    base = source.url.rstrip("/") + "/"
    resp = get(base)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")

    # Find detail links (robust: anything that looks like a GrowthZone "events/details/..." link)
    links = set()
    for a in soup.select('a[href*="/events/details/"]'):
        href = a.get("href")
        if not href:
            continue
        links.add(urljoin(base, href))

    # If the listing has paginated months, also include obvious "Next" month
    # but keep it surgical: only current page to avoid overfetching.

    events: List[Event] = []
    for url in sorted(links):
        try:
            d = get(url)
            d.raise_for_status()
        except Exception:
            continue

        dsoup = BeautifulSoup(d.text, "html.parser")

        # Title
        title_el = dsoup.select_one("h1") or dsoup.find("h1", {"class": re.compile(r"(title|event)", re.I)})
        title = _clean_title(_first_text(title_el) or "")

        start, end, loc_name, uid = _parse_json_ld_event(dsoup)

        if not start:
            s2, e2, l2 = _fallback_details(dsoup)
            start = start or s2
            end = end or e2
            loc_name = loc_name or l2

        ev = Event(
            uid=str(uid or f"gz-{hash((title, url))}"),
            title=title or "Untitled",
            start_utc=start,
            end_utc=end,
            url=url,
            location=loc_name,
            source=source.name,
            calendar=source.name,
        )
        events.append(ev)

    return events
