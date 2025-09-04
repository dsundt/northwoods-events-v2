from __future__ import annotations
from typing import List, Tuple, Dict, Any
from icalendar import Calendar
from src.fetch import get
from src.models import Event


def fetch_ics(url: str, start_date, end_date) -> Tuple[List[Event], Dict[str, Any]]:
    resp = get(url)
    cal = Calendar.from_ical(resp.content)
    evs: List[Event] = []
    for comp in cal.walk("vevent"):
        title = str(comp.get("summary") or "(no title)")
        dtstart = comp.get("dtstart")
        dtend = comp.get("dtend")
        desc = str(comp.get("description") or "") or None
        loc = str(comp.get("location") or "") or None
        url_e = str(comp.get("url") or "") or None

        start = getattr(dtstart, "dt", None)
        end = getattr(dtend, "dt", None)
        evs.append(Event(
            title=title,
            start_utc=start,
            end_utc=end,
            description=desc,
            url=url_e,
            location=loc,
        ))
    return evs, {"note": "ics parsed"}
