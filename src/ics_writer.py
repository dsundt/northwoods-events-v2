from __future__ import annotations
import os
from typing import List, Dict
from icalendar import Calendar, Event
from datetime import datetime
from pathlib import Path

def _mk_public():
    Path("public").mkdir(parents=True, exist_ok=True)
    Path("public/by-source").mkdir(parents=True, exist_ok=True)

def _add_event(cal: Calendar, e: Dict):
    ev = Event()
    ev.add("uid", e.get("uid"))
    ev.add("summary", e.get("title") or "")
    if e.get("start_utc"):
        ev.add("dtstart", e["start_utc"])
    if e.get("end_utc"):
        ev.add("dtend", e["end_utc"])
    url = e.get("url")
    if url:
        ev.add("url", url)
    loc = e.get("location")
    if loc:
        ev.add("location", loc)
    cal.add_component(ev)

def write_per_source_ics(events: List[Dict]):
    _mk_public()
    # group by calendar (source label)
    buckets: Dict[str, List[Dict]] = {}
    for e in events:
        buckets.setdefault(e.get("calendar") or "unknown", []).append(e)

    for label, items in buckets.items():
        cal = Calendar()
        cal.add("prodid", "-//northwoods-events-v2//EN")
        cal.add("version", "2.0")
        for e in items:
            _add_event(cal, e)
        slug = (
            label.lower()
            .replace("(", "")
            .replace(")", "")
            .replace("&", "and")
            .replace(" ", "-")
            .replace("/", "-")
        )
        path = Path("public/by-source") / f"{slug}.ics"
        with open(path, "wb") as f:
            f.write(cal.to_ical())

def write_combined_ics(events: List[Dict]):
    _mk_public()
    cal = Calendar()
    cal.add("prodid", "-//northwoods-events-v2//EN")
    cal.add("version", "2.0")
    for e in events:
        _add_event(cal, e)
    with open("public/combined.ics", "wb") as f:
        f.write(cal.to_ical())
