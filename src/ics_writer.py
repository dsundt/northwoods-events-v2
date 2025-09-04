from __future__ import annotations
from typing import List, Dict
from icalendar import Calendar, Event
from datetime import datetime
from dateutil import parser as dtp
from pathlib import Path

def _to_ics(events: List[Dict]) -> Calendar:
    cal = Calendar()
    cal.add("prodid", "-//northwoods-events-v2//")
    cal.add("version", "2.0")
    for ev in events:
        e = Event()
        e.add("uid", ev["uid"])
        e.add("summary", ev["title"])
        e.add("url", ev["url"])
        if ev.get("location"):
            e.add("location", ev["location"])
        # Times
        start = dtp.parse(ev["start_utc"])
        e.add("dtstart", start)
        if ev.get("end_utc"):
            e.add("dtend", dtp.parse(ev["end_utc"]))
        cal.add_component(e)
    return cal

def write_per_source_ics(outdir: Path, grouped: Dict[str, List[Dict]]) -> List[str]:
    outdir.mkdir(parents=True, exist_ok=True)
    written = []
    for slug, events in grouped.items():
        cal = _to_ics(events)
        path = outdir / f"{slug}.ics"
        with open(path, "wb") as f:
            f.write(cal.to_ical())
        written.append(str(path))
    return written

def write_combined_ics(path: Path, all_events: List[Dict]) -> str:
    cal = _to_ics(all_events)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as f:
        f.write(cal.to_ical())
    return str(path)
