from typing import List, Optional
from bs4 import BeautifulSoup
from dateutil import parser as dtp
from datetime import datetime, timezone
import hashlib

from src.models import Event


def parse_growthzone_html(html: bytes, source_name: str, calendar: str, base_url: Optional[str] = None) -> List[Event]:
    """
    GrowthZone 'events/search' list pages.
    """
    soup = BeautifulSoup(html, "html.parser")
    events: List[Event] = []

    candidates = soup.select(".event-item, .gz-event, .gz-event-list-item, li, article")
    if not candidates:
        candidates = soup.find_all(True)

    for el in candidates:
        title_el = el.select_one("a[href*='EventDetails'], .gz-event-title a, .gz-event-title, a[href*='/event/']")
        if not title_el:
            continue
        title = title_el.get_text(strip=True) or "(no title)"
        url = title_el.get("href")

        t_start = _find_any_time(el)
        if t_start is None:
            txt = el.get_text(" ", strip=True)
            t_start = _parse_maybe(txt)
        if t_start is None:
            continue

        start_utc = _to_utc(t_start)
        end_utc = None

        location = _find_one(el, [".gz-event-location", ".location", ".venue", "[itemprop='location']"])
        desc = _find_one(el, [".gz-event-description", ".description", ".summary", "[itemprop='description']"])

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


def _find_any_time(el):
    t = el.find("time")
    if t and t.has_attr("datetime"):
        try:
            return dtp.parse(t["datetime"])
        except Exception:
            return None
    if t and t.get_text(strip=True):
        return _parse_maybe(t.get_text(strip=True))
    return None


def _find_one(el, selectors) -> str:
    for sel in selectors:
        cand = el.select_one(sel)
        if cand:
            return cand.get_text(" ", strip=True)
    return ""


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


def _stable_uid(source: str, title: str, start_utc: datetime, url: str) -> str:
    h = hashlib.sha1()
    h.update((source or "").encode("utf-8"))
    h.update((title or "").encode("utf-8"))
    h.update(start_utc.isoformat().encode("utf-8"))
    h.update((url or "").encode("utf-8"))
    return h.hexdigest() + "@northwoods-v2"
