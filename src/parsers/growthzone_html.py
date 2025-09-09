# src/parsers/growthzone_html.py
from __future__ import annotations
import json, re
from datetime import datetime
from html import unescape
from typing import Any, Dict, List, Optional, Set, Tuple
from urllib.parse import urljoin, urlparse, parse_qs, unquote

def _clean_text(s: Optional[str]) -> Optional[str]:
    if not s: return None
    body = re.sub(r"(?is)<script[^>]*>.*?</script>|<style[^>]*>.*?</style>", "", s)
    body = re.sub(r"(?is)<br\s*/?>", "\n", body)
    body = re.sub(r"(?is)</p\s*>", "\n", body)
    body = re.sub(r"(?is)<[^>]+>", "", body)
    body = unescape(body).strip()
    body = re.sub(r"[ \t]+\n", "\n", body)
    body = re.sub(r"\n{3,}", "\n\n", body)
    return body or None

def _coerce_signature(args, kwargs):
    source = args[0] if args else kwargs.get("source")
    session = kwargs.get("session")
    start_date = kwargs.get("start_date")
    end_date = kwargs.get("end_date")
    logger = kwargs.get("logger")
    rest = list(args[1:])
    if rest and hasattr(rest[0], "get"):
        session = rest.pop(0)
    if rest:
        start_date = rest.pop(0)
    if rest:
        end_date = rest.pop(0)
    return source, session, start_date, end_date, logger

def _src_url(source):
    return source if isinstance(source, str) else (source.get("url") if source else None)

def _src_name(source, default="GrowthZone"):
    return default if isinstance(source, str) else (source.get("name") or default)

def _log(logger, msg): 
    try:
        if logger and hasattr(logger, "debug"): logger.debug(msg)
    except Exception: pass

def _warn(logger, msg):
    try:
        if logger and hasattr(logger, "warning"): logger.warning(msg)
    except Exception: pass

# -------- link discovery (broadened) --------
_GZ_DETAIL_RE = re.compile(
    r'href=["\']([^"\']*(?:^|/)(?:event|events)/details[^"\']*)["\']',
    re.I,
)

def _extract_gz_detail_links(page_html: str, page_base: str) -> Set[str]:
    out: Set[str] = set()
    for m in _GZ_DETAIL_RE.finditer(page_html):
        href = m.group(1)
        if href.lower().startswith(("mailto:", "tel:")): continue
        if not re.match(r'^https?://', href, re.I):
            if not href.startswith("/"): href = "/" + href
            href = urljoin(page_base, href)
        out.add(href)
    return out

# ---- St. Germain helpers (outbound to WP) ----
_STG_OUTBOUND_DIRECT = re.compile(
    r'href=["\'](https?://(?:www\.)?st-germain\.com/(?:event|events)/[^"\']+)["\']',
    re.I,
)
_STG_LINKCLICK = re.compile(r'href=["\'](/?linkclick\.aspx\?[^"\']+)["\']', re.I)

def _multi_unquote(u: str, times: int = 3) -> str:
    v = u
    for _ in range(times):
        v2 = unquote(v)
        if v2 == v: break
        v = v2
    return v

def _extract_outbound_stgermain(page_html: str, page_base: str) -> Set[str]:
    out: Set[str] = set()
    for m in _STG_OUTBOUND_DIRECT.finditer(page_html):
        out.add(m.group(1))
    for m in _STG_LINKCLICK.finditer(page_html):
        u = urljoin(page_base, m.group(1))
        qs = parse_qs(urlparse(u).query)
        raw = (qs.get("link") or qs.get("Link") or [None])[0]
        if raw:
            tgt = _multi_unquote(raw)
            if re.search(r"^https?://(?:www\.)?st-germain\.com/(?:event|events)/", tgt, re.I):
                out.add(tgt)
    return out

def _events_root_same_host(u: str) -> str:
    p = urlparse(u)
    root = f"{p.scheme}://{p.netloc}"
    base = p.path or ""
    if "/events" in base:
        root += base.split("/events", 1)[0]
    return f"{root}/events"

def _month_starts(n: int = 6) -> List[str]:
    from datetime import date
    first = date.today().replace(day=1)
    ys, ms = first.year, first.month
    out: List[str] = []
    for i in range(n):
        yy = ys + (ms - 1 + i) // 12
        mm = (ms - 1 + i) % 12 + 1
        out.append(f"{yy:04d}-{mm:02d}-01")
    return out

# ---- JSON-LD ----
def _jsonld_events(html: str) -> List[Dict[str, Any]]:
    evs: List[Dict[str, Any]] = []
    for sm in re.finditer(
        r'(?is)<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', html
    ):
        block = sm.group(1).strip()
        try:
            data = json.loads(block)
        except Exception:
            continue
        def _maybe(node):
            t = node.get("@type")
            ok = False
            if isinstance(t, list):
                ok = any(str(x).lower() == "event" for x in t)
            else:
                ok = str(t).lower() == "event"
            if ok: evs.append(node)
        if isinstance(data, dict):
            if "@type" in data: _maybe(data)
            g = data.get("@graph")
            if isinstance(g, list):
                for n in g:
                    if isinstance(n, dict): _maybe(n)
        elif isinstance(data, list):
            for n in data:
                if isinstance(n, dict): _maybe(n)
    return evs

def _page_h1(html: str) -> Optional[str]:
    m = re.search(r"(?is)<h1[^>]*>(.*?)</h1>", html)
    return _clean_text(m.group(1)) if m else None

# ---- St. Germain WP detail parsing ----
_MONTHS = {m: i for i, m in enumerate(
    ["January","February","March","April","May","June","July","August","September","October","November","December"], 1)}
_ABBR = {m[:3].lower(): i for m, i in _MONTHS.items()}

def _parse_month(mtxt: str) -> Optional[int]:
    mtxt = (mtxt or "").strip().rstrip(".")
    if not mtxt: return None
    if mtxt in _MONTHS: return _MONTHS[mtxt]
    a = mtxt[:3].lower()
    return _ABBR.get(a)

def _parse_time_token(tstr: str) -> Tuple[int, int]:
    m = re.match(r'(?i)^\s*(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\s*$', tstr.strip())
    if not m:
        return 9, 0
    hh = int(m.group(1)); mm = int(m.group(2) or 0); ap = (m.group(3) or "").lower()
    if ap == "pm" and hh != 12: hh += 12
    if ap == "am" and hh == 12: hh = 0
    return hh, mm

def _parse_stgermain_location(html: str) -> Optional[str]:
    m = re.search(
        r'(?is)<span[^>]*class="[^"]*x-text-content-text-primary[^"]*"[^>]*>(.*?)</span>',
        html,
    )
    if m:
        return _clean_text(m.group(1))
    m2 = re.search(r'(?i)\b(St\.?\s*Germain[^<\n]{0,120})', html)
    return _clean_text(m2.group(1)) if m2 else None

def _parse_stgermain_dates(blob: str) -> Tuple[Optional[str], Optional[str]]:
    txt = _clean_text(blob) or ""
    # Range with two months
    m = re.search(
        r'(?i)\b([A-Z][a-z]{2,9})\.?\s+(\d{1,2})(?:st|nd|rd|th)?\s*,\s*(\d{4})\s*(?:–|-|to)\s*'
        r'([A-Z][a-z]{2,9})\.?\s+(\d{1,2})(?:st|nd|rd|th)?\s*,\s*(\d{4})', txt)
    if m:
        m1,d1,y1,m2,d2,y2 = m.groups()
        M1=_parse_month(m1); M2=_parse_month(m2)
        if M1 and M2:
            start = datetime(int(y1), M1, int(d1)); end = datetime(int(y2), M2, int(d2))
            t = re.search(r'(?i)\b(?:\d{1,2}:\d{2}\s*(?:am|pm)?|\d{1,2}\s*(?:am|pm))\s*(?:–|-|to|&)\s*(?:\d{1,2}:\d{2}\s*(?:am|pm)?|\d{1,2}\s*(?:am|pm))', txt)
            if t:
                parts = re.split(r'(?i)(?:–|-|to|&)', t.group(0))
                h1,m1_=_parse_time_token(parts[0]); h2,m2_=_parse_time_token(parts[-1])
                start=start.replace(hour=h1,minute=m1_); end=end.replace(hour=h2,minute=m2_)
            return start.isoformat(), end.isoformat()
    # Month D – D, YYYY  (or &)
    m = re.search(
        r'(?i)\b([A-Z][a-z]{2,9})\.?\s+(\d{1,2})(?:st|nd|rd|th)?\s*(?:–|-|&|to)\s*(\d{1,2})(?:st|nd|rd|th)?\s*,\s*(\d{4})', txt)
    if m:
        mon,d1,d2,y = m.groups()
        M=_parse_month(mon)
        if M:
            start=datetime(int(y),M,int(d1)); end=datetime(int(y),M,int(d2))
            t = re.search(r'(?i)\b(?:\d{1,2}:\d{2}\s*(?:am|pm)?|\d{1,2}\s*(?:am|pm))\s*(?:–|-|to|&)\s*(?:\d{1,2}:\d{2}\s*(?:am|pm)?|\d{1,2}\s*(?:am|pm))', txt)
            if t:
                parts = re.split(r'(?i)(?:–|-|to|&)', t.group(0))
                h1,m1_=_parse_time_token(parts[0]); h2,m2_=_parse_time_token(parts[-1])
                start=start.replace(hour=h1,minute=m1_); end=end.replace(hour=h2,minute=m2_)
            return start.isoformat(), end.isoformat()
    # Single date with optional time/range
    m = re.search(r'(?i)\b([A-Z][a-z]{2,9})\.?\s+(\d{1,2})(?:st|nd|rd|th)?\s*,\s*(\d{4})', txt)
    if m:
        mon,d,y = m.groups(); M=_parse_month(mon)
        if M:
            start = datetime(int(y),M,int(d))
            t2 = re.search(r'(?i)\b(?:\d{1,2}:\d{2}\s*(?:am|pm)?|\d{1,2}\s*(?:am|pm))(?:\s*(?:–|-|to|&)\s*(?:\d{1,2}:\d{2}\s*(?:am|pm)?|\d{1,2}\s*(?:am|pm)))?', txt)
            if t2:
                parts = re.split(r'(?i)(?:–|-|to|&)', t2.group(0))
                h1,m1_=_parse_time_token(parts[0]); start=start.replace(hour=h1,minute=m1_)
                if len(parts)==2:
                    h2,m2_=_parse_time_token(parts[1]); end=datetime(int(y),M,int(d),h2,m2_)
                    return start.isoformat(), end.isoformat()
            return start.isoformat(), None
    return None, None

def _parse_stgermain_detail(html: str, url: str, source: str) -> Optional[Dict[str, Any]]:
    title = _page_h1(html) or "(untitled)"
    sect = re.search(r'(?is)(<h2[^>]*>\s*Event\s*Info\s*</h2>.*?)(?:<h2|\Z)', html)
    blob = sect.group(1) if sect else html
    start_iso, end_iso = _parse_stgermain_dates(blob)
    location = _parse_stgermain_location(html)
    if not start_iso:
        return None
    return {
        "title": title,
        "start": start_iso, "end": end_iso,
        "start_utc": start_iso, "end_utc": end_iso,
        "location": location,
        "url": url,
        "source": source, "_source": "growthzone_html",
    }

# ---- GrowthZone labeled fallback (fixes Rhinelander when no JSON-LD/microdata) ----
def _extract_label_lines(text: str, label: str) -> Optional[str]:
    pat = re.compile(rf'(?im)^{re.escape(label)}\s*:\s*(.*)$')
    m = pat.search(text)
    if m:
        return m.group(1).strip()
    if label.lower() == "location":
        m2 = re.search(r'(?is)^\s*Location\s*:\s*(.*?)\n(?=(?:Date/Time Information|Contact Information|Fees/Admission|Set a Reminder|Event Description)\s*:|$)', text)
        if m2:
            return m2.group(1).strip()
    return None

def _parse_gz_labeled(detail_html: str) -> Optional[Dict[str, Any]]:
    txt = _clean_text(detail_html) or ""
    date_str = _extract_label_lines(txt, "Date")
    time_str = _extract_label_lines(txt, "Time")
    loc = _extract_label_lines(txt, "Location")
    if not date_str:
        return None
    dm = re.search(r'(?i)\b([A-Z][a-z]{2,9})\s+(\d{1,2})(?:st|nd|rd|th)?\s*,\s*(\d{4})', date_str)
    if not dm:
        return None
    mon, d, y = dm.groups()
    M = _parse_month(mon)
    if not M:
        return None
    start = datetime(int(y), M, int(d))
    end = None
    if time_str:
        tm = re.search(r'(?i)(\d{1,2}(?::\d{2})?\s*(?:am|pm))\s*(?:–|-|to)\s*(\d{1,2}(?::\d{2})?\s*(?:am|pm))', time_str)
        if tm:
            def to_hm(t):
                m = re.match(r'(?i)^\s*(\d{1,2})(?::(\d{2}))?\s*(am|pm)\s*$', t)
                hh = int(m.group(1)); mm = int(m.group(2) or 0); ap = m.group(3).lower()
                if ap == "pm" and hh != 12: hh += 12
                if ap == "am" and hh == 12: hh = 0
                return hh, mm
            h1,m1 = to_hm(tm.group(1)); h2,m2 = to_hm(tm.group(2))
            start = start.replace(hour=h1, minute=m1)
            end = datetime(int(y), M, int(d), h2, m2)
        else:
            tm2 = re.search(r'(?i)(\d{1,2})(?::(\d{2}))?\s*(am|pm)', time_str)
            if tm2:
                hh=int(tm2.group(1)); mm=int(tm2.group(2) or 0); ap=tm2.group(3).lower()
                if ap=="pm" and hh!=12: hh+=12
                if ap=="am" and hh==12: hh=0
                start = start.replace(hour=hh, minute=mm)
    return {
        "title": None,
        "start": start.isoformat(),
        "end": end.isoformat() if end else None,
        "start_utc": start.isoformat(),
        "end_utc": end.isoformat() if end else None,
        "location": loc,
    }

def _detail_to_event(detail_html: str, page_url: str, source_name: str) -> Optional[Dict[str, Any]]:
    blocks = _jsonld_events(detail_html)
    if blocks:
        ev = blocks[0]
        title = ev.get("name") or ev.get("headline") or _page_h1(detail_html) or "(untitled)"
        start = ev.get("startDate"); end = ev.get("endDate")
        loc = ev.get("location")
        if isinstance(loc, dict):
            loc_out = loc.get("name") or _clean_text(json.dumps(loc))
        else:
            loc_out = _clean_text(str(loc)) if loc else None
        return {
            "title": title, "start": start, "end": end,
            "start_utc": start, "end_utc": end,
            "location": loc_out, "url": page_url,
            "description": ev.get("description"),
            "jsonld": ev, "source": source_name, "_source": "growthzone_html",
        }
    # St. Germain WP pages
    if re.search(r"^https?://(?:www\.)?st-germain\.com/(?:event|events)/", page_url, re.I):
        return _parse_stgermain_detail(detail_html, page_url, source_name)

    # GrowthZone labeled fallback (Date:/Time:/Location:)
    lab = _parse_gz_labeled(detail_html)
    if lab and (lab.get("start") or lab.get("start_utc")):
        title = _page_h1(detail_html) or "(untitled)"
        lab.update({
            "title": title,
            "url": page_url,
            "source": source_name,
            "_source": "growthzone_html",
        })
        return lab

    # Minimal
    return {"url": page_url, "source": source_name, "_source": "growthzone_html"}

def _filter_range(events: List[Dict[str, Any]], sdt, edt) -> List[Dict[str, Any]]:
    if not sdt or not edt:
        return events
    out: List[Dict[str, Any]] = []
    for ev in events:
        s = ev.get("start") or ev.get("start_utc")
        if not s: continue
        try:
            dt = datetime.fromisoformat(str(s).split("+")[0])
        except Exception:
            try:
                dt = datetime.strptime(str(s)[:10], "%Y-%m-%d")
            except Exception:
                continue
        if sdt <= dt <= edt:
            out.append(ev)
    return out

def fetch_growthzone_html(*args, **kwargs) -> List[Dict[str, Any]]:
    source, session, start_date, end_date, logger = _coerce_signature(args, kwargs)
    base = _src_url(source); name = _src_name(source, "GrowthZone")
    if not base: return []

    own_session = False
    if session is None:
        import requests
        session = requests.Session()
        own_session = True

    try:
        _log(logger, f"[growthzone_html] GET {base}")
        resp = session.get(base, timeout=30); resp.raise_for_status()
        html = resp.text

        links: Set[str] = set()
        gz_links = _extract_gz_detail_links(html, base)
        if gz_links: links |= gz_links
        _log(logger, f"[growthzone_html] initial gz-detail links: {len(gz_links)}")

        host = urlparse(base).netloc.lower()

        if not links and "stgermainwi.chambermaster.com" in host:
            out_links = _extract_outbound_stgermain(html, base)
            if out_links: links |= out_links
            _log(logger, f"[growthzone_html] initial outbound TEC links: {len(out_links)}")

        if not links:
            root = _events_root_same_host(base)
            candidates = [
                base + ("&o=alpha" if "?" in base else "?o=alpha"),
                f"{root}/calendar",
                f"{root}/search",
                f"{root}/searchscroll",
            ]
            for iso in _month_starts(6):
                candidates.append(f"{root}/calendar/{iso}")
            for alt in candidates:
                try:
                    _log(logger, f"[growthzone_html] fallback GET {alt}")
                    r2 = session.get(alt, timeout=30)
                    if not r2.ok: continue
                    cand = _extract_gz_detail_links(r2.text, alt)
                    if cand:
                        links |= cand
                        _log(logger, f"[growthzone_html] fallback gz links: {len(cand)} from {alt}")
                        break
                    if "stgermainwi.chambermaster.com" in host:
                        extra = _extract_outbound_stgermain(r2.text, alt)
                        if extra:
                            links |= extra
                            _log(logger, f"[growthzone_html] fallback outbound TEC links: {len(extra)} from {alt}")
                            break
                except Exception as e:
                    _warn(logger, f"[growthzone_html] fallback error on {alt}: {e}")

        if not links:
            _log(logger, "[growthzone_html] no links discovered after fallbacks")
            return []

        events: List[Dict[str, Any]] = []
        for href in sorted(links):
            try:
                _log(logger, f"[growthzone_html] detail GET {href}")
                r = session.get(href, timeout=30)
                if not r.ok: continue
                ev = _detail_to_event(r.text, href, name)
                if not ev: continue
                if ev.get("start") and "start_utc" not in ev:
                    ev["start_utc"] = ev["start"]
                if ev.get("end") and "end_utc" not in ev:
                    ev["end_utc"] = ev["end"]
                if ev.get("start") or ev.get("start_utc"):
                    events.append(ev)
            except Exception as e:
                _warn(logger, f"[growthzone_html] error parsing {href}: {e}")

        events = _filter_range(events, start_date, end_date)
        _log(logger, f"[growthzone_html] parsed events: {len(events)}")
        return events

    finally:
        if own_session:
            try: session.close()
            except Exception: pass
