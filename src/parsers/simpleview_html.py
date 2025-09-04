"""
Simpleview HTML parser.

Exports:
    fetch_simpleview_html

Why this exists:
    - main.py imports `fetch_simpleview_html` from `src.parsers`
      which delegates to this module via parsers/__init__.py.
    - Prior builds failed because this function wasn't defined here.

What it does:
    - Loads a Simpleview events listing page (e.g. https://www.minocqua.org/events/)
    - Extracts Event data from JSON-LD blocks (schema.org/Event)
    - Normalizes URLs and datetimes
    - Optionally filters by an inclusive [start_date, end_date] window if provided

Return shape (list of dicts):
    {
        "title": str,
        "start_utc": str (ISO 8601 in UTC),
        "end_utc": Optional[str] (ISO 8601 in UTC) or None,
        "url": str (absolute),
        "location": Optional[str],
        "source": str,     # e.g., "Let's Minocqua (Simpleview)"
        "calendar": str    # same as source (kept for downstream consistency)
    }
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Tuple
from urllib.parse import urljoin

from bs4 import BeautifulSoup

# Soft deps to match project conventions.
try:
    import requests
except Exception:  # pragma: no cover - runner has requests via requirements.txt
    requests = None  # type: ignore


__all__ = ["fetch_simpleview_html"]


def _to_utc_iso(dt_str: str) -> Optional[str]:
    """
    Convert any ISO-ish datetime string to a strict UTC ISO8601 string.
    Returns None if parsing fails or input is falsy.
    """
    if not dt_str:
        return None
    try:
        # Handle common cases: full ISO8601 with or without timezone
        # Fall back: treat naive times as local-less (assume UTC).
        dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        else:
            dt = dt.astimezone(timezone.utc)
        return dt.isoformat()
    except Exception:
        # Some Simpleview feeds store date only (YYYY-MM-DD)
        # Treat date-only as midnight UTC start.
        try:
            d = datetime.strptime(dt_str, "%Y-%m-%d")
            return d.replace(tzinfo=timezone.utc).isoformat()
        except Exception:
            return None


def _load(source_url: str, session: Optional[requests.Session] = None) -> str:
    sess = session or requests.Session()
    resp = sess.get(source_url, timeout=30)
    resp.raise_for_status()
    return resp.text


def _iter_jsonld_events(soup: BeautifulSoup) -> Iterable[Dict[str, Any]]:
    """
    Yield dictionaries that look like schema.org Event from all JSON-LD blocks.
    Handles single object or list payloads and @type variations ("Event" or contains it).
    """
    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        text = script.string or script.get_text() or ""
        if not text.strip():
            continue
        try:
            data = json.loads(text)
        except Exception:
            continue

        def maybe_yield(obj: Any):
            if isinstance(obj, dict):
                typ = obj.get("@type")
                # @type can be "Event" or ["Thing", "Event"]
                if (typ == "Event") or (isinstance(typ, list) and "Event" in typ):
                    yield obj
            elif isinstance(obj, list):
                for it in obj:
                    yield from maybe_yield(it)

        yield from maybe_yield(data)


def _location_to_text(loc_obj: Any) -> Optional[str]:
    """
    Flatten a schema.org Place/PostalAddress into a readable string.
    """
    if not loc_obj:
        return None
    try:
        if isinstance(loc_obj, str):
            return loc_obj.strip() or None

        if isinstance(loc_obj, dict):
            # Event.location may be a Place with 'name' and 'address'
            if loc_obj.get("@type") == "Place":
                name = (loc_obj.get("name") or "").strip()
                addr = loc_obj.get("address")
                addr_txt = _location_to_text(addr)
                if name and addr_txt:
                    return f"{name}, {addr_txt}"
                return name or addr_txt

            # Or a PostalAddress directly
            if loc_obj.get("@type") == "PostalAddress":
                parts = [
                    (loc_obj.get("streetAddress") or "").strip(),
                    (loc_obj.get("addressLocality") or "").strip(),
                    (loc_obj.get("addressRegion") or "").strip(),
                ]
                # drop empties and compress spaces
                parts = [p for p in parts if p]
                return ", ".join(parts) or None

            # Fallback: try common address-like fields
            parts = [
                (loc_obj.get("name") or "").strip(),
                (loc_obj.get("streetAddress") or "").strip(),
                (loc_obj.get("addressLocality") or "").strip(),
                (loc_obj.get("addressRegion") or "").strip(),
            ]
            parts = [p for p in parts if p]
            return ", ".join(parts) or None
    except Exception:
        return None
    return None


def _within_window(
    start_iso_utc: Optional[str],
    start_date: Optional[datetime],
    end_date: Optional[datetime],
) -> bool:
    if not start_iso_utc or (not start_date and not end_date):
        return True  # no filtering requested or no start => keep
    try:
        dt = datetime.fromisoformat(start_iso_utc.replace("Z", "+00:00"))
    except Exception:
        return True
    if start_date and dt < start_date.replace(tzinfo=timezone.utc):
        return False
    if end_date and dt > end_date.replace(tzinfo=timezone.utc):
        return False
    return True


def fetch_simpleview_html(
    source: Any,
    session: Optional[requests.Session] = None,
    *,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    logger: Optional[Any] = None,
) -> List[Dict[str, Any]]:
    """
    Fetch & parse events from a Simpleview listing page.

    Parameters
    ----------
    source : str | dict
        - If str: treated as the base URL (e.g., "https://www.minocqua.org/events/")
        - If dict: expects keys:
            { "url": <base_url>, "name": <display/source name> }
    session : requests.Session, optional
    start_date, end_date : datetime, optional
        Inclusive window filter. If omitted, all future-ish events pass.
    logger : any, optional
        Object with .info/.warning/.error; used if provided.

    Returns
    -------
    List[Dict[str, Any]]
        Normalized events (see module docstring).
    """
    # Normalize source input
    if isinstance(source, str):
        base_url = source
        source_name = "Let's Minocqua (Simpleview)"
    elif isinstance(source, dict):
        base_url = source.get("url") or source.get("base_url") or ""
        source_name = source.get("name") or source.get("source") or "Simpleview"
    else:
        raise TypeError("source must be a str or dict")

    if not base_url:
        raise ValueError("Simpleview parser requires a non-empty 'url'")

    if logger:
        logger.info(f"[simpleview] GET {base_url}")

    html = _load(base_url, session=session)
    soup = BeautifulSoup(html, "html.parser")

    results: List[Dict[str, Any]] = []
    now_utc = datetime.now(timezone.utc)

    for ev in _iter_jsonld_events(soup):
        title = (ev.get("name") or "").strip()
        url = (ev.get("url") or "").strip()
        if url:
            url = urljoin(base_url, url)  # normalize relative to absolute

        start_utc = _to_utc_iso(ev.get("startDate") or ev.get("startTime") or "")
        end_utc = _to_utc_iso(ev.get("endDate") or ev.get("endTime") or "")

        # Skip clearly past events if no explicit window provided
        if not start_date and not end_date and start_utc:
            try:
                start_dt = datetime.fromisoformat(start_utc.replace("Z", "+00:00"))
                if start_dt < now_utc:
                    continue
            except Exception:
                pass

        if not _within_window(start_utc, start_date, end_date):
            continue

        location_txt = _location_to_text(ev.get("location"))
        results.append(
            {
                "title": title or "Untitled Event",
                "start_utc": start_utc,
                "end_utc": end_utc,
                "url": url,
                "location": location_txt,
                "source": source_name,
                "calendar": source_name,
            }
        )

    if logger:
        logger.info(f"[simpleview] parsed {len(results)} events from {base_url}")

    return results
