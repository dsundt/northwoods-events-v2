# src/ics_writer.py
from __future__ import annotations
from datetime import datetime
from typing import Dict, List
from pathlib import Path

from icalendar import Calendar, Event

def _to_ics(events: List[Dict]) -> Calendar:
    cal = Calendar()
    cal.add("prodid", "-//Northwoods Events v2//")
    cal.add("version", "2.0")
    for e in events:
        if not e.get("start_utc"):
            # skip events without a start datetime
            continue
        ev = Event()
        ev.add("uid", e.get("uid"))
        ev.add("summary", e.get("title") or "(untitled)")
        try:
            ev.add("dtstart", datetime.fromisoformat(e["start_utc"].replace(" ", "T")))
        except Exception:
            continue
        if e.get("end_utc"):
            try:
                ev.add("dtend", datetime.fromisoformat(e["end_utc"].replace(" ", "T")))
            except Exception:
                pass
        if e.get("url"):
            ev.add("url", e["url"])
        if e.get("location"):
            ev.add("location", e["location"])
        cal.add_component(ev)
    return cal

def write_combined_ics(all_events: List[Dict], output_path: str) -> None:
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    cal = _to_ics(all_events)
    with open(output_path, "wb") as f:
        f.write(cal.to_ical())

def write_per_source_ics(events_by_source: Dict[str, List[Dict]], dir_path: str) -> None:
    outdir = Path(dir_path)
    outdir.mkdir(parents=True, exist_ok=True)
    for slug, events in events_by_source.items():
        cal = _to_ics(events)
        with open(outdir / f"{slug}.ics", "wb") as f:
            f.write(cal.to_ical())
