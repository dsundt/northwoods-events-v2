from __future__ import annotations

from typing import List
from icalendar import Calendar, Event as IcsEvent
from datetime import datetime, timezone
import os

from src.models import Event
from src.sources import SourceCfg
from src.util import PUBLIC_DIR, BY_SOURCE_DIR


def _ics_for(events: List[Event], cal_name: str) -> Calendar:
    cal = Calendar()
    cal.add("prodid", "-//Northwoods Events v2.0//EN")
    cal.add("version", "2.0")
    cal.add("method", "PUBLISH")
    cal.add("x-wr-calname", cal_name)
    now = datetime.now(timezone.utc)
    for e in events:
        if not e.start_utc:
            continue
        ics_e = IcsEvent()
        ics_e.add("uid", e.uid)
        ics_e.add("summary", e.title or "(no title)")
        if e.description:
            ics_e.add("description", e.description)
        if e.url:
            ics_e.add("url", e.url)
        if e.location:
            ics_e.add("location", e.location)
        ics_e.add("dtstamp", now)
        ics_e.add("dtstart", e.start_utc)
        if e.end_utc:
            ics_e.add("dtend", e.end_utc)
        cal.add_component(ics_e)
    return cal


def write_per_source_ics(source: SourceCfg, events: List[Event]) -> str:
    """
    Write a per-source ICS file under public/by-source/<slug>.ics
    Returns the file path written.
    """
    os.makedirs(BY_SOURCE_DIR, exist_ok=True)
    filename = f"{source.slug}.ics"
    path = os.path.join(BY_SOURCE_DIR, filename)
    cal = _ics_for(events, f"Northwoods – {source.name}")
    with open(path, "wb") as f:
        f.write(cal.to_ical())
    return path


def write_combined_ics(all_events: List[Event]) -> str:
    """
    Write the combined ICS file under public/combined.ics
    Returns the file path written.
    """
    os.makedirs(PUBLIC_DIR, exist_ok=True)
    path = os.path.join(PUBLIC_DIR, "combined.ics")
    cal = _ics_for(all_events, "Northwoods – Combined")
    with open(path, "wb") as f:
        f.write(cal.to_ical())
    return path
