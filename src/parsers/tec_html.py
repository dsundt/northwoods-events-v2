# src/parsers/tec_html.py
import re
import json
from html import unescape
from datetime import datetime, date
from urllib.parse import urljoin

from src.util import expand_tec_ics_urls

# -------------------- call-shape normalization --------------------

def _coerce_signature(args, kwargs):
    """
    Supports these shapes:
      (source)
      (source, session)
      (source, start_date, end_date)
      (source, session, start_date, end_date)
      plus kwargs: start_date=..., end_date=..., session=...

    Returns: source, session|None, start_date|None, end_date|None
    """
    source = args[0] if args else kwargs.get("source")
    session = kwargs.get("session")
    start_date = kwargs.get("start_date")
    end_date = kwargs.get("end_date")

    pos = list(args[1:])
    # If the first positional looks like a session (has .get attr), treat as session.
    if pos and hasattr(pos[0], "get"):
        session = pos.pop(0)

    # Remaining two (if any) are start_date / end_date
    if pos:
        start_date = pos.pop(0)
    if pos:
        end_date = pos.pop(0)

    return source, session, start_date, end_date

def _src_url(source):
    if isinstance(source, str):
        return source
    if not source:
        return None

    url = source.get("url") if isinstance(source, dict) else None
    calendar = None
    if isinstance(source, dict):
        calendar = source.get("calendar") or source.get("calendar_url")

    if url:
        lowered = url.lower()
        looks_like_feed = (
            lowered.endswith(".rss")
            or "/rss" in lowered
            or lowered.endswith("/feed")
            or lowered.endswith("/feed/")
        )
        if looks_like_feed and calendar:
            return calendar
        return url

    return calendar

def _src_name(source, default="TEC HTML"):
    return default if isinstance(source, str) else (source.get("name") or default)

def _clean_html(s):
    if not s:
        return None
    s = re.sub(r"(?is)<script[^>]*>.*?</script>|<style[^>]*>.*?</style>", "", s)
    s = re.sub(r"(?is)<br\s*/?>", "\n", s)
    s = re.sub(r"(?is)<[^>]+>", "", s)
    s = unescape(s).strip()
    s = re.sub(r"[ \t]+\n", "\n", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s

def _first(pattern, text, flags=re.IGNORECASE | re.DOTALL):
    m = re.search(pattern, text, flags)
    return m.group(1).strip() if m else None

# -------------------- tiny ICS reader (no external deps) --------------------

def _unfold_ics(text):
    lines = text.splitlines()
    out = []
    for ln in lines:
        if ln.startswith((" ", "\t")) and out:
            out[-1] += ln[1:]
        else:
            out.append(ln)
    return out

def _parse_ics_dt(val):
    try:
        if val.endswith("Z"):
            return datetime.strptime(val, "%Y%m%dT%H%M%SZ")
        if "T" in val:
            return datetime.strptime(val, "%Y%m%dT%H%M%S")
        return datetime.strptime(val, "%Y%m%d")
    except Exception:
        return None

def _parse_ics(text, source_name):
    events = []
    uid = title = location = url = None
    dtstart = dtend = None
    in_evt = False

    for ln in _unfold_ics(text):
        if ln.startswith("BEGIN:VEVENT"):
            in_evt = True
            uid = title = location = url = None
            dtstart = dtend = None
            continue
        if ln.startswith("END:VEVENT"):
            if in_evt:
                ev = {
                    "uid": uid or f"tec-{abs(hash((title or '', dtstart or '', url or '')))}",
                    "title": title or "(untitled)",
                    "start_utc": dtstart,
                    "end_utc": dtend,
                    "url": url,
                    "location": location,
                    "source": source_name,
                    "calendar": source_name,
                }
                events.append(ev)
            in_evt = False
            continue
        if not in_evt:
            continue

        m = re.match(r"([^:;]+)(?:;[^:]+)?:\s*(.*)$", ln)
        if not m:
            continue
        k, v = m.group(1).upper(), m.group(2).strip()

        if k == "UID":
            uid = v
        elif k == "SUMMARY":
            title = unescape(v)
        elif k == "LOCATION":
            location = unescape(v)
        elif k == "URL":
            url = v
        elif k.startswith("DTSTART"):
            d = _parse_ics_dt(v)
            if d:
                dtstart = d.strftime("%Y-%m-%d %H:%M:%S")
        elif k.startswith("DTEND"):
            d = _parse_ics_dt(v)
            if d:
                dtend = d.strftime("%Y-%m-%d %H:%M:%S")

    return events

# -------------------- HTML fallbacks (JSON-LD / TEC list) --------------------

def _events_from_jsonld(html, source_name):
    out = []
    for m in re.finditer(r'(?is)<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', html):
        try:
            blob = unescape(m.group(1)).strip()
            data = json.loads(blob)
            items = data if isinstance(data, list) else [data]
        except Exception:
            continue
        for it in items:
            try:
                if not isinstance(it, dict):
                    continue
                t = it.get("name") or it.get("headline")
                s = it.get("startDate")
                e = it.get("endDate")
                loc = it.get("location")
                url = it.get("url")
                if isinstance(loc, dict):
                    loc = loc.get("name") or (loc.get("address") if isinstance(loc.get("address"), str) else None)

                def norm(x):
                    if not x:
                        return None
                    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
                        try:
                            return datetime.strptime(x, fmt).strftime("%Y-%m-%d %H:%M:%S")
                        except Exception:
                            pass
                    return None

                start_s = norm(s)
                end_s = norm(e)
                if t and start_s:
                    uid = f"tec-{abs(hash((t, start_s, url or '')))}"
                    out.append({
                        "uid": uid,
                        "title": _clean_html(t),
                        "start_utc": start_s,
                        "end_utc": end_s,
                        "url": url,
                        "location": _clean_html(loc),
                        "source": source_name,
                        "calendar": source_name,
                    })
            except Exception:
                continue
    return out

def _events_from_list_markup(html, base_url, source_name):
    events = []

    # TEC often embeds JSON in data-tribe-event-json
    for m in re.finditer(r'(?is)data-tribe-event-json=["\'](.*?)["\']', html):
        try:
            data = json.loads(unescape(m.group(1)))
        except Exception:
            continue
        if not isinstance(data, dict):
            continue
        t = data.get("title")
        s = data.get("startDate")
        e = data.get("endDate")
        u = data.get("url")

        def norm(x):
            if not x: return None
            for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S"):
                try:
                    return datetime.strptime(x, fmt).strftime("%Y-%m-%d %H:%M:%S")
                except Exception:
                    pass
            return None

        start_s = norm(s)
        end_s = norm(e)
        if t and start_s:
            uid = f"tec-{abs(hash(((u or ''), t, start_s or '')))}"
            events.append({
                "uid": uid,
                "title": _clean_html(t),
                "start_utc": start_s,
                "end_utc": end_s,
                "url": u,
                "location": _clean_html((data.get("venue") or {}).get("venue") if isinstance(data.get("venue"), dict) else data.get("venue")),
                "source": source_name,
                "calendar": source_name,
            })

    # Article-based fallback
    if not events:
        for block in re.finditer(r'(?is)<article[^>]*?class="[^"]*tribe-events[^"]*".*?</article>', html):
            b = block.group(0)
            title = _clean_html(_first(r'(?is)<a[^>]+class="[^"]*\btribe-[^"]*event[^"]*"[^>]*>(.*?)</a>', b))
            url = _first(r'(?is)<a[^>]+href=["\'](.*?)["\']', b)
            start_dt = _first(r'(?is)<time[^>]+datetime=["\'](.*?)["\']', b)

            start_s = None
            if start_dt:
                for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%d"):
                    try:
                        start_s = datetime.strptime(start_dt, fmt).strftime("%Y-%m-%d %H:%M:%S")
                        break
                    except Exception:
                        pass

            if title and start_s:
                uid = f"tec-{abs(hash(((url or ''), title, start_s or '')))}"
                events.append({
                    "uid": uid,
                    "title": title,
                    "start_utc": start_s,
                    "end_utc": None,
                    "url": urljoin(base_url, url) if url else None,
                    "location": None,
                    "source": source_name,
                    "calendar": source_name,
                })

    return events

# -------------------- date filtering --------------------

def _coerce_date(x):
    if x is None:
        return None
    if isinstance(x, datetime):
        return x.date()
    if isinstance(x, date):
        return x
    if isinstance(x, str):
        # accept 'YYYY-MM-DD'
        try:
            return datetime.strptime(x.strip(), "%Y-%m-%d").date()
        except Exception:
            return None
    return None

def _filter_range(events, start_date, end_date):
    sd = _coerce_date(start_date)
    ed = _coerce_date(end_date)
    if not sd and not ed:
        return events

    def in_range(ev):
        s = ev.get("start_utc")
        if not s:
            return False
        try:
            dt = datetime.strptime(s, "%Y-%m-%d %H:%M:%S").date()
        except Exception:
            return False
        if sd and dt < sd:
            return False
        if ed and dt > ed:
            return False
        return True

    return [e for e in events if in_range(e)]

# -------------------- main entry --------------------

def fetch_tec_html(*args, **kwargs):
    """
    St. Germain TEC HTML fetcher (session optional).
    Strategy:
      1) Try ICS from calendar page (?ical=1 and common fallbacks)
      2) If no ICS, parse HTML (JSON-LD, then TEC list markup)
      3) Optionally filter to [start_date, end_date]
    """
    source, session, start_date, end_date = _coerce_signature(args, kwargs)
    base = _src_url(source)
    name = _src_name(source, "TEC HTML")
    if not base:
        return []

    # Create a local session if none provided
    own_session = False
    if session is None:
        import requests
        session = requests.Session()
        own_session = True

    try:
        # --- ICS first ---
        candidates = expand_tec_ics_urls(base, start_date, end_date)

        ics_text = None
        for u in candidates:
            try:
                r = session.get(u, timeout=30)
                if r.ok and "BEGIN:VCALENDAR" in r.text:
                    ics_text = r.text
                    break
            except Exception:
                continue

        events = []
        if ics_text:
            events = _parse_ics(ics_text, name)
            events = _filter_range(events, start_date, end_date)
            if events:
                return events

        # --- HTML fallbacks ---
        try:
            r = session.get(base, timeout=30)
            r.raise_for_status()
            html = r.text
        except Exception:
            return []

        events = _events_from_jsonld(html, name)
        if not events:
            events = _events_from_list_markup(html, base, name)

        events = _filter_range(events, start_date, end_date)
        return events

    finally:
        if own_session:
            try:
                session.close()
            except Exception:
                pass
