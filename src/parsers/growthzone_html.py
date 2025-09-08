# src/parsers/growthzone_html.py
import re
import json
from html import unescape
from datetime import datetime, date, time
from urllib.parse import urljoin

# ---- helpers ---------------------------------------------------------------

def _src_url(source):
    # Accept dict or string for backwards/forwards compatibility
    return source if isinstance(source, str) else (source.get("url") if source else None)

def _src_name(source, default="GrowthZone"):
    return default if isinstance(source, str) else (source.get("name") or default)

def _clean_html(s):
    if not s:
        return None
    # strip tags (lightweight, no bs4 dependency)
    s = re.sub(r"(?is)<script[^>]*>.*?</script>|<style[^>]*>.*?</style>", "", s)
    s = re.sub(r"(?is)<br\s*/?>", "\n", s)
    s = re.sub(r"(?is)<[^>]+>", "", s)
    # collapse whitespace
    s = unescape(s).strip()
    s = re.sub(r"[ \t]+\n", "\n", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s

def _first_group(pattern, text, flags=re.IGNORECASE|re.DOTALL):
    m = re.search(pattern, text, flags)
    return m.group(1).strip() if m else None

def _parse_time_range(date_text, time_text):
    """
    date_text like 'September 14, 2025'
    time_text like '2:00 PM - 4:30 PM CDT' OR 'All Day'
    returns (start_dt_str, end_dt_str) or (date-only start with 00:00, end None)
    """
    if not date_text:
        return (None, None)

    # normalize date
    date_text = date_text.strip()
    dt_obj = None
    for fmt in ("%B %d, %Y", "%b %d, %Y", "%m/%d/%Y"):
        try:
            dt_obj = datetime.strptime(date_text, fmt).date()
            break
        except Exception:
            pass

    if dt_obj is None:
        return (None, None)

    if not time_text or re.search(r"\ball\s*day\b", time_text, re.I):
        start = datetime.combine(dt_obj, time(0, 0))
        return (start.strftime("%Y-%m-%d %H:%M:%S"), None)

    # extract "start - end" times; tolerate timezone suffix
    # examples:
    #  "10:00 AM - 10:30 AM CDT"
    #  "5:00 PM - 7:00 PM"
    #  "9:00 AM"
    times = re.split(r"\s*-\s*", time_text.split("  ")[0].strip())
    def _parse_clock(tstr):
        tstr = re.sub(r"\s+[A-Z]{2,4}$", "", tstr.strip())  # drop trailing timezone token if present
        for tf in ("%I:%M %p", "%I %p", "%H:%M", "%H"):
            try:
                return datetime.strptime(tstr, tf).time()
            except Exception:
                pass
        return None

    start_t = _parse_clock(times[0]) if times else None
    end_t   = _parse_clock(times[1]) if len(times) > 1 else None

    if not start_t and not end_t:
        # fallback: date only
        start = datetime.combine(dt_obj, time(0, 0))
        return (start.strftime("%Y-%m-%d %H:%M:%S"), None)

    start_dt = datetime.combine(dt_obj, start_t or time(0,0))
    end_dt   = datetime.combine(dt_obj, end_t) if end_t else None
    return (start_dt.strftime("%Y-%m-%d %H:%M:%S"),
            end_dt.strftime("%Y-%m-%d %H:%M:%S") if end_dt else None)

def _extract_json_ld(html):
    # Find Event JSON-LD if GrowthZone happens to inject it
    out = {}
    for m in re.finditer(r'(?is)<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', html):
        try:
            data = json.loads(unescape(m.group(1)))
        except Exception:
            continue
        # JSON-LD can be dict or list
        blobs = data if isinstance(data, list) else [data]
        for b in blobs:
            if not isinstance(b, dict):
                continue
            if b.get("@type") in ("Event", ["Event"]):
                if b.get("startDate"):
                    out["start"] = b.get("startDate")
                if b.get("endDate"):
                    out["end"] = b.get("endDate")
                if b.get("location"):
                    loc = b["location"]
                    if isinstance(loc, dict):
                        out["location"] = loc.get("name") or loc.get("address") or None
                    elif isinstance(loc, str):
                        out["location"] = loc
                if b.get("name"):
                    out["title"] = b.get("name")
                if out:
                    return out
    return {}

def _extract_location_block(html):
    """
    Prefer ONLY the content inside the specific GrowthZone block:
      <div class="mn-event-section mn-event-location"> ... <div class="mn-event-content"><div class="mn-raw ...">TEXT</div></div>
    If not found, fallback to strict 'Location:' capture (until the next section head).
    """
    # strict block
    m = re.search(
        r'(?is)<div[^>]+class="[^"]*\bmn-event-section\b[^"]*\bmn-event-location\b[^"]*"[^>]*>.*?<div[^>]+class="[^"]*\bmn-event-content\b[^"]*"[^>]*>\s*(.*?)\s*</div>\s*</div>',
        html
    )
    if m:
        return _clean_html(m.group(1))

    # strict label capture (stop before another labeled section head)
    m = re.search(
        r'(?is)>\s*Location:\s*</div>\s*<div[^>]+class="[^"]*\bmn-event-content\b[^"]*"[^>]*>\s*(.*?)\s*</div>',
        html
    )
    if m:
        return _clean_html(m.group(1))

    # generic "Location:" line capture; stop at next heading-like token
    m = re.search(
        r'(?is)\bLocation:\s*</?(?:div|span|p)[^>]*>(.*?)</?(?:div|span|p)>',
        html
    )
    if m:
        return _clean_html(m.group(1))

    # ultimate fallback: single-line after "Location:" until next known section key
    m = re.search(
        r'(?is)\bLocation:\s*(.*?)(?:\bDate/Time Information:|\bContact Information:|\bFees/Admission:|\bWebsite:|<h\d|\Z)',
        html
    )
    if m:
        return _clean_html(m.group(1))

    return None

def _parse_growthzone_detail(html, url, source_name):
    # title
    title = _first_group(r'(?is)<h1[^>]*id=["\']page-title["\'][^>]*>(.*?)</h1>', html) \
         or _first_group(r'(?is)<meta[^>]+property=["\']og:title["\'][^>]+content=["\'](.*?)["\']', html)

    # primary: explicit labeled fields
    date_text = _first_group(r'(?is)>\s*Date:\s*</div>\s*<div[^>]*>\s*(.*?)\s*</div>', html) \
             or _first_group(r'(?is)\bDate:\s*(.*?)<', html)
    time_text = _first_group(r'(?is)>\s*Time:\s*</div>\s*<div[^>]*>\s*(.*?)\s*</div>', html) \
             or _first_group(r'(?is)\bTime:\s*(.*?)<', html)

    start_str, end_str = _parse_time_range(date_text, time_text)

    # secondary: JSON-LD if dates still missing
    if not start_str:
        j = _extract_json_ld(html)
        if j.get("start"):
            # normalize common date formats
            try:
                dt = j["start"]
                # tolerate ISO or "YYYY-MM-DD" or "YYYY-MM-DDTHH:MM"
                for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
                    try:
                        d = datetime.strptime(dt, fmt)
                        start_str = d.strftime("%Y-%m-%d %H:%M:%S")
                        break
                    except Exception:
                        pass
            except Exception:
                pass
        if j.get("end") and not end_str:
            for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
                try:
                    d = datetime.strptime(j["end"], fmt)
                    end_str = d.strftime("%Y-%m-%d %H:%M:%S")
                    break
                except Exception:
                    pass
        if not title and j.get("title"):
            title = j["title"]

    location = _extract_location_block(html)

    # uid: stable-ish from URL
    uid = f"gz-{abs(hash((url, title or '', start_str or '')))}"

    return {
        "uid": uid,
        "title": _clean_html(title) or "(untitled)",
        "start_utc": start_str,
        "end_utc": end_str,
        "url": url,
        "location": location,
        "source": source_name,
        "calendar": source_name,
    }

# ---- main fetcher ----------------------------------------------------------

def fetch_growthzone_html(source, session, start_date=None, end_date=None):
    """
    HTML scraper for GrowthZone.
    - Accepts source dict or URL string.
    - If given a calendar/search page, finds detail links and parses each event page for Date/Time and Location.
    - If given a direct detail URL, parses that single event.
    - Returns a list of normalized event dicts.
    """
    base_url = _src_url(source)
    name = _src_name(source, "GrowthZone")
    if not base_url:
        return []

    # If already a detail page, just parse one.
    if re.search(r"/events/details/", base_url):
        r = session.get(base_url, timeout=30)
        r.raise_for_status()
        return [_parse_growthzone_detail(r.text, base_url, name)]

    # Otherwise, treat as calendar index: gather detail links.
    r = session.get(base_url, timeout=30)
    r.raise_for_status()
    html = r.text

    # Primary: collect all /events/details/ links present on the page
    links = set(re.findall(r'href=["\'](\/events\/details\/[^"\']+)["\']', html, re.I))
    # Secondary: also look for "events/search" result links if present in markup
    links |= set(re.findall(r'href=["\'](\/events\/details\/[^"\']+?)["\']', html, re.I))

    # If the calendar page is sparse (JS-driven), try a generic "search" fallback over a wide window.
    if not links:
        # build a plausible search URL window if the domain supports it
        # e.g., /events/search?from=09/01/2025&to=01/31/2026
        try:
            today = datetime.utcnow().date()
            from_s = today.strftime("%m/%d/%Y")
            to_s = (date(today.year + (today.month + 4 > 12), ((today.month + 4 - 1) % 12) + 1, 1) - datetime.resolution).strftime("%m/%d/%Y")
            search_rel = f"/events/search?from={from_s}&to={to_s}"
            sr = session.get(urljoin(base_url, search_rel), timeout=30)
            if sr.ok:
                links |= set(re.findall(r'href=["\'](\/events\/details\/[^"\']+)["\']', sr.text, re.I))
        except Exception:
            pass

    events = []
    for rel in sorted(links):
        try:
            url = urljoin(base_url, rel)
            ev = session.get(url, timeout=30)
            ev.raise_for_status()
            events.append(_parse_growthzone_detail(ev.text, url, name))
        except Exception:
            # continue on per-event failures
            continue

    return events
