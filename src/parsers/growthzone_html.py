# src/parsers/growthzone_html.py
# GrowthZone/ChamberMaster HTML parser with guarded fallbacks.
# - Rhinelander: unchanged behavior (extracts /events/details/... right away).
# - St. Germain: if no /events/details/... are found, collect outbound
#   st-germain.com/events/... links (direct or LinkClick.aspx) and parse those
#   event pages (JSON-LD if present, otherwise robust "Event Info" fallback).

from __future__ import annotations

import json
import re
from datetime import datetime, date
from html import unescape
from typing import Any, Dict, List, Optional, Set
from urllib.parse import urljoin, urlparse, parse_qs, unquote


# -------------------- signature normalization --------------------

def _coerce_signature(args, kwargs):
    """
    Supported call shapes from your runner:
      - (source)
      - (source, session)
      - (source, start_date, end_date)
      - (source, session, start_date, end_date)
    and keyword args: session=, start_date=, end_date=, logger=.
    """
    source = args[0] if args else kwargs.get("source")
    session = kwargs.get("session")
    start_date = kwargs.get("start_date")
    end_date = kwargs.get("end_date")

    # positional unpacking after source:
    rest = list(args[1:])
    # detect requests.Session-like by duck-typing (has .get)
    if rest and hasattr(rest[0], "get"):
        session = rest.pop(0)
    if rest:
        start_date = rest.pop(0)
    if rest:
        end_date = rest.pop(0)
    return source, session, start_date, end_date, kwargs.get("logger")


def _src_url(source):
    return source if isinstance(source, str) else (source.get("url") if source else None)


def _src_name(source, default="GrowthZone"):
    return default if isinstance(source, str) else (source.get("name") or default)


# -------------------- small utils --------------------

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
    # strip tags and scripts/styles, collapse whitespace
    body = re.sub(r"(?is)<script[^>]*>.*?</script>|<style[^>]*>.*?</style>", "", s)
    body = re.sub(r"(?is)<br\s*/?>", "\n", body)
    body = re.sub(r"(?is)<[^>]+>", "", body)
    body = unescape(body).strip()
    body = re.sub(r"[ \t]+\n", "\n", body)
    body = re.sub(r"\n{3,}", "\n\n", body)
    return body or None


# -------------------- link discovery --------------------

def _extract_gz_detail_links(page_html: str, page_base: str) -> Set[str]:
    """Find GrowthZone-native event detail anchors."""
    out: Set[str] = set()
    # absolute /events/details/...
    for m in re.finditer(
        r'href=["\'](https?://[^"\']*/events/details/[^"\']+)["\']', page_html, flags=re.I
    ):
        out.add(m.group(1))
    # relative /events/details/...
    for m in re.finditer(
        r'href=["\'](/events/details/[^"\']+)["\']', page_html, flags=re.I
    ):
        out.add(urljoin(page_base, m.group(1)))
    return out


def _extract_outbound_stgermain(page_html: str, page_base: str) -> Set[str]:
    """
    St. Germain-specific: find outbound st-germain.com/events/... anchors.
    Handles both direct anchors and GrowthZone LinkClick.aspx redirects.
    """
    out: Set[str] = set()
    # direct anchors
    for m in re.finditer(
        r'href=["\'](https?://st-germain\.com/events/[^"\']+)["\']', page_html, flags=re.I
    ):
        out.add(m.group(1))
    # LinkClick.aspx?link=<URL-ENCODED>
    for m in re.finditer(
        r'href=["\'](/?linkclick\.aspx\?[^"\']+)["\']', page_html, flags=re.I
    ):
        u = urljoin(page_base, m.group(1))
        qs = parse_qs(urlparse(u).query)
        raw = (qs.get("link") or qs.get("Link") or [None])[0]
        if raw:
            tgt = unquote(raw)
            if re.search(r"^https?://st-germain\.com/events/", tgt, flags=re.I):
                out.add(tgt)
    return out


def _events_root_same_host(u: str) -> str:
    p = urlparse(u)
    root = f"{p.scheme}://{p.netloc}"
    path = p.path or ""
    if "/events" in path:
        root += path.split("/events", 1)[0]
    return f"{root}/events"


def _month_starts(n: int = 4) -> List[str]:
    first = datetime.utcnow().date().replace(day=1)
    ys, ms = first.year, first.month
    out: List[str] = []
    for i in range(n):
        yy = ys + (ms - 1 + i) // 12
        mm = (ms - 1 + i) % 12 + 1
        out.append(f"{yy:04d}-{mm:02d}-01")
    return out


# -------------------- detail parsing --------------------

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


def _parse_stgermain_eventinfo(html: str, url: str, source: str) -> Optional[Dict[str, Any]]:
    """
    St. Germain TEC page fallback when no JSON-LD Event exists.
    Extracts:
      - Title from <h1>
      - Date (e.g., 'September 20th, 2025', 'Oct 4, 2025')
      - Optional time (e.g., '10:00 am')
      - A simple location line that mentions 'St Germain...'
    """
    title = _page_h1(html) or "(untitled)"

    # Try to confine to an "Event Info" block if present, else use full HTML.
    sect = re.search(r'(?is)(<h2[^>]*>\s*Event\s*Info\s*</h2>.*?)(?:<h2|\Z)', html)
    blob = sect.group(1) if sect else html

    # Date: 'September 20th, 2025' or 'Sep 20, 2025' / 'Oct. 4, 2025'
    m_date = re.search(
        r'(?i)\b([A-Z][a-z]{2,9})\.?\s+(\d{1,2})(?:st|nd|rd|th)?\s*,\s*(\d{4})',
        blob,
    )
    if not m_date:
        # Sometimes 'Saturday, September 20th, 2025'
        m_date = re.search(
            r'(?i)\b(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)[a-z]*,\s+([A-Z][a-z]{2,9})\.?\s+(\d{1,2})(?:st|nd|rd|th)?\s*,\s*(\d{4})',
            blob,
        )
    if not m_date:
        return None

    month, day, year = m_date.groups()
    # Try long month first, then short
    dt = None
    try:
        dt = datetime.strptime(f"{month} {int(day)} {year}", "%B %d %Y")
    except Exception:
        try:
            dt = datetime.strptime(f"{month} {int(day)} {year}", "%b %d %Y")
        except Exception:
            return None

    # Optional time (e.g., '10:00 am')
    m_time = re.search(r'(?i)\b(\d{1,2}:\d{2})\s*(am|pm)\b', blob)
    if m_time:
        hhmm, ampm = m_time.groups()
        hh, mm = map(int, hhmm.split(":"))
        if ampm.lower() == "pm" and hh != 12:
            hh += 12
        if ampm.lower() == "am" and hh == 12:
            hh = 0
        dt = dt.replace(hour=hh, minute=mm)

    # Location line: grab something human-readable mentioning St Germain
    m_loc = re.search(r"(?i)\b(St\.?\s*Germain[^<\n]{0,120})", blob)
    location = _clean_text(m_loc.group(1)) if m_loc else None

    return {
        "title": title,
        "start": dt.isoformat(),
        "url": url,
        "location": location,
        "source": source,
        "_source": "growthzone_html",
    }


def _detail_to_event(detail_html: str, page_url: str, source_name: str) -> Optional[Dict[str, Any]]:
    # 1) Prefer JSON-LD Event if present
    blocks = _jsonld_events(detail_html)
    for ev in blocks:
        title = ev.get("name") or ev.get("headline") or _page_h1(detail_html) or "(untitled)"
        start = ev.get("startDate")
        end = ev.get("endDate")
        loc = ev.get("location")
        if isinstance(loc, dict):
            loc_out = loc.get("name") or _clean_text(json.dumps(loc))
        else:
            loc_out = _clean_text(str(loc)) if loc else None
        return {
            "title": title,
            "start": start,
            "end": end,
            "location": loc_out,
            "url": page_url,
            "description": ev.get("description"),
            "jsonld": ev,
            "source": source_name,
            "_source": "growthzone_html",
        }

    # 2) St. Germain TEC fallback: parse "Event Info" text
    if re.search(r"^https?://st-germain\.com/events/", page_url, flags=re.I):
        return _parse_stgermain_eventinfo(detail_html, page_url, source_name)

    # 3) No structured info available; emit minimal placeholder
    return {"url": page_url, "source": source_name, "_source": "growthzone_html"}


def _filter_range(events: List[Dict[str, Any]], sdt, edt) -> List[Dict[str, Any]]:
    if not sdt or not edt:
        return events
    out: List[Dict[str, Any]] = []
    for ev in events:
        s = ev.get("start") or ev.get("start_utc")
        if not s:
            continue
        # Lenient ISO parsing: drop TZ if present for comparison
        try:
            s2 = s.replace("Z", "+00:00")
        except Exception:
            s2 = s
        try:
            dt = datetime.fromisoformat(s2.split("+")[0])
        except Exception:
            # Try date-only
            try:
                dt = datetime.strptime(s2[:10], "%Y-%m-%d")
            except Exception:
                continue
        if sdt <= dt <= edt:
            out.append(ev)
    return out


# -------------------- MAIN ENTRY --------------------

def fetch_growthzone_html(*args, **kwargs) -> List[Dict[str, Any]]:
    """
    GrowthZone (ChamberMaster) HTML fetcher with guarded St. Germain fallback.
    - First, extract internal /events/details/... links.
    - If none AND host is stgermainwi.chambermaster.com, also collect outbound
      st-germain.com/events/... links (including LinkClick.aspx redirects).
    - Probe a few SSR variants when zero links remain.
    - Parse detail pages via JSON-LD or St. Germain 'Event Info' fallback.
    """
    source, session, start_date, end_date, logger = _coerce_signature(args, kwargs)
    base = _src_url(source)
    name = _src_name(source, "GrowthZone")
    if not base:
        return []

    # Create session if not provided
    own_session = False
    if session is None:
        import requests
        session = requests.Session()
        own_session = True

    try:
        _log(logger, f"[growthzone_html] GET {base}")
        resp = session.get(base, timeout=30)
        resp.raise_for_status()
        html = resp.text

        links: Set[str] = set()

        # A) Try to get GrowthZone internal detail anchors right away.
        gz_links = _extract_gz_detail_links(html, base)
        links |= gz_links
        _log(logger, f"[growthzone_html] initial gz-detail links: {len(gz_links)}")

        host = urlparse(base).netloc.lower()

        # B) St. Germain-only: collect outbound TEC anchors if no GZ links found yet.
        if not links and "stgermainwi.chambermaster.com" in host:
            out_links = _extract_outbound_stgermain(html, base)
            _log(logger, f"[growthzone_html] initial outbound TEC links: {len(out_links)}")
            links |= out_links

        # C) If still none, probe a few server-rendered variants on same host.
        if not links:
            root = _events_root_same_host(base)
            candidates = [
                base + ("&o=alpha" if "?" in base else "?o=alpha"),
                f"{root}/calendar",
                f"{root}/search",
            ]
            for iso in _month_starts(4):
                candidates.append(f"{root}/calendar/{iso}")

            for alt in candidates:
                try:
                    _log(logger, f"[growthzone_html] fallback GET {alt}")
                    r2 = session.get(alt, timeout=30)
                    if not r2.ok:
                        continue
                    # try GZ native links first
                    cand = _extract_gz_detail_links(r2.text, alt)
                    if cand:
                        links |= cand
                        _log(logger, f"[growthzone_html] fallback gz links from {alt}: {len(cand)}")
                        break
                    # St. Germain-only outbound anchors
                    if "stgermainwi.chambermaster.com" in host:
                        extra = _extract_outbound_stgermain(r2.text, alt)
                        if extra:
                            links |= extra
                            _log(logger, f"[growthzone_html] fallback outbound TEC links from {alt}: {len(extra)}")
                            break
                except Exception as e:
                    _warn(logger, f"[growthzone_html] fallback error on {alt}: {e}")
                    continue

        if not links:
            _log(logger, "[growthzone_html] no links discovered after fallbacks")
            return []

        # D) Visit each detail page and parse
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
                # unify keys if upstream used start_utc/end_utc
                if "start_utc" in ev and "start" not in ev:
                    ev["start"] = ev.pop("start_utc")
                if "end_utc" in ev and "end" not in ev:
                    ev["end"] = ev.pop("end_utc")
                # keep only events with a detectable start
                if ev.get("start"):
                    events.append(ev)
            except Exception as e:
                _warn(logger, f"[growthzone_html] error parsing {href}: {e}")
                continue

        # E) Optional date filtering
        events = _filter_range(events, start_date, end_date)
        _log(logger, f"[growthzone_html] parsed events: {len(events)}")
        return events

    finally:
        if own_session:
            try:
                session.close()
            except Exception:
                pass
