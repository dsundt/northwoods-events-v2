# src/parsers/tec_html.py
import re
from html import unescape
from datetime import datetime
from urllib.parse import urljoin, urlparse, urlunparse

def _src_url(source):
    return source if isinstance(source, str) else (source.get("url") if source else None)

def _src_name(source, default="TEC HTML"):
    return default if isinstance(source, str) else (source.get("name") or default)

def _clean_html(s):
    if not s:
        return None
    s = re.sub(r"(?is)<script[^>]*>.*?</script>|<style[^>]*>.*?</style>", "", s)
    s = re.sub(r"(?is)<br\s*/?>", "\n", s)
    s = re.sub(r"(?is)<[^>]+>", "", s)
    s = unescape(s).strip()
    s = re.sub(r"\s+\n", "\n", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s

# ---------------- ICS tiny reader (no external deps) ------------------------

def _unfold_ics(text):
    # RFC5545 line folding: subsequent lines beginning with space/tab are continuation
    lines = text.splitlines()
    out = []
    for ln in lines:
        if ln.startswith((" ", "\t")) and out:
            out[-1] += ln[1:]
        else:
            out.append(ln)
    return out

def _parse_ics_dt(val):
    # Handles YYYYMMDD or YYYYMMDDTHHMMSS(Z)
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

        # Key[:;params]=Value
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
        elif k in ("URL", "X-ALT-DESC;FMTTYPE=text/html", "X-ALT-DESC"):
            # prefer URL, but X-ALT-DESC can be noisy; we'll keep URL only
            if k == "URL":
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

# ---------------- HTML fallbacks (JSON-LD / TEC list) -----------------------

def _events_from_jsonld(html, source_name):
    out = []
    for m in re.finditer(r'(?is)<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', html):
        try:
            blob = unescape(m.group(1)).strip()
            data = None
            # very defensive JSON extraction
            import json
            data = json.loads(blob)
            items = data if isinstance(data, list) else [data]
        except Exception:
            continue
        for it in items:
            try:
                t = it.get("name") or it.get("headline")
                s = it.get("startDate")
                e = it.get("endDate")
                loc = it.get("location")
                url = it.get("url")
                if isinstance(loc, dict):
                    loc = loc.get("name") or loc.get("address")
                # normalize ISO-ish date strings
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
                        "title": t,
                        "start_utc": start_s,
                        "end_utc": end_s,
                        "url": url,
                        "location": loc,
                        "source": source_name,
                        "calendar": source_name,
                    })
            except Exception:
                continue
    return out

def _events_from_list_markup(html, base_url, source_name):
    """
    Handles common TEC list markup:
      - anchors with class containing 'tribe-event-url' or 'tribe-common-b1'
      - data-tribejson or data-tribe-event-json payloads with startDate
    """
    events = []
    # data-tribejson blob
    for m in re.finditer(r'(?is)data-tribe-event-json=["\'](.*?)["\']', html):
        try:
            import json
            data = json.loads(unescape(m.group(1)))
        except Exception:
            continue
        if isinstance(data, dict) and data.get("startDate") and data.get("title"):
            s = data["startDate"]; e = data.get("endDate")
            def norm(x):
                if not x: return None
                for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S"):
                    try:
                        return datetime.strptime(x, fmt).strftime("%Y-%m-%d %H:%M:%S")
                    except Exception:
                        pass
                return None
            start_s = norm(s); end_s = norm(e)
            uid = f"tec-{abs(hash((data.get('url') or '', data['title'], start_s or '')))}"
            events.append({
                "uid": uid,
                "title": _clean_html(data["title"]),
                "start_utc": start_s,
                "end_utc": end_s,
                "url": data.get("url"),
                "location": _clean_html((data.get("venue") or {}).get("venue") if isinstance(data.get("venue"), dict) else data.get("venue")),
                "source": source_name,
                "calendar": source_name,
            })

    # anchor-only fallback (no dates, but try to pick them up from surrounding time tags)
    if not events:
        # try to pair titles with nearby <time datetime="...">
        # find blocks that look like a list item
        for block in re.finditer(r'(?is)<article[^>]*?class="[^"]*tribe-events[^"]*".*?</article>', html):
            b = block.group(0)
            title = _clean_html(_first(r'(?is)<a[^>]+class="[^"]*tribe-[^"]*event[^"]*"[^>]*>(.*?)</a>', b))
            url = _first(r'(?is)<a[^>]+href=["\'](.*?)["\']', b)
            start_dt = _first(r'(?is)<time[^>]+datetime=["\'](.*?)["\']', b)
            if title and start_dt:
                try:
                    # normalize
                    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%d"):
                        try:
                            start_s = datetime.strptime(start_dt, fmt).strftime("%Y-%m-%d %H:%M:%S")
                            break
                        except Exception:
                            start_s = None
                except Exception:
                    start_s = None
                uid = f"tec-{abs(hash((url or '', title, start_s or '')))}"
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

def _first(pattern, text, flags=re.IGNORECASE|re.DOTALL):
    m = re.search(pattern, text, flags)
    return m.group(1).strip() if m else None

# ---------------- main ------------------------------------------------------

def fetch_tec_html(source, session, start_date=None, end_date=None):
    """
    St. Germain (TEC) HTML fetcher with built-in ICS fallback.
    Does NOT require src.ics_fetch.* and does not touch TEC REST.
    """
    base = _src_url(source)
    name = _src_name(source, "TEC HTML")
    if not base:
        return []

    # Prefer ICS if available
    candidates = []
    # canonical page usually ends with /events-calendar/
    if base.endswith("/"):
        candidates.append(base + "?ical=1")
    else:
        candidates.append(base + "/?ical=1")

    # fallbacks that often work on TEC sites
    # /events/ and /event/ are both seen in the wild
    parts = list(urlparse(base))
    parts[2] = parts[2].rstrip("/")
    for tail in ("/events/?ical=1", "/event/?ical=1", "/?ical=1"):
        candidates.append(urlunparse(parts[:2] + [parts[2] + tail] + parts[3:]))

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
        if events:
            return events  # success via ICS

    # HTML fallbacks: JSON-LD then TEC list markup
    try:
        r = session.get(base, timeout=30)
        r.raise_for_status()
        html = r.text
        events = _events_from_jsonld(html, name)
        if events:
            return events
        events = _events_from_list_markup(html, base, name)
        if events:
            return events
    except Exception:
        pass

    # nothing worked; return empty (caller will log)
    return []
