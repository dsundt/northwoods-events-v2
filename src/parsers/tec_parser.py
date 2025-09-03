from typing import List, Optional
from bs4 import BeautifulSoup
from dateutil import parser as dtp
from datetime import datetime, timezone
import hashlib

from src.models import Event


def parse_tec_html(html: bytes, source_name: str, calendar: str, base_url: Optional[str] = None) -> List[Event]:
    """
    The Events Calendar (Modern Tribe) list-like pages.
    Heuristics target common classes but fall back to generic parsing.
    """
    soup = BeautifulSoup(html, "html.parser")
    events: List[Event] = []

    candidates = soup.select(".tribe-events-calendar-list__event, .tribe-common-event, .tribe-events-calendar-list__event-row")
    if not candidates:
        candidates = soup.select("[class*='tribe'] article, [class*='tribe'] li")

    for el in candidates:
        title_el = el.select_one(".tribe-events-calendar-list__event-title a, a.tribe-event-url, a[href*='/event/']")
        title = (title_el.get_text(strip=True) if title_el else "").strip() or "(no title)"
        url = title_el.get("href") if title_el else None

        t_start = _first_time(el)
        t_end = _second_time(el)
        if t_start is None:
            date_text = el.get_text(" ", strip=True)
            t_start = _parse_maybe(date_text)
        if t_start is None:
            continue

        start_utc = _to_utc(t_start)
        end_utc = _to_utc(t_end) if t_end else None

        location = _extract_text(el, [
            ".tribe-events-venue",
            ".tribe-events-calendar-list__event-venue",
            ".tribe-events-venue-details"
        ])
        desc = _extract_text(el, [
            ".tribe-events-calendar-list__event-description",
            ".tribe-events-pro-description",
            ".tribe-events-event-description"
        ])

        uid = _stable_uid(source_name, title, start_utc, url)
        events.append(Event(
            uid=uid,
            title=title,
            description=desc,
            url=url,
            location=location,
            start_utc=start_utc,
            end_utc=end_utc,
            source_name=source_name,
            calendar=calendar,
        ))
    return events


def _first_time(el):
    t = el.find("time")
    if t and t.has_attr("datetime"):
        try:
            return dtp.parse(t["datetime"])
        except Exception:
            return None
    if t and t.get_text(strip=True):
        return _parse_maybe(t.get_text(strip=True))
    return None


def _second_time(el):
    times = el.find_all("time")
    if len(times) >= 2:
        t = times[1]
        if t and t.has_attr("datetime"):
            try:
                return dtp.parse(t["datetime"])
            except Exception:
                return None
        if t and t.get_text(strip=True):
            return _parse_maybe(t.get_text(strip=True))
    return None


def _parse_maybe(text: str):
    try:
        return dtp.parse(text, fuzzy=True)
    except Exception:
        return None


def _to_utc(dt) -> datetime:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _extract_text(el, selectors) -> str:
    for sel in selectors:
        cand = el.select_one(sel)
        if cand:
            return cand.get_text(" ", strip=True)
    return ""


def _stable_uid(source: str, title: str, start_utc: datetime, url: str) -> str:
    h = hashlib.sha1()
    h.update((source or "").encode("utf-8"))
    h.update((title or "").encode("utf-8"))
    h.update(start_utc.isoformat().encode("utf-8"))
    h.update((url or "").encode("utf-8"))
    return h.hexdigest() + "@northwoods-v2"
