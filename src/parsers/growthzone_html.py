# src/parsers/growthzone_html.py
# GrowthZone/ChamberMaster HTML parser with protected St. Germain fallback.
# - Rhinelander & other GZ: unchanged behavior; broader link discovery restores the
#   previous working path (SSR anchors -> /event(s)/details/...).
# - St. Germain only (host: stgermainwi.chambermaster.com): when zero GZ detail links,
#   collect outbound st-germain.com event anchors (incl. LinkClick.aspx), walk a few
#   SSR listing variants, and parse WP detail pages (dates + location).

from __future__ import annotations

import json
import re
from datetime import datetime, date
from html import unescape
from typing import Any, Dict, List, Optional, Set, Tuple
from urllib.parse import urljoin, urlparse, parse_qs, unquote


# ---------- runner call-shape compatibility ----------

def _coerce_signature(args, kwargs):
    """
    Supports runner call shapes:
      (source)
      (source, session)
      (source, start_date, end_date)
      (source, session, start_date, end_date)
    plus keyword args: session=, start_date=, end_date=, logger=
    """
    source = args[0] if args else kwargs.get("source")
    session = kwargs.get("session")
    start_date = kwargs.get("start_date")
    end_date = kwargs.get("end_date")
    logger = kwargs.get("logger")

    rest = list(args[1:])
    if rest and hasattr(rest[0], "get"):  # requests.Session-like
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


# ---------- small utils ----------

def _log(logger, msg: str) -> None:
    if logger and hasattr(logger, "debug"):
        try:
            logger.debug(msg)
        except Exception:
            pass


def _warn(logger, msg: str) -> None:
    if logger and hasattr(logger, "warning"):
        try:
            logger.warning(msg)
        except Exception:
            pass


def _clean_text(s: Optional[str]) -> Optional[str]:
    if not s:
        return None
    body = re.sub(r"(?is)<script[^>]*>.*?</script>|<style[^>]*>.*?</style>", "", s)
    body = re.sub(r"(?is)<br\s*/?>", "\n", body)
    body = re.sub(r"(?is)<[^>]+>", "", body)
    body = unescape(body).strip()
    body = re.sub(r"[ \t]+\n", "\n", body)
    body = re.sub(r"\n{3,}", "\n\n", body)
    return body or None


# ---------- link discovery ----------

# Broadened to restore Rhinelander:
_GZ_DETAIL_RE = re.compile(
    r'href=["\'](?:'
    r'(?P<abs>https?://[^"\']*/(?:event|events)/details/[^"\']+)'
    r'|'
    r'(?P<rel>/?(?:event|events)/details/[^"\']+)'
    r'|'
    r'(?P<qry>/?(?:event|events)/details/[^"\']*\?[^"\']*)'
    r')["\']',
    re.I,
)

def _extract_gz_detail_links(page_html: str, page_base: str) -> Set[str]:
    out: Set[str] = set()
    for m in _GZ_DETAIL_RE.finditer(page_html):
        absu = m.group("abs")
        relu = m.group("rel") or m.group("qry")
        if absu:
            out.add(absu)
        elif relu:
            # handle both "/events/details/..." and "events/details/..."
            if not relu.startswith("/"):
                relu = "/" + relu
            out.add(urljoin(page_base, relu))
    return out


_STG_OUTBOUND_DIRECT = re.compile(
    r'href=["\'](https?://st-germain\.com/(?:event|events)/[^"\']+)["\']',
    re.I,
)

_STG_LINKCLICK = re.compile(
    r'href=["\'](/?linkclick\.aspx\?[^"\']+)["\']',
    re.I,
)

def _extract_outbound_stgermain(page_html: str, page_base: str) -> Set[str]:
    """St. Germain-specific: outbound anchors to st-germain.com event pages (incl. LinkClick.aspx)."""
    out: Set[str] = set()
    for m in _STG_OUTBOUND_DIRECT.finditer(page_html):
        out.add(m.group(1))
    for m in _STG_LINKCLICK.finditer(page_html):
        u = urljoin(page_base, m.group(1))
        qs = parse_qs(urlparse(u).query)
        raw = (qs.get("link") or qs.get("Link") or [None])[0]
        if raw:
            tgt = unquote(raw)
            if re.search(r"^https?://st-germain\.com/(?:event|events)/", tgt, re.I):
                out.add(tgt)
    return out


def _events_root_same_host(u: str) -> str:
    p = urlparse(u)
    root = f"{p.scheme}://{p.netloc}"
    path = p.path or ""
    if "/events" in path:
        root += path.split("/events", 1)[0]
    return f"{root}/events"


def _month_starts(n: int = 6) -> List[str]:
    first = datetime.utcnow().date().replace(day=1)
    ys, ms = first.year, first.month
    out: List[str] = []
    for i in range(n):
        yy = ys + (ms - 1 + i) // 12
        mm = (ms - 1 + i) % 12 + 1
        out.append(f"{yy:04d}-{mm:02d}-01")
    return out


# ---------- detail parsing ----------

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

        def _maybe(node: Dict[str, Any]):
            t = node.get("@type")
            ok = False
            if isinstance(t, list):
                ok = any(str(x).lower() == "event" for x in t)
            else:
                ok = str(t).lower() == "event"
            if ok:
                evs.append(node)

        if isinstance(data, dict):
            if "@type" in data:
                _maybe(data)
            g = data.get("@graph")
            if isinstance(g, list):
                for n in g:
                    if isinstance(n, dict):
                        _maybe(n)
        elif isinstance(data, list):
            for n in data:
                if isinstance(n, dict):
                    _maybe(n)
    return evs


def _page_h1(html: str) -> Optional[str]:
    m = re.search(r"(?is)<h1[^>]*>(.*?)</h1>", html)
    return _clean_text(m.group(1)) if m else None


# --- St. Germain TEC detail extraction (no JSON-LD) ---

_MONTHS = {m: i for i, m in enumerate(
    ["January","February","March","April","May","June","July","August","September","October","November","December"], 1)}
_ABBR = {m[:3].lower(): i for m, i in _MONTHS.items()}

def _parse_month(mtxt: str) -> Optional[int]:
    mtxt = (mtxt or "").strip().rstrip(".")
    if not mtxt:
        return None
    if mtxt in _MONTHS:
        return _MONTHS[mtxt]
    a = mtxt[:3].lower()
    return _ABBR.get(a)

def _parse_time(tstr: str) -> Tuple[int, int]:
    m = re.match(r'(?i)^\s*(\d{1,2}):(\d{2})\s*(am|pm)\s*$', tstr.strip())
    if not m:
        return 9, 0  # default 09:00 local if not provided
    hh, mm, ampm = int(m.group(1)), int(m.group(2)), m.group(3).lower()
    if ampm == "pm" and hh != 12:
        hh += 12
    if ampm == "am" and hh == 12:
        hh = 0
    return hh, mm

def _parse_stgermain_location(html: str) -> Optional[str]:
    # Primary pattern you provided (granular and precise)
    m = re.search(
        r'(?is)x-text-content-text[^>]*>\s*<span[^>]*x-text-content-text-primary[^>]*>(.*?)</span',
        html,
    )
    if m:
        return _clean_text(m.group(1))
    # Fallback: human-friendly snippet
    m2 = re.search(r'(?i)\b(St\.?\s*Germain[^<\n]{0,120})', html)
    return _clean_text(m2.group(1)) if m2 else None

def _parse_stgermain_dates(blob: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Supports:
      - September 20, 2025
      - Sep 20, 2025
      - October 4 – 6, 2025
      - Oct 4 & 5, 2025
      - October 4, 2025 – October 6, 2025
      - With optional times: '10:00 am' or '8:00 am – 2:00 pm'
    Returns ISO strings (no timezone): (start_iso, end_iso|None)
    """
    txt = _clean_text(blob) or ""

    # Full range with two endpoints
    m = re.search(
        r'(?i)\b([A-Z][a-z]{2,9})\.?\s+(\d{1,2})(?:st|nd|rd|th)?\s*,\s*(\d{4})\s*[–-]\s*'
        r'([A-Z][a-z]{2,9})\.?\s+(\d{1,2})(?:st|nd|rd|th)?\s*,\s*(\d{4})',
        txt
    )
    if m:
        m1, d1, y1, m2, d2, y2 = m.groups()
        M1 = _parse_month(m1); M2 = _parse_month(m2)
        if M1 and M2:
            start = datetime(int(y1), M1, int(d1))
            end = datetime(int(y2), M2, int(d2))
            t = re.search(r'(?i)\b(\d{1,2}:\d{2}\s*(?:am|pm))\s*[–-]\s*(\d{1,2}:\d{2}\s*(?:am|pm))', txt)
            if t:
                h1, m1_ = _parse_time(t.group(1))
                h2, m2_ = _parse_time(t.group(2))
                start = start.replace(hour=h1, minute=m1_)
                end = end.replace(hour=h2, minute=m2_)
            return start.isoformat(), end.isoformat()

    # Month D – D, YYYY  (and Month D & D, YYYY)
    m = re.search(
        r'(?i)\b([A-Z][a-z]{2,9})\.?\s+(\d{1,2})(?:st|nd|rd|th)?\s*(?:[–-]|&)\s*(\d{1,2})(?:st|nd|rd|th)?\s*,\s*(\d{4})',
        txt
    )
    if m:
        mon, d1, d2, y = m.groups()
        M = _parse_month(mon)
        if M:
            start = datetime(int(y), M, int(d1))
            end = datetime(int(y), M, int(d2))
            t = re.search(r'(?i)\b(\d{1,2}:\d{2}\s*(?:am|pm))\s*(?:[–-]|&)\s*(\d{1,2}:\d{2}\s*(?:am|pm))', txt)
            if t:
                h1, m1_ = _parse_time(t.group(1))
                h2, m2_ = _parse_time(t.group(2))
                start = start.replace(hour=h1, minute=m1_)
                end = end.replace(hour=h2, minute=m2_)
            return start.isoformat(), end.isoformat()

    # Single date: Month D, YYYY (optional time or time range)
    m = re.search(
        r'(?i)\b([A-Z][a-z]{2,9})\.?\s+(\d{1,2})(?:st|nd|rd|th)?\s*,\s*(\d{4})',
        txt
    )
    if m:
        mon, d, y = m.groups()
        M = _parse_month(mon)
        if M:
            start = datetime(int(y), M, int(d))
            t2 = re.search(r'(?i)\b(\d{1,2}:\d{2}\s*(?:am|pm))(?:\s*(?:[–-]|&)\s*(\d{1,2}:\d{2}\s*(?:am|pm)))?', txt)
            if t2:
                h1, m1_ = _parse_time(t2.group(1))
                start = start.replace(hour=h1, minute=m1_)
                if t2.group(2):
                    h2, m2_ = _parse_time(t2.group(2))
                    end = datetime(int(y), M, int(d), h2, m2_)
                    return start.isoformat(), end.isoformat()
            return start.isoformat(), None

    return None, None


def _parse_stgermain_detail(html: str, url: str, source: str) -> Optional[Dict[str, Any]]:
    title = _page_h1(html) or "(untitled)"
    sect = re.search(r'(?is)(<h2[^>]*>\s*Event\s*Info\s*</h2>.*?)(?:<h2|\Z)', html)
    blob = sect.group(1) if sect else html
    start_iso, end_iso = _parse_stgermain_dates(blob)
    location = _parse_stgermain_location(blob)
    ev = {
        "title": title,
        "start": start_iso,
        "end": end_iso,
        "start_utc": start_iso,
        "end_utc": end_iso,
        "location": location,
        "url": url,
        "source": source,
        "_source": "growthzone_html",
    }
    if not start_iso:
        return None
    return ev


def _detail_to_event(detail_html: str, page_url: str, source_name: str) -> Optional[Dict[str, Any]]:
    # 1) JSON-LD first (works on most GZ detail pages)
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
            "title": title,
            "start": start,
            "end": end,
            "start_utc": start,
            "end_utc": end,
            "location": loc_out,
            "url": page_url,
            "description": ev.get("description"),
            "jsonld": ev,
            "source": source_name,
            "_source": "growthzone_html",
        }

    # 2) St. Germain TEC fallback
    if re.search(r"^https?://st-germain\.com/(?:event|events)/", page_url, re.I):
        return _parse_stgermain_detail(detail_html, page_url, source_name)

    # 3) Last resort
    return {"url": page_url, "source": source_name, "_source": "growthzone_html"}


def _filter_range(events: List[Dict[str, Any]], sdt, edt) -> List[Dict[str, Any]]:
    if not sdt or not edt:
        return events
    out: List[Dict[str, Any]] = []
    for ev in events:
        s = ev.get("start") or ev.get("start_utc")
        if not s:
            continue
        s2 = s.replace("Z", "+00:00") if isinstance(s, str) else s
        try:
            dt = datetime.fromisoformat(str(s2).split("+")[0])
        except Exception:
            try:
                dt = datetime.strptime(str(s2)[:10], "%Y-%m-%d")
            except Exception:
                continue
        if sdt <= dt <= edt:
            out.append(ev)
    return out


# ---------- MAIN ----------

def fetch_growthzone_html(*args, **kwargs) -> List[Dict[str, Any]]:
    source, session, start_date, end_date, logger = _coerce_signature(args, kwargs)
    base = _src_url(source)
    name = _src_name(source, "GrowthZone")
    if not base:
        return []

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

        # (A) Normal GZ SSR anchors (restores Rhinelander)
        gz_links = _extract_gz_detail_links(html, base)
        links |= gz_links
        _log(logger, f"[growthzone_html] initial gz-detail links: {len(gz_links)}")

        host = urlparse(base).netloc.lower()

        # (B) St. Germain-only outbound anchors if no GZ links
        if not links and "stgermainwi.chambermaster.com" in host:
            out_links = _extract_outbound_stgermain(html, base)
            _log(logger, f"[growthzone_html] initial outbound TEC links: {len(out_links)}")
            links |= out_links

        # (C) Probe SSR variants if still empty
        if not links:
            root = _events_root_same_host(base)
            candidates = [
                base + ("&o=alpha" if "?" in base else "?o=alpha"),
                f"{root}/calendar",
                f"{root}/search",
            ]
            # walk next 6 months (server-rendered month pages)
            for iso in _month_starts(6):
                candidates.append(f"{root}/calendar/{iso}")

            for alt in candidates:
                try:
                    _log(logger, f"[growthzone_html] fallback GET {alt}")
                    r2 = session.get(alt, timeout=30)
                    if not r2.ok:
                        continue
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
                    continue

        if not links:
            _log(logger, "[growthzone_html] no links discovered after fallbacks")
            return []

        # (D) Visit details and parse
        events: List[Dict[str, Any]] = []
        for href in sorted(links):
            try:
                _log(logger, f"[growthzone_html] detail GET {href}")
                r = session.get(href, timeout=30)
                if not r.ok:
                    continue
                ev = _detail_to_event(r.text, href, name)
                if not ev:
                    continue
                # Ensure both start/start_utc exist for downstream compatibility
                if ev.get("start") and "start_utc" not in ev:
                    ev["start_utc"] = ev["start"]
                if ev.get("end") and "end_utc" not in ev:
                    ev["end_utc"] = ev["end"]
                if ev.get("start") or ev.get("start_utc"):
                    events.append(ev)
            except Exception as e:
                _warn(logger, f"[growthzone_html] error parsing {href}: {e}")
                continue

        # (E) Date filter
        events = _filter_range(events, start_date, end_date)
        _log(logger, f"[growthzone_html] parsed events: {len(events)}")
        return events

    finally:
        if own_session:
            try:
                session.close()
            except Exception:
                pass
