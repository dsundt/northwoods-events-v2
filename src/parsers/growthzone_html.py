# src/parsers/growthzone_html.py
# GrowthZone list parser with unified signature.

from bs4 import BeautifulSoup
from dateutil import parser as dtparse
from urllib.parse import urljoin
from src.fetch import get

def _text(el):
    return (el.get_text(" ", strip=True) if el else "").strip()

def _guess_dt(txt):
    try:
        return dtparse.parse(txt, fuzzy=True)
    except Exception:
        return None

def _fmt(dt):
    return dt.strftime("%Y-%m-%d %H:%M:%S") if dt else None

def fetch_growthzone_html(source, start_date=None, end_date=None, session=None):
    base_url = source.get("url")
    name = source.get("name", source.get("id", "Calendar"))
    resp = get(base_url)
    soup = BeautifulSoup(resp.text, "html.parser")

    events = []
    # Typical GrowthZone list structure – be permissive:
    # Look for event cards linking to /events/details/
    cards = soup.select('a[href*="/events/details/"], .event-list a[href*="/events/details/"]')
    seen = set()
    for a in cards:
        href = a.get("href")
        if not href:
            continue
        full = urljoin(base_url, href)
        if full in seen:
            continue
        seen.add(full)

        title = _text(a)
        # Try to find a date snippet near the link
        container = a.find_parent(["div", "li", "article"]) or soup
        date_txt = _text(
            container.select_one(".date, .event-date, .cc-date, time, [class*='date']")
        )
        start = _guess_dt(date_txt)
        events.append({
            "uid": None,
            "title": title or full,
            "start_utc": _fmt(start),
            "end_utc": None,
            "url": full,
            "location": None,
            "source": name,
            "calendar": name,
        })

    return events, {"ok": True, "error": "", "diag": {"count": len(events)}}
