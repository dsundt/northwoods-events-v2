# src/ics_writer.py
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Dict, List, Optional

from icalendar import Calendar, Event


def _ensure_dir(path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)


def _to_dt(s: Optional[str]) -> Optional[datetime]:
    if not s:
        return None
    # Expect "YYYY-mm-dd HH:MM:SS" (UTC) in our pipeline
    try:
        dt = datetime.strptime(s, "%Y-%m-%d %H:%M:%S")
        return dt.replace(tzinfo=timezone.utc)
    except Exception:
        return None


def _events_to_calendar(events: List[Dict], cal_name: str, cal_desc: str) -> Calendar:
    cal = Calendar()
    cal.add("prodid", "-//northwoods-events-v2//EN")
    cal.add("version", "2.0")
    cal.add("X-WR-CALNAME", cal_name)
    cal.add("X-WR-CALDESC", cal_desc)

    for e in events:
        start = _to_dt(e.get("start_utc"))
        if not start:
            continue  # cannot write without a start
        end = _to_dt(e.get("end_utc"))
        ve = Event()
        ve.add("uid", e.get("uid") or f"{hash(e.get('url',''))}@northwoods-v2")
        ve.add("summary", e.get("title") or "Untitled Event")
        ve.add("dtstart", start)
        if end:
            ve.add("dtend", end)
        if e.get("url"):
            ve.add("url", e["url"])
        if e.get("location"):
            ve.add("location", e["location"])
        cal.add_component(ve)

    return cal


def _write_calendar(cal: Calendar, path: str) -> None:
    _ensure_dir(path)
    with open(path, "wb") as f:
        f.write(cal.to_ical())


def write_per_source_ics(events: List[Dict], path: str) -> None:
    """
    Write a per-source ICS file (path points at public/by-source/<slug>.ics).
    """
    cal_name = "Northwoods Events – Source"
    cal_desc = "Events for a single configured source"
    cal = _events_to_calendar(events, cal_name=cal_name, cal_desc=cal_desc)
    _write_calendar(cal, path)


def write_combined_ics(events: List[Dict], path: str) -> None:
    """
    Write the combined ICS file at public/combined.ics.
    """
    cal_name = "Northwoods Events (Combined)"
    cal_desc = "Aggregated events from all configured sources"
    cal = _events_to_calendar(events, cal_name=
