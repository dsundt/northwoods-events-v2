from typing import List, Optional
from bs4 import BeautifulSoup
from dateutil import parser as dtp
from datetime import datetime, timezone
import hashlib

from src.models import Event


def parse_simpleview_html(html: bytes, source_name: str, calendar: str, base_url: Optional[str] = None) -> List[Event]:
    """
    Simpleview list view parser (targets /events/?view=list).
    Heuristics:
      - Container: cards/items under list results (varies by theme)
      - Title link: first anchor inside card heading
      - Time: <time datetime=...> when present, else date/time text within item
      - Location/description: common Simpleview classes and fallbacks
    Notes:
      - Paginates server-side; this parser handles the page that was fetched.
      - If the site hides times on the list page, we derive from text; otherwise
        customers may switch to ICS if Simpleview exposes it.
    """
    soup = BeautifulSoup(html, "html.parser")
    events: List[Event] = []

    # Broad candidate selection across known Simpleview themes
    candidates = soup.select(
        ".l-event-list .c-card, "
        ".event-list .event, "
        ".event-card, "
        "li.event, "
        "article.event, "
        ".result-item, "
        ".tiles .tile"
    )
    if not candidates:
        # Fallback: look for anchors pointing to event details
        candidates = soup.find_all("a", href=True)

    for el in candidates:
        title_el = _first_of(el, [
            ".c-card__heading a",
            ".event-title a",
            "a[href*='/event/']",
            "a"
        ])
        if not title_el:
            # If the "candidate" is itself an <a>, use it
            if getattr(el, "name", "") == "a":
                title_el = el
            else:
                continue

        title = title_el.get_text(strip=True) or "(no title)"
        url = title_el.get("href")

        # Time extraction
        t_start = _first_time(el)
        if t_start is None:
            # Some list pages show a single "Date" string without <time>
            t_start = _parse_maybe(el.get_text(" ", strip=True))
        if t_start is None:
            # If nothing parseable, skip; detail pages often contain the full date,
            # but we keep the list parser conservative to avoid bad dates.
            continue

        start_utc = _to_utc(t_start)
        end_utc = None

        location = _first_text(el, [
            ".event-location",
            ".c-card__meta--location",
            ".location",
            "[itemprop='location']",
        ])
        desc = _first_text(el, [
            ".event-description",
            ".c-card__summary",
            ".summary",
            ".teaser",
            "[itemprop='description']",
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


def _first_of(el, selectors):
    for sel in selectors:
        cand = el.select_one(sel)
        if cand:
            return cand
    return None


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


def _first_text(el, selectors) -> str:
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


def _stable_uid(source: str, title: str, start_utc: datetime, url: Optional[str]) -> str:
    h = hashlib.sha1()
    h.update((source or "").encode("utf-8"))
    h.update((title or "").encode("utf-8"))
    h.update(start_utc.isoformat().encode("utf-8"))
    h.update((url or "").encode("utf-8"))
    return h.hexdigest() + "@northwoods-v2"
