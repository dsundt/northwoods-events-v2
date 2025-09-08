# src/parsers/growthzone_html.py
# GrowthZone/ChamberMaster HTML parser with a guarded fallback for JS-heavy listings.
# Backward/forward compatible signature: supports callers passing url=... or positional base.

import re
import json
from datetime import datetime, date
from typing import Any, Dict, List, Optional, Set
from urllib.parse import urljoin, urlparse


def fetch_growthzone_html(
    session,
    url: Optional[str] = None,           # allow keyword-style callers
    base: Optional[str] = None,          # allow legacy positional/keyword
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
    Steps
    -----
    1) GET listing and extract /events/details/... links.
    2) If zero links found, probe SSR variants on same host:
       '?o=alpha', '/events/calendar', '/events/search',
       and a few month pages: '/events/calendar/YYYY-MM-01'
    3) Visit detail pages; parse JSON-LD; normalize minimal fields.

    Safety
    ------
    The fallback ONLY runs when the first page yields zero links.
    Working sources (e.g., Rhinelander) behave exactly as before.
    """

    # Resolve base URL from various caller styles
    base_url = base or url or kwargs.get("source_url") or kwargs.get("start_url")
    if not base_url:
        raise ValueError("growthzone_html: no URL provided (expected url= or base=)")

    # --- logger shims ---
    def _log(msg: str) -> None:
        if logger and hasattr(logger, "debug"):
            try:
                logger.debug(msg)
            except Exception:
                pass

    def _warn(msg: str) -> None:
        if logger and hasattr(logger, "warning"):
            try:
                logger.warning(msg)
            except Exception:
                pass

    # --- helpers ---
    def _extract_links(page_html: str, page_base: str) -> Set[str]:
        links: Set[str] = set()
        # absolute detail links
        for m in re.finditer(
            r'href=["\'](https?://[^"\']*/events/details/[^"\']+)["\']',
            page_html,
            flags=re.I,
        ):
            links.add(m.group(1))
        # relative detail links
        for m in re.finditer(
            r'href=["\'](/events/details/[^"\']+)["\']',
            page_html,
            flags=re.I,
        ):
            links.add(urljoin(page_base, m.group(1)))
        return links

    def _events_root_same_host(u: str) -> str:
        parts = urlparse(u)
        root = f"{parts.scheme}://{parts.netloc}"
        path = parts.path or ""
        if "/events" in path:
            root += path.split("/events", 1)[0]
        return f"{root}/events"

    def _month_starts(count: int = 4) -> List[str]:
        first = datetime.utcnow().date().replace(day=1)
        ys = first.year
        ms = first.month
        out: List[str] = []
        for i in range(count):
            yy = ys + (ms - 1 + i) // 12
            mm = (ms - 1 + i) % 12 + 1
            out.append(f"{yy:04d}-{mm:02d}-01")
        return out

    def _jsonld_events(html: str) -> List[Dict[str, Any]]:
        events: List[Dict[str, Any]] = []
        for sm in re.finditer(
            r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
            html,
            flags=re.I | re.S,
        ):
            block = sm.group(1).strip()
            try:
                data = json.loads(block)
            except Exception:
                continue

            def _maybe_add(node: Dict[str, Any]) -> None:
                t = node.get("@type")
                if isinstance(t, list):
                    ok = any(str(x).lower() == "event" for x in t)
                else:
                    ok = str(t).lower() == "event"
                if ok:
                    events.append(node)

            if isinstance(data, dict):
                if "@type" in data:
                    _maybe_add(data)
                g = data.get("@graph")
                if isinstance(g, list):
                    for n in g:
                        if isinstance(n, dict):
                            _maybe_add(n)
            elif isinstance(data, list):
                for n in data:
                    if isinstance(n, dict):
                        _maybe_add(n)
        return events

    def _norm_dt(s: Optional[str]) -> Optional[str]:
        return s or None

    def _norm_place(loc: Any) -> Optional[str]:
        if not loc:
            return None
        if isinstance(loc, dict):
            name = loc.get("name")
            if name:
                return str(name)
            parts = [
                str(loc.get("streetAddress", "")).strip(),
                str(loc.get("addressLocality", "")).strip(),
                str(loc.get("addressRegion", "")).strip(),
            ]
            joined = ", ".join([p for p in parts if p])
            return joined or json.dumps(loc)
        return str(loc)

    # --- 1) initial listing fetch ---
    _log(f"[growthzone_html] GET {base_url}")
    resp = session.get(base_url, timeout=timeout)
    resp.raise_for_status()
    html = resp.text

    links = _extract_links(html, base_url)
    _log(f"[growthzone_html] initial links: {len(links)}")

    # --- 2) guarded fallbacks (only if zero links) ---
    if not links:
        root = _events_root_same_host(base_url)
        candidates: List[str] = []

        # alpha list view (same URL with param)
        candidates.append(base_url + ("&o=alpha" if "?" in base_url else "?o=alpha"))
        # canonical calendar & search on same host
        candidates.append(f"{root}/calendar")
        candidates.append(f"{root}/search")
        # a few upcoming month pages (SSR per-month calendars)
        for iso_day in _month_starts(count=4):
            candidates.append(f"{root}/calendar/{iso_day}")

        for alt in candidates:
            try:
                _log(f"[growthzone_html] fallback GET {alt}")
                r2 = session.get(alt, timeout=timeout)
                if not r2.ok:
                    continue
                cand = _extract_links(r2.text, alt)
                _log(f"[growthzone_html] fallback links from {alt}: {len(cand)}")
                if cand:
                    links |= cand
                    break
            except Exception as e:
                _warn(f"[growthzone_html] fallback error on {alt}: {e}")

    if not links:
        _log("[growthzone_html] no detail links discovered after fallbacks")
        return []

    # --- 3) detail pages & JSON-LD ---
    events: List[Dict[str, Any]] = []
    for i, detail_url in enumerate(sorted(links)):
        if i >= max_events:
            break
        try:
            _log(f"[growthzone_html] detail GET {detail_url}")
            r = session.get(detail_url, timeout=timeout)
            if not r.ok:
                continue
            dhtml = r.text

            jsonld = _jsonld_events(dhtml)
            if not jsonld:
                # minimal placeholder if no JSON-LD present
                events.append({"url": detail_url, "_source": "growthzone_html"})
                continue

            for ev in jsonld:
                title = ev.get("name") or ev.get("headline")
                start = _norm_dt(ev.get("startDate"))
                end = _norm_dt(ev.get("endDate"))
                location = _norm_place(ev.get("location"))
                desc = ev.get("description")

                events.append(
                    {
                        "title": title,
                        "start": start,
                        "end": end,
                        "location": location,
                        "url": detail_url,
                        "description": desc,
                        "jsonld": ev,
                        "_source": "growthzone_html",
                    }
                )
        except Exception as e:
            _warn(f"[growthzone_html] error parsing {detail_url}: {e}")
            continue

    _log(f"[growthzone_html] parsed events: {len(events)}")
    return events
