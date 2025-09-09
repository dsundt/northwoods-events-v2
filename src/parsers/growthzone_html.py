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
    m2 = re.search(
