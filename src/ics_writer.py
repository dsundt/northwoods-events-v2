from typing import List, Dict, Iterable
from icalendar import Calendar, Event as IcsEvent
from datetime import datetime, timezone
import hashlib
import os
import json

from src.models import Event


def _ics_for_events(events: List[Event], cal_name: str) -> Calendar:
    cal = Calendar()
    cal.add("prodid", "-//Northwoods Events v2.0//EN")
    cal.add("version", "2.0")
    cal.add("method", "PUBLISH")
    cal.add("x-wr-calname", cal_name)
    now = datetime.now(timezone.utc)
    for e in events:
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


def write_outputs(
    public_dir: str,
    events: List[Event],
    by_source: Dict[str, List[Event]],
    all_source_names: Iterable[str],
) -> None:
    """
    Writes:
      - public/combined.ics
      - public/by-source/<slug>.ics for **every enabled source**, even if it had 0 events
    """
    os.makedirs(public_dir, exist_ok=True)

    # Combined ICS (always written)
    combined = _ics_for_events(events, "Northwoods – Combined")
    with open(os.path.join(public_dir, "combined.ics"), "wb") as f:
        f.write(combined.to_ical())

    # Per-source ICS
    base = os.path.join(public_dir, "by-source")
    os.makedirs(base, exist_ok=True)

    # Ensure a file for every enabled source (even empty)
    for source_name in all_source_names:
        src_events = by_source.get(source_name, [])
        safe = _slugify(source_name)
        cal = _ics_for_events(src_events, f"Northwoods – {source_name}")
        with open(os.path.join(base, f"{safe}.ics"), "wb") as f:
            f.write(cal.to_ical())


def _slugify(name: str) -> str:
    cleaned = "".join(c.lower() if c.isalnum() else "-" for c in name).strip("-")
    while "--" in cleaned:
        cleaned = cleaned.replace("--", "-")
    if not cleaned:
        cleaned = hashlib.sha1(name.encode("utf-8")).hexdigest()[:8]
    return cleaned


def write_report(public_dir: str, report: dict) -> None:
    path = os.path.join(public_dir, "report.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
