from typing import List, Optional, Union
from icalendar import Calendar
from datetime import datetime, date, time, timezone
import hashlib

from src.models import Event


def parse_ics_feed(content: bytes, source_name: str, calendar: str) -> List[Event]:
    cal = Calendar.from_ical(content)
    events: List[Event] = []
    for comp in cal.walk():
        if comp.name != "VEVENT":
            continue
        title = _safe_str(comp.get("summary"))
        desc = _safe_str(comp.get("description"))
        url = _safe_str(comp.get("url"))
        location = _safe_str(comp.get("location"))

        dtstart = _to_utc(comp.get("dtstart"))
        dtend = _to_utc(comp.get("dtend")) if comp.get("dtend") else None

        uid = _stable_uid(source_name, title, dtstart, url)
        events.append(Event(
            uid=uid,
            title=title or "(no title)",
            description=desc,
            url=url,
            location=location,
            start_utc=dtstart,
            end_utc=dtend,
            source_name=source_name,
            calendar=calendar,
        ))
    return events


def _safe_str(v) -> str:
    if v is None:
        return ""
    if hasattr(v, "to_ical"):
        try:
            return v.to_ical().decode("utf-8", "ignore")
        except Exception:
            return str(v)
    if isinstance(v, list):
        return " ".join(str(x) for x in v)
    return str(v)


def _ensure_datetime_utc(v: Union[datetime, date]) -> datetime:
    if isinstance(v, date) and not isinstance(v, datetime):
        # All-day event: interpret as midnight UTC
        return datetime.combine(v, time.min).replace(tzinfo=timezone.utc)
    if isinstance(v, datetime):
        if v.tzinfo is None:
            v = v.replace(tzinfo=timezone.utc)
        return v.astimezone(timezone.utc)
    raise ValueError("Invalid datetime/date value")


def _to_utc(param) -> datetime:
    # param may be a vDatetime, vDate, or similar with .dt
    dt = param.dt if hasattr(param, "dt") else param
    return _ensure_datetime_utc(dt)


def _stable_uid(source: str, title: str, start: datetime, url: str) -> str:
    h = hashlib.sha1()
    h.update((source or "").encode("utf-8"))
    h.update((title or "").encode("utf-8"))
    h.update(start.isoformat().encode("utf-8"))
    h.update((url or "").encode("utf-8"))
    return h.hexdigest() + "@northwoods-v2"
