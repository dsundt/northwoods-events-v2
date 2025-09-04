"""
ICS writers for northwoods-events-v2.

Provides two functions with the signatures expected by src/main.py:

    write_per_source_ics(events: List[dict], path: str) -> None
    write_combined_ics(events: List[dict], path: str) -> None

Both functions:
- Create parent directories as needed.
- Write a valid VCALENDAR even when events is empty (helps debugging).
- Normalize datetimes from ISO 8601 (UTC). Events without a valid start time are skipped.
- Include helpful calendar metadata (X-WR-CALNAME / X-WR-CALDESC) when available.

Assumed event shape (dict keys used if present):
    title        : str
    start_utc    : str  (ISO8601; treated/converted to UTC)
    end_utc      : str  (ISO8601; treated/converted to UTC) optional
    url          : str  optional
    location     : str  optional
    source       : str  optional (used for calendar name)
    calendar     : str  optional (used for calendar name/desc)

Dependencies: icalendar, python-dateutil (both already in requirements.txt).
"""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from typing import Iterable, List, Optional

from icalendar import Calendar, Event
from dateutil import parser as dtparser


def _ensure_parent_dir(path: str) -> None:
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)


def _to_utc_dt(iso_str: Optional[str]) -> Optional[datetime]:
    """Parse an ISO-ish string into an aware UTC datetime. Returns None if parsing fails or input missing."""
    if not iso_str or not str(iso_str).strip():
        return None
    try:
        dt = dtparser.isoparse(iso_str)
        if dt.tzinfo is None:
            # Treat naive as UTC to avoid accidental local conversions in runners.
            dt = dt.replace(tzinfo=timezone.utc)
        else:
            dt = dt.astimezone(timezone.utc)
        return dt
    except Exception:
        return None


def _new_calendar(name: Optional[str] = None, desc: Optional[str] = None) -> Calendar:
    cal = Calendar()
    cal.add("prodid", "-//northwoods-events-v2//ics//EN")
    cal.add("version", "2.0")
    if name:
        cal.add("X-WR-CALNAME", name)
    if desc:
        cal.add("X-WR-CALDESC", desc)
    return cal


def _add_event(cal: Calendar, ev: dict) -> bool:
    """
    Add a single event dict to the calendar.
    Returns True if added, False if skipped (e.g., missing/invalid start).
    """
    start_dt = _to_utc_dt(ev.get("start_utc"))
    if start_dt is None:
        return False  # cannot create VEVENT without DTSTART

    end_dt = _to_utc_dt(ev.get("end_utc"))
    title = (ev.get("title") or "Untitled Event").strip() or "Untitled Event"

    ical_ev = Event()
    ical_ev.add("uid", ev.get("uid") or f"{uuid.uuid4()}@northwoods")
    ical_ev.add("summary", title)
    ical_ev.add("dtstart", start_dt)

    if end_dt and end_dt >= start_dt:
        ical_ev.add("dtend", end_dt)

    url = (ev.get("url") or "").strip()
    if url:
        ical_ev.add("url", url)

    loc = (ev.get("location") or "").strip()
    if loc:
        ical_ev.add("location", loc)

    # Add source as an X-property for traceability
    src = (ev.get("source") or ev.get("calendar") or "").strip()
    if src:
        ical_ev.add("X-NORTHWOODS-SOURCE", src)

    cal.add_component(ical_ev)
    return True


def _events_to_calendar(events: Iterable[dict], *, cal_name: Optional[str] = None, cal_desc: Optional[str] = None) -> Calendar:
    cal = _new_calendar(cal_name, cal_desc)
    count = 0
    for ev in events:
        if _add_event(cal, ev):
            count += 1
    # Even if count == 0, we still return a valid VCALENDAR so the file exists for debugging.
    return cal


def _write_calendar(cal: Calendar, path: str) -> None:
    _ensure_parent_dir(path)
    with open(path, "wb") as f:
        f.write(cal.to_ical())


def write_per_source_ics(events: List[dict], path: str) -> None:
    """
    Write an ICS file for a single source.
    The calendar name/desc is derived from the first event that has 'calendar' or 'source'.
    """
    cal_name = None
    cal_desc = None

    # Try to infer a meaningful name/desc from the first event with a calendar/source field.
    for ev in events:
        name_from_ev = (ev.get("calendar") or ev.get("source") or "").strip()
        if name_from_ev:
            cal_name = name_from_ev
            cal_desc = f"Events from {name_from_ev}"
            break

    cal = _events_to_calendar(events, cal_name=cal_name, cal_desc=cal_desc)
    _write_calendar(cal, path)


def write_combined_ics(events: List[dict], path: str) -> None:
    """
    Write a combined ICS file with all events.
    Calendar name is fixed and descriptive.
    """
    cal_name = "Northwoods Events (Combined)"
    cal_desc = "Aggregated events from all configured sources"
    cal = _events_to_calendar(events, cal_name=cal_name, cal_desc=cal_desc)
    _write_calendar(cal, path)
