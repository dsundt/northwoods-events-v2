# src/ics_writer.py
"""
ICS writer utilities.

Exports:
    - write_combined_ics(events, out_path)
    - write_per_source_ics(events_or_map, out_dir)

Both functions are tolerant to:
    * missing end times (defaults to start + 1 hour)
    * naive datetimes (treated as UTC)
    * input being a list of dict events (with keys like 'title','start_utc','end_utc','url','location','calendar')
      or, for per-source writing, a dict mapping {group_name: [events...]}

No external dependencies beyond icalendar and python-dateutil (already in requirements).
"""

from __future__ import annotations

import os
from datetime import timedelta, timezone
from typing import Dict, Iterable, List, Tuple

from dateutil import parser as dtparse
from icalendar import Calendar, Event

from src.util import slugify


# -------------------------
# Helpers
# -------------------------

UTC = timezone.utc


def _parse_dt(s: str | None):
    if not s:
        return None
    try:
        dt = dtparse.parse(s)
        # Treat naive as UTC
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        else:
            dt = dt.astimezone(UTC)
        return dt
    except Exception:
        return None


def _ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)


def _events_to_calendar(events: Iterable[dict], cal_name: str = "Northwoods Events") -> Calendar:
    cal = Calendar()
    cal.add("prodid", "-//northwoods-events-v2//EN")
    cal.add("version", "2.0")
    cal.add("calscale", "GREGORIAN")
    cal.add("X-WR-CALNAME", cal_name)

    for ev in events:
        title = (ev.get("title") or "Untitled").strip()
        url = ev.get("url")
        location = (ev.get("location") or "").strip() or None
        uid = ev.get("uid") or f"{abs(hash(url or title)) % 10**10}@northwoods-v2"

        start_dt = _parse_dt(ev.get("start_utc"))
        end_dt = _parse_dt(ev.get("end_utc"))

        if start_dt is None and end_dt is None:
            # skip events without any time info
            continue
        if start_dt is None and end_dt is not None:
            # fabricate a start one hour before end
            start_dt = end_dt - timedelta(hours=1)
        if end_dt is None and start_dt is not None:
            end_dt = start_dt + timedelta(hours=1)

        ical_ev = Event()
        ical_ev.add("uid", uid)
        ical_ev.add("summary", title)

        # RFC5545 prefers UTC for date-times
        ical_ev.add("dtstart", start_dt)
        ical_ev.add("dtend", end_dt)

        if location:
            ical_ev.add("location", location)
        if url:
            ical_ev.add("url", url)

        cal.add_component(ical_ev)

    return cal


# -------------------------
# Public API
# -------------------------

def write_combined_ics(events: Iterable[dict], out_path: str) -> Tuple[int, str]:
    """
    Write a single ICS file containing all events.

    Returns:
        (count_written, out_path)
    """
    _ensure_dir(os.path.dirname(out_path) or ".")
    cal_name = "Northwoods Combined"
    cal = _events_to_calendar(events, cal_name=cal_name)
    with open(out_path, "wb") as f:
        f.write(cal.to_ical())
    # Count events roughly by number of VEVENT lines
    count = sum(1 for _ in cal.subcomponents if isinstance(_, Event))
    return count, out_path


def _dedupe_slug(base: str, used: set[str]) -> str:
    slug = base
    suffix = 1
    while slug in used:
        suffix += 1
        slug = f"{base}-{suffix}"
    used.add(slug)
    return slug


def write_per_source_ics(events_or_map, out_dir: str) -> Dict[str, str]:
    """
    Write one ICS file per source/group.

    Args:
        events_or_map:
            - list[dict]: will be grouped by 'calendar' (falling back to 'source').
            - dict[str, list[dict]]: mapping display name -> events list.
        out_dir:
            target directory (e.g., 'public/by-source').

    Returns:
        dict: {slug: written_file_path}
    """
    _ensure_dir(out_dir)

    # Build groups
    meta: Dict[str, Dict[str, str]] = {}
    if isinstance(events_or_map, dict):
        groups = {}
        for key, value in events_or_map.items():
            if isinstance(value, dict) and "events" in value:
                groups[key] = list(value.get("events") or [])
                meta[key] = {
                    "display": value.get("name") or key,
                    "slug": value.get("slug") or key,
                }
            else:
                groups[key] = list(value or [])
                meta[key] = {
                    "display": key,
                    "slug": "",
                }
    else:
        groups = {}
        for ev in list(events_or_map or []):
            key = ev.get("calendar") or ev.get("source") or "Calendar"
            groups.setdefault(key, []).append(ev)
        for key in groups:
            meta[key] = {
                "display": key,
                "slug": "",
            }

    written: Dict[str, str] = {}
    used_slugs: set[str] = set()
    for name, evs in groups.items():
        if not evs:
            continue
        info = meta.get(name, {})
        display = info.get("display") or name
        slug_hint = info.get("slug") or ""
        base_slug = slug_hint or slugify(display, fallback="calendar")
        slug = _dedupe_slug(base_slug, used_slugs)
        cal = _events_to_calendar(evs, cal_name=display)
        path = os.path.join(out_dir, f"{slug}.ics")
        _ensure_dir(os.path.dirname(path))
        with open(path, "wb") as f:
            f.write(cal.to_ical())
        written[slug] = path

    return written
