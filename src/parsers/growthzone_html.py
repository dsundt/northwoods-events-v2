# src/parsers/growthzone_html.py
# GrowthZone/ChamberMaster HTML parser with guarded fallbacks.
# NEW: St. Germain–only cross-domain fallback to TEC event pages when the
# GrowthZone calendar exposes *only* outbound st-germain.com/events/... links.

import re
import json
from datetime import datetime, date
from typing import Any, Dict, List, Optional, Set
from urllib.parse import urljoin, urlparse


def fetch_growthzone_html(*args, **kwargs):
    """
    Call shapes supported by the existing runner:
      (source)
      (source, session)
      (source, start_date, end_date)
      (source, session, start_date, end_date)
    plus keyword args: session=, start_date=, end_date=
    """
    # ---------- signature & source ----------
    source = args[0] if args else kwargs.get("source")
    session = kwargs.get("session")
    start_date = kwargs.get("start_date")
    end_date = kwargs.get("end_date")

    # positional unpacking after `source`:
    rest = list(args[1:])
    if rest and hasattr(rest[0], "get"):  # requests.Session-like
        session = rest.pop(0)
    if rest:
        start_date = rest.pop(0)
    if rest:
        end_date = rest.pop(0)

    base = source if isinstance(source, str) else (source.get("url") if source else None)
    name = "GrowthZone" if isinstance(source, str) else (source.get("name") or "GrowthZone")
    if not base:
        return []

    own = False
    if session is None:
        import requests
        session = requests.Session()
        own = True

    def _log(msg: str) -> None:
        logger = kwargs.get("logger")
        if logger and hasattr(logger, "debug"):
            try:
                logger.debug(msg)
            except Exception:
                pass

    def _warn(msg: str) -> None:
        logger = kwargs.get("logger")
        if logger and hasattr(logger, "warning"):
            try:
                logger.warning(msg)
            except Exception:
                pass

    # ---------- helpers ----------
    def _extract_gz_detail_links(page_html: str, page_base: str) -> Set[str]:
        links: Set[str] = set()
        # absolute /events/details/...
        for m in re.finditer(r'href=["\'](https?://[^"\']*/events/details/[^"\']+)["\']', page_html, flags=re.I):
            links.add(m.group(1))
        # relative /events/details/...
        for m in re.finditer(r'href=["\'](/events/details/[^"\']+)["\']', page_html, flags=re.I):
            links.add(urljoin(page_base, m.group(1)))
        return links

    def _extract_stgermain_outbound(page_html: str) -> Set[str]:
        # St. Germain GrowthZone often links out to st-germain.com/events/...
        links: Set[str] = set()
        for m in re.finditer(r'href=["\'](https?://st-germain\.com/events/[^"\']+)["\']', page_html, flags=re.I):
            links.add(m.group(1))
        return links

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
        out = []
        for i in range(n):
            yy = ys + (ms - 1 + i) // 12
            mm = (ms - 1 + i) % 12 + 1
            out.append(f"{yy:04d}-{mm:02d}-01")
        return out

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

    def _coerce_dt(s: Optional[str]) -> Optional[str]:
        return s or None

    def _norm_place(loc: Any) -> Optional[str]:
        if not loc:
            return None
        if isinstance(loc, dict):
            if loc.get("name"):
                return str(loc["name"])
            parts = [str(loc.get(k, "")).strip() for k in ("streetAddress", "addressLocality", "addressRegion")]
            joined = ", ".join([p for p in parts if p])
            return joined or json.dumps(loc)
        return str(loc)

    def _detail_to_event(detail_html: str, page_url: str, source_name: str) -> Optional[Dict[str, Any]]:
        jsonld = _jsonld_events(detail_html)
        if not jsonld:
            return {"url": page_url, "_source": "growthzone_html"}
        out: List[Dict[str, Any]] = []
        for ev in jsonld:
            title = ev.get("name") or ev.get("headline") or "(untitled)"
            start = _coerce_dt(ev.get("startDate"))
            end = _coerce_dt(ev.get("endDate"))
            loc = _norm_place(ev.get("location"))
            out.append(
                {
                    "title": title,
                    "start": start,
                    "end": end,
                    "location": loc,
                    "url": page_url,
                    "description": ev.get("description"),
                    "jsonld": ev,
                    "source": source_name,
                    "_source": "growthzone_html",
                }
            )
        # prefer first event node
        return out[0] if out else None

    def _filter_range(events: List[Dict[str, Any]], sdt, edt) -> List[Dict[str, Any]]:
        if not sdt or not edt:
            return events
        out: List[Dict[str, Any]] = []
        for ev in events:
            s = ev.get("start")
            if not s:
                continue
            # keep ISO-like strings; caller may normalize TZ later
            try:
                # accept YYYY-MM-DD or YYYY-MM-DDTHH:MM
                if len(s) == 10:
                    dt = datetime.strptime(s, "%Y-%m-%d")
                else:
                    # strip timezone if present (best-effort)
                    s2 = s.replace("Z", "+00:00")
                    # handle common shape
                    dt = datetime.fromisoformat(s2.split("+")[0])
            except Exception:
                continue
            if sdt <= dt <= edt:
                out.append(ev)
        return out

    # ---------- 1) fetch listing ----------
    _log(f"[growthzone_html] GET {base}")
    resp = session.get(base, timeout=30)
    resp.raise_for_status()
    html = resp.text

    links = _extract_gz_detail_links(html, base)
    _log(f"[growthzone_html] initial gz-detail links: {len(links)}")

    # ---------- 2) standard fallbacks (only if zero links) ----------
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
                _log(f"[growthzone_html] fallback GET {alt}")
                r2 = session.get(alt, timeout=30)
                if not r2.ok:
                    continue
                cand = _extract_gz_detail_links(r2.text, alt)
                _log(f"[growthzone_html] fallback gz-detail links from {alt}: {len(cand)}")
                if cand:
                    links |= cand
                    break
                # ---------- 2a) St. Germain–only cross-domain fallback ----------
                # If host is stgermainwi.chambermaster.com and still no GZ detail links,
                # collect outbound st-germain.com/events/... anchors (TEC pages).
                host = urlparse(base).netloc.lower()
                if "stgermainwi.chambermaster.com" in host and not links:
                    extra = _extract_stgermain_outbound(r2.text)
                    if extra:
                        _log(f"[growthzone_html] collected {len(extra)} outbound TEC links for St. Germain")
                        # We don't 'break' here; we'll proceed to detail fetch below using `links | extra`.
                        links |= extra
                        break
            except Exception as e:
                _warn(f"[growthzone_html] fallback error on {alt}: {e}")

    if not links:
        _log("[growthzone_html] no links discovered after fallbacks")
        return []

    # ---------- 3) visit detail pages & parse JSON-LD ----------
    events: List[Dict[str, Any]] = []
    for href in sorted(links):
        try:
            _log(f"[growthzone_html] detail GET {href}")
            r = session.get(href, timeout=30)
            if not r.ok:
                continue
            ev = _detail_to_event(r.text, href, name)
            if ev and (ev.get("start") or ev.get("start_utc")):
                # unify to 'start'/'end' keys for downstream normalizer
                if "start_utc" in ev and not ev.get("start"):
                    ev["start"] = ev.pop("start_utc")
                if "end_utc" in ev and not ev.get("end"):
                    ev["end"] = ev.pop("end_utc")
                events.append(ev)
        except Exception as e:
            _warn(f"[growthzone_html] error parsing {href}: {e}")
            continue

    # ---------- 4) optional date filter ----------
    if start_date and end_date:
        events = _filter_range(events, start_date, end_date)

    # done
    return events

