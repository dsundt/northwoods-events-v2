# src/main.py
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import yaml

# ---- Required parsers available in this repo ----
from src.parsers import (
    fetch_tec_rest,          # expects: (url: str, start_utc: str | None, end_utc: str | None, ...)
    fetch_growthzone_html,   # expects: (source: dict, [session], [start_date], [end_date])
    fetch_simpleview_html,   # expects: (url: str, timeout=20, max_items=200)
    fetch_tec_html,          # expects: (source: dict, [session], [start_date], [end_date])
)

# ---- Optional parsers (guard so builds never break if missing) ----
try:
    # In this repo, ICS fetcher is named fetch_ics(url, start_utc, end_utc)
    from src.parsers.ics_feed import fetch_ics as _fetch_ics_raw  # type: ignore
except Exception:
    _fetch_ics_raw = None

try:
    # St. Germain WordPress crawler (only used if you add a st-germain-wp source)
    from src.parsers import fetch_stgermain_wp  # exported by src/parsers/__init__.py
except Exception:
    fetch_stgermain_wp = None


# ---------------------- config ----------------------

DEFAULT_WINDOW_FWD = int(os.getenv("NW_WINDOW_FWD_DAYS", "180"))
REPORT_JSON_PATH = os.getenv("NW_REPORT_JSON", "report.json")
SOURCES_YAML = os.getenv("NW_SOURCES_YAML", "config/sources.yaml")


def _window() -> tuple[datetime, datetime]:
    now = datetime.now(timezone.utc)
    return now - timedelta(days=1), now + timedelta(days=DEFAULT_WINDOW_FWD)


def _fmt_date_only(dt: datetime) -> str:
    # For TEC/ICS REST endpoints that want YYYY-MM-DD
    return dt.strftime("%Y-%m-%d")


def _normalize_event(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Lenient normalization for report.json preview only (does NOT affect icsbuild)."""
    title = raw.get("title") or raw.get("name") or "(untitled)"
    start = raw.get("start_utc") or raw.get("start")
    end = raw.get("end_utc") or raw.get("end")
    return {
        "calendar": raw.get("source") or "Unknown",
        "title": title,
        "start_utc": start,
        "end_utc": end,
        "location": raw.get("location"),
        "url": raw.get("url") or raw.get("link"),
        "_source": raw.get("_source"),
    }


def _fetch_one(source: Dict[str, Any], start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
    """
    Route per source.type and call each parser with the signature it expects.
    This is the key to avoid breaking working calendars.
    """
    stype = (source.get("type") or "").strip()
    url = source.get("url") or ""
    name = source.get("name") or source.get("id") or stype

    # TEC REST (The Events Calendar REST)
    if stype == "tec_rest":
        if not url:
            raise RuntimeError("tec_rest: missing url")
        return fetch_tec_rest(
            url=url,
            start_utc=_fmt_date_only(start_date),
            end_utc=_fmt_date_only(end_date),
        ) or []

    # GrowthZone HTML (expects source dict + optional dates)
    if stype == "growthzone_html":
        return fetch_growthzone_html(
            source=source,
            start_date=start_date,
            end_date=end_date,
        ) or []

    # TEC HTML (expects source dict + optional dates)
    if stype == "tec_html":
        return fetch_tec_html(
            source=source,
            start_date=start_date,
            end_date=end_date,
        ) or []

    # Simpleview HTML (RSS) expects a URL string
    if stype == "simpleview_html":
        if not url:
            raise RuntimeError("simpleview_html: missing url")
        return fetch_simpleview_html(url) or []

    # ICS feed (optional) – use raw function if present
    if stype == "ics_feed":
        if _fetch_ics_raw is None:
            raise RuntimeError("ics_feed: parser not available")
        if not url:
            raise RuntimeError("ics_feed: missing url")
        return _fetch_ics_raw(url, _fmt_date_only(start_date), _fmt_date_only(end_date)) or []

    # St. Germain WordPress crawler (optional, isolated)
    if stype == "stgermain_wp":
        if fetch_stgermain_wp is None:
            raise RuntimeError("stgermain_wp: parser not available")
        return fetch_stgermain_wp(
            source=source,
            start_date=start_date,
            end_date=end_date,
        ) or []

    raise RuntimeError(f"Unsupported source type: {stype}")


def main() -> int:
    # 1) Load sources.yaml
    print(f"[northwoods] Loading sources from: {SOURCES_YAML}")
    try:
        with open(SOURCES_YAML, "r", encoding="utf-8") as f:
            sources = yaml.safe_load(f)
    except Exception as e:
        print(f"[northwoods] ERROR reading {SOURCES_YAML}: {e}")
        return 2

    if not isinstance(sources, list):
        print("[northwoods] ERROR: sources.yaml must be a list.")
        return 2

    start_date, end_date = _window()

    all_events: List[Dict[str, Any]] = []
    source_logs: List[Dict[str, Any]] = []

    # 2) Fetch each source
    for src in sources:
        stype = src.get("type")
        sid = src.get("id")
        name = src.get("name") or sid or (stype or "Unknown")
        url = src.get("url") or ""

        print(f"[northwoods] Fetching: {name} ({sid}) [{stype}] -> {url}")

        per_source_events: List[Dict[str, Any]] = []
        err_msg: Optional[str] = None

        try:
            per_source_events = _fetch_one(src, start_date, end_date) or []
        except Exception as e:
            err_msg = str(e)
            print(f"[northwoods] ERROR while fetching {name}: {err_msg}")

        source_logs.append({
            "id": sid,
            "name": name,
            "type": stype,
            "url": url,
            "ok": err_msg is None,
            "count": len(per_source_events),
            "error": err_msg,
        })
        all_events.extend(per_source_events)

    # 3) Build report.json preview
    normalized_preview = [_normalize_event(e) for e in all_events]

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "sources_processed": len(source_logs),
        "total_events": len(all_events),
        "source_logs": source_logs,
        "normalized_events": normalized_preview[:500],
        "events_preview_count": min(500, len(normalized_preview)),
    }

    try:
        with open(REPORT_JSON_PATH, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"[northwoods] ERROR writing report.json: {e}")

    print(json.dumps({"ok": True, "events": len(all_events)}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
