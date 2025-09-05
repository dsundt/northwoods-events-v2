# src/parsers/simpleview_html.py
# Simpleview events list parser with unified signature.

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

def fetch_simpleview_html(source, start_date=None, end_date=None, session=None):
    base_url = source.get("url")
    name = source.get("name", source.get("id", "Calendar"))
    resp = get(base_url)
    soup = BeautifulSoup(resp.text, "html.parser")

    events = []
    # Broad selectors for Simpleview cards:
    # anchor for each event (often /event/…)
    for a in soup.select('a[href*="/event/"]'):
        href = a.get("href")
        if not href:
            continue
        full = urljoin(base_url, href)
        # Title commonly near/inside the anchor or in a heading sibling
        title = _text(a) or _text(a.find(["h2", "h3"]))
        block = a.find_parent(["div", "li", "article"]) or soup
        date_txt = _text(block.select_one(".date, .event-date, time, [class*='date']"))
        start = _guess_dt(date_txt)
        loc = _text(block.select_one(".venue, .location, [class*='venue']"))

        evt = {
            "uid": None,
            "title": title or full,
            "start_utc": _fmt(start),
            "end_utc": None,
            "url": full,
            "location": loc or None,
            "source": name,
            "calendar": name,
        }
        if evt["title"]:
            events.append(evt)

    # De-dup by URL
    uniq = {}
    for e in events:
        uniq[e["url"]] = e
    events = list(uniq.values())
    return events, {"ok": True, "error": "", "diag": {"count": len(events)}}
