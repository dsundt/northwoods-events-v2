# src/parsers/tec_html.py
# Dual-mode parser:
#  - TEC HTML (classic front-end markup)
#  - Eventastic (used by St. Germain) – parsed via generic WP archive structure
#
# Signature accepts extra args to match main.py calls.

from bs4 import BeautifulSoup
from datetime import datetime
from dateutil import parser as dtparse
from urllib.parse import urljoin
from src.fetch import get

def _text(el):
    return (el.get_text(" ", strip=True) if el else "").strip()

def _dt_guess(txt):
    if not txt:
        return None
    try:
        # allow ambiguous inputs; return naive UTC-like string
        dt = dtparse.parse(txt, fuzzy=True)
        return dt
    except Exception:
        return None

def _fmt(dt):
    if not dt:
        return None
    # emit as 'YYYY-MM-DD HH:MM:SS' to match existing report.json style
    return dt.strftime("%Y-%m-%d %H:%M:%S")

def _is_tec_html(soup):
    # Loose markers for TEC front-end
    return bool(
        soup.select_one(".tribe-events, [data-js='tribe-events-view'], .tribe-common")
    )

def _parse_tec_list(soup, base_url, calendar_name):
    events = []
    # Try modern list cards first
    cards = soup.select(".tribe-events-calendar-list__event, .tribe-events-calendar-list__event-row")
    if not cards:
        # Fallback – generic 'tribe-event' items
        cards = soup.select(".tribe-event, .tribe-events-list-event, article.tribe_events")

    for card in cards:
        a = card.select_one("a[href]")
        title = _text(card.select_one("h3, h2, .tribe-events-calendar-list__event-title, .tribe-event-title, .tribe-events-list-event-title"))
        href = a["href"] if a else None
        start = None
        end = None

        # Look for time tags first
        tstart = card.select_one("time[datetime]")
        if tstart and tstart.has_attr("datetime"):
            start = _dt_guess(tstart["datetime"])
        if not start:
            # Try text in date/time containers
            datebits = _text(card.select_one("[class*='time'], [class*='date'], .tribe-events-calendar-list__event-datetime"))
            start = _dt_guess(datebits)

        # End time (best-effort)
        tend = card.select("time[datetime]")
        if len(tend) > 1 and tend[1].has_attr("datetime"):
            end = _dt_guess(tend[1]["datetime"])

        loc = _text(card.select_one(".tribe-events-calendar-list__event-venue, .tribe-venue, .tribe-events-venue, .venue, .location"))
        evt = {
            "uid": None,  # filled by caller if desired
            "title": title or (href or "").rstrip("/").split("/")[-1].replace("-", " ").title(),
            "start_utc": _fmt(start),
            "end_utc": _fmt(end) if end else None,
            "url": urljoin(base_url, href) if href else None,
            "location": loc or None,
            "source": calendar_name,
            "calendar": calendar_name,
        }
        if evt["url"] and evt["title"]:
            events.append(evt)
    return events

def _parse_eventastic_archive(soup, base_url, calendar_name):
    # Eventastic archive pages tend to be simple WP loops: h2.entry-title > a + meta/date nearby
    events = []
    posts = soup.select("article, .hentry, .post")
    if not posts:
        # Try a simpler list (links under entry-title)
        posts = soup.select("h2.entry-title, h2 a[href]")

    for p in posts:
        # Title + URL
        a = p.select_one("h2.entry-title a[href]") or p.select_one("a[href]")
        title = _text(p.select_one("h2.entry-title")) or _text(a)
        href = a["href"] if a and a.has_attr("href") else None

        # Date: time[datetime] or text near meta/date elements
        t = p.select_one("time[datetime]")
        start = None
        if t and t.has_attr("datetime"):
            start = _dt_guess(t["datetime"])
        if not start:
            date_txt = _text(
                p.select_one(".entry-meta, .post-meta, .event-date, .date, .posted-on")
            )
            # If not on the card, check global meta around it
            if not date_txt and a:
                parent = p.parent
                if parent:
                    date_txt = _text(parent.select_one(".entry-meta, .event-date, time"))
            start = _dt_guess(date_txt)

        loc = _text(p.select_one(".venue, .location, .event-location"))
        evt = {
            "uid": None,
            "title": title or (href or "").rstrip("/").split("/")[-1].replace("-", " ").title(),
            "start_utc": _fmt(start),
            "end_utc": None,
            "url": urljoin(base_url, href) if href else None,
            "location": loc or None,
            "source": calendar_name,
            "calendar": calendar_name,
        }
        if evt["url"] and evt["title"]:
            events.append(evt)
    return events

def fetch_tec_html(source, start_date=None, end_date=None, session=None):
    """
    HTML fetcher that handles:
      * TEC HTML list pages
      * Eventastic (St. Germain) WordPress archive
    """
    base_url = source.get("url")
    name = source.get("name", source.get("id", "Calendar"))
    diag = {"mode": None, "counts": {}}

    resp = get(base_url)
    soup = BeautifulSoup(resp.text, "html.parser")

    if _is_tec_html(soup):
        diag["mode"] = "tec_html"
        events = _parse_tec_list(soup, base_url, name)
    else:
        diag["mode"] = "eventastic"
        events = _parse_eventastic_archive(soup, base_url, name)

    return events, {"ok": True, "error": "", "diag": diag}
