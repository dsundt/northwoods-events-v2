# src/parsers/growthzone_html.py
# Drop-in parser for GrowthZone/ChamberMaster event listings.
# This version preserves existing behavior and adds a guarded fallback
# that probes SSR list views (alpha/search/monthly calendar) ONLY if the
# initial listing page yields zero /events/details/ links.
#
# Tested paths:
# - Rhinelander (server-rendered calendar) -> unchanged behavior
# - St. Germain (JS-heavy listings) -> fallback activates to find links

from __future__ import annotations

import re
import json
from datetime import datetime, date
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple
from urllib.parse import urljoin, urlparse

# NOTE: We intentionally keep the signature flexible to match various callers.
# The function accepts extra keyword args and ignores what it doesn't use.
# This ensures backward compatibility with your runner.
def fetch_growthzone_html(
    session,
    base: str,
    *,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    timezone: Optional[str] = None,
    logger: Optional[Any] = None,
    timeout: int = 30,
    max_events: int = 500,
    **kwargs: Any,
) -> List[Dict[str, Any]]:
    """
    Fetch and normalize GrowthZone events by extracting /events/details/... links
    from a server-rendered listing page and parsing JSON-LD from detail pages.

    Behavior:
      1) Fetch `base` and extract detail links.
      2) If ZERO links found, try safe SSR variants on the same host:
         - add '?o=alpha'
         - '/events/calendar'
         - next few monthly calendar paths '/events/calendar/YYYY-MM-01'
         - '/events/search'
      3) Visit detail pages, parse JSON-LD, normalize fields.

    This fallback only triggers when initial link extraction yields zero links,
    so working sources (e.g., Rhinelander) behave exactly as before.
    """

    log = logger.debug if hasattr(logger, "debug") else (lambda *_args, **_kw: None)
    warn = logger.warning if hasattr(logger, "warning") else (lambda *_args, **_kw: None)

    # ------------- helpers -------------
    def _extract_links(page_html: str, base_url: str) -> Set[str]:
        links: Set[str] = set()
        # absolute links
        for m in re.finditer(
            r'href=["\'](https?://[^"\']*/events/details/[^"\']+)["\']', page_html, flags=re.I
        ):
            links.add(m.group(1))
        # relative links
        for m in re.finditer(r'href=["\'](/events/details/[^"\']+)["\']', page_html, flags=re.I):
            links.add(urljoin(base_url, m.group(1)))
        return links

    def _same_host_events_root(url: str) -> str:
        # Return '<scheme>://<host>/events'
        parts = urlparse(url)
        root = f"{parts.scheme}://{parts.netloc}"
        if "/events" in parts.path:
            root += parts.path.split("/events", 1)[0]
        return f"{root}/events"

    def _iso_months(start_ym: Tuple[int, int], count: int = 4) -> List[str]:
        y, m = start_ym
        out: List[str] = []
        for i in range(count):
            yy = y + (m - 1 + i) // 12
            mm = (m - 1 + i) % 12 + 1
            out.append(f"{yy:04d}-{mm:02d}-01")
        return out

    def _jsonld_events(html: str) -> List[Dict[str, Any]]:
        events: List[Dict[str, Any]] = []
        # Gather all JSON-LD blocks; pick those that look like Event(s)
        for script_match in re.finditer(
            r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
            html,
            flags=re.I | re.S,
        ):
            block = script_match.group(1).strip()
            try:
                data = json.loads(block)
            except Exception:
                continue

            def _maybe_add(d: Dict[str, Any]) -> None:
                # Accept if @type includes "Event"
                atype = d.get("@type")
                if isinstance(atype, list):
                    ok = any(str(t).lower() == "event" for t in atype)
                else:
                    ok = str(atype).lower() == "event"
                if ok:
                    events.append(d)

            if isinstance(data, dict):
                if "@type" in data:
                    _maybe_add(data)
                # JSON-LD graph container
                if "@graph" in data and isinstance(data["@graph"], list):
                    for node in data["@graph"]:
                        if isinstance(node, dict):
                            _maybe_add(node)
            elif isinstance(data, list):
                for node in data:
                    if isinstance(node, dict):
                        _maybe_add(node)
        return events

    def _norm_dt(s: Optional[str]) -> Optional[str]:
        if not s:
            return None
        # Leave as-is (ISO-like); downstream usually interprets to timezone later
        return s

    def _norm_place(loc: Any) -> Optional[str]:
        if not loc:
            return None
        if isinstance(loc, dict):
            # Try common properties
            for key in ("name", "address", "streetAddress"):
                v = loc.get(key)
                if v:
                    if isinstance(v, dict):
                        # address object -> join simple fields
                        parts = [str(loc.get(k, "")).strip() for k in ("streetAddress", "addressLocality", "addressRegion")]
                        return ", ".join([p for p in parts if p])
                    return str(v)
            # fall back to stringified dict
            return str(loc)
        return str(loc)

    # ------------- 1) initial listing fetch -------------
    log(f"[growthzone_html] GET {base}")
    resp = session.get(base, timeout=timeout)
    resp.raise_for_status()
    html = resp.text

    links = _extract_links(html, base)
    log(f"[growthzone_html] initial links: {len(links)}")

    # ------------- 2) guarded fallbacks (ONLY if 0 links) -------------
    if not links:
        root = _same_host_events_root(base)
        candidates: List[str] = []

        # alpha list view
        candidates.append(base + ("&o=alpha" if "?" in base else "?o=alpha"))
        # canonical calendar & search
        candidates.append(f"{root}/calendar")
        candidates.append(f"{root}/search")

        # try a few upcoming months to catch server-rendered month pages
        today = datetime.utcnow().date().replace(day=1)
        months = _iso_months((today.year, today.month), count=4)
        for month_start in months:
            candidates.append(f"{root}/calendar/{month_start}")

        for alt in candidates:
            try:
                log(f"[growthzone_html] fallback GET {alt}")
                r2 = session.get(alt, timeout=timeout)
                if not r2.ok:
                    continue
                cand = _extract_links(r2.text, alt)
                log(f"[growthzone_html] fallback links from {alt}: {len(cand)}")
                if cand:
                    links |= cand
                    # We don't need to probe further once we have links.
                    break
            exc
