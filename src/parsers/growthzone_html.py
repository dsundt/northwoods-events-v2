# src/parsers/growthzone_html.py
import re
import json
from datetime import datetime, date
from html import unescape
from urllib.parse import urljoin

# -------------------- call-shape normalization --------------------

def _coerce_signature(args, kwargs):
    """
    Supports:
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
    if pos and hasattr(pos[0], "get"):  # looks like a requests.Session
        session = pos.pop(0)
    if pos:
        start_date = pos.pop(0)
    if pos:
        end_date = pos.pop(0)
    return source, session, start_date, end_date

def _src_url(source):
    return source if isinstance(source, str) else (source.get("url") if source else None)

def _src_name(source, default="GrowthZone"):
    return default if isinstance(source, str) else (source.get("name") or default)

# -------------------- utils --------------------

def _clean_html(s):
    if not s:
        return None
    s = re.sub(r"(?is)<script[^>]*>.*?</script>|<style[^>]*>.*?</style>", "", s)
    s = re.sub(r"(?is)<br\s*/?>", "\n", s)
    s = re.sub(r"(?is)<[^>]+>", "", s)
    s = unescape(s).strip()
    s = re.sub(r"[ \t]+\n", "\n", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s or None

def _coerce_date(x):
    if x is None:
        return None
    if isinstance(x, datetime):
        return x.date()
    if isinstance(x, date):
        return x
    if isinstance(x, str):
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
        ts = ev.get("start_utc")
        if not ts:
            return False
        try:
            dt = datetime.strptime(ts, "%Y-%m-%d %H:%M:%S").date()
        except Exception:
            return False
        if sd and dt < sd:
            return False
        if ed and dt > ed:
            return False
        return True

    return [e for e in events if in_range(e)]

def _norm_dt(x):
    if not x:
        return None
    v = x.strip()
    # normalize 'Z' to +00:00 for fromisoformat
    if v.endswith("Z"):
        v = v[:-1] + "+00:00"
    # Try a few common shapes
    for fn in (
        lambda s: datetime.fromisoformat(s),
        lambda s: datetime.strptime(s, "%Y-%m-%dT%H:%M:%S%z"),
        lambda s: datetime.strptime(s, "%Y-%m-%dT%H:%M:%S"),
        lambda s: datetime.strptime(s, "%Y-%m-%d"),
    ):
        try:
            return fn(v).strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            pass
    return None

def _jsonld_events(html):
    """Return list of dicts parsed from any application/ld+json blocks."""
    out = []
    for m in re.finditer(r'(?is)<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', html):
        blob = unescape(m.group(1)).strip()
        try:
            data = json.loads(blob)
        except Exception:
            continue
        if isinstance(data, list):
            out.extend([d for d in data if isinstance(d, dict)])
        elif isinstance(data, dict):
            out.append(data)
    return out

def _extract_location_from_block(html):
    """
    Only take the inner content of:
      <div class="mn-event-section mn-event-location">
        <div class="mn-event-content"> ...desired location html... </div>
      </div>
    """
    m = re.search(
        r'(?is)<div[^>]+class="[^"]*\bmn-event-section\b[^"]*\bmn-event-location\b[^"]*"[^>]*>'
        r'.*?<div[^>]+class="[^"]*\bmn-event-content\b[^"]*"[^>]*>(.*?)</div>',
        html,
    )
    if not m:
        return None
    return _clean_html(m.group(1))

def _extract_title(html):
    # Prefer the page H1 if present; otherwise fall back to JSON-LD name/headline upstream
    m = re.search(r'(?is)<h1[^>]*>(.*?)</h1>', html)
    return _clean_html(m.group(1)) if m else None

def _detail_to_event(detail_html, page_url, source_name):
    # 1) JSON-LD first (usually includes start/end and location)
    title = None
    start_s = end_s = None
    location = None
    url = page_url

    for obj in _jsonld_events(detail_html):
        if not isinstance(obj, dict):
            continue
        # Look for Event-like objects
        if obj.get("@type") in ("Event", ["Event"]) or ("startDate" in obj or "endDate" in obj or "name" in obj):
            title = title or obj.get("name") or obj.get("headline")
            start_s = start_s or _norm_dt(obj.get("startDate"))
            end_s = end_s or _norm_dt(obj.get("endDate"))
            loc = obj.get("location")
            if isinstance(loc, dict):
                # Prefer name; include address string if provided
                location = location or _clean_html(
                    (loc.get("name") or "") + ("\n" + loc.get("address") if isinstance(loc.get("address"), str) else "")
                )
            elif isinstance(loc, str):
                location = location or _clean_html(loc)
            url = obj.get("url") or url

    # 2) If dates still missing, try meta itemprops
    if not start_s:
        m = re.search(r'itemprop=["\']startDate["\'][^>]*content=["\']([^"\']+)["\']', detail_html, flags=re.I)
        if m:
            start_s = _norm_dt(m.group(1))
    if not end_s:
        m = re.search(r'itemprop=["\']endDate["\'][^>]*content=["\']([^"\']+)["\']', detail_html, flags=re.I)
        if m:
            end_s = _norm_dt(m.group(1))

    # 3) Title fallback
    title = title or _extract_title(detail_html) or "(untitled)"

    # 4) Location: STRICT block-only per your requirement
    explicit_loc = _extract_location_from_block(detail_html)
    if explicit_loc:
        location = explicit_loc

    uid = f"gz-{abs(hash((title or '', start_s or '', url or '')))}"
    return {
        "uid": uid,
        "title": title,
        "start_utc": start_s,
        "end_utc": end_s,
        "url": url,
        "location": location,
        "source": source_name,
        "calendar": source_name,
    }

# -------------------- main entry --------------------

def fetch_growthzone_html(*args, **kwargs):
    """
    GrowthZone (ChamberMaster) HTML fetcher.
    - Accepts optional session / date bounds
    - Finds detail links on the calendar page and parses each detail page
    - Dates from JSON-LD/meta; location ONLY from the mn-event-location block
    """
    source, session, start_date, end_date = _coerce_signature(args, kwargs)
    base = _src_url(source)
    name = _src_name(source, "GrowthZone")
    if not base:
        return []

    # Make a session if not provided
    own_session = False
    if session is None:
        import requests
        session = requests.Session()
        own_session = True

    try:
        # 1) Fetch calendar listing
        resp = session.get(base, timeout=30)
        resp.raise_for_status()
        html = resp.text

        # 2) Find detail URLs (absolute or relative)
        links = set()
        for m in re.finditer(r'href=["\'](https?://[^"\']*/events/details/[^"\']+)["\']', html, flags=re.I):
            links.add(m.group(1))
        for m in re.finditer(r'href=["\'](/events/details/[^"\']+)["\']', html, flags=re.I):
            links.add(urljoin(base, m.group(1)))

        events = []
        # 3) Visit each detail page and extract fields
        for href in sorted(links):
            try:
                r = session.get(href, timeout=30)
                if not r.ok:
                    continue
                ev = _detail_to_event(r.text, href, name)
                # Skip if no start date (prevents null-date clutter)
                if ev.get("start_utc"):
                    events.append(ev)
            except Exception:
                continue

        # 4) Optional date filtering
        events = _filter_range(events, start_date, end_date)
        return events

    finally:
        if own_session:
            try:
                session.close()
            except Exception:
                pass
