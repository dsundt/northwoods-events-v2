# src/main.py
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import yaml

# ---- Parsers in this repo ----
from src.parsers import (
    fetch_tec_rest,          # POSitional: (url: str, start_utc: str|None, end_utc: str|None)
    fetch_growthzone_html,   # kwargs:     (source: dict, [session], [start_date], [end_date])
    fetch_simpleview_html,   # POSitional: (url: str, timeout=20, max_items=200)
    fetch_tec_html,          # kwargs:     (source: dict, [session], [start_date], [end_date])
)

# Optional: ICS
try:
    # In this repo: fetch_ics(url, start_utc, end_utc) — POSitional
    from src.parsers.ics_feed import fetch_ics as _fetch_ics_raw  # type: ignore
except Exception:
    _fetch_ics_raw = None

# Optional: St. Germain WP (only if present + enabled in sources.yaml)
try:
    from src.parsers import fetch_stgermain_wp
except Exception:
    fetch_stgermain_wp = None

DEFAULT_WINDOW_FWD = int(os.getenv("NW_WINDOW_FWD_DAYS", "180"))
REPORT_JSON_PATH = os.getenv("NW_REPORT_JSON", "report.json")
BY_SOURCE_DIR = os.getenv("NW_BY_SOURCE_DIR", "by-source")
SOURCES_YAML = os.getenv("NW_SOURCES_YAML", "config/sources.yaml")

def _window() -> tuple[datetime, datetime]:
    now = datetime.now(timezone.utc)
    return now - timedelta(days=1), now + timedelta(days=DEFAULT_WINDOW_FWD)

def _ymd(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d")

def _normalize_event(raw: Dict[str, Any]) -> Dict[str, Any]:
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
    stype = (source.get("type") or "").strip()
    url = source.get("url") or ""

    if stype == "tec_rest":
        if not url: raise RuntimeError("tec_rest: missing url")
        return fetch_tec_rest(url, _ymd(start_date), _ymd(end_date)) or []

    if stype == "growthzone_html":
        return fetch_growthzone_html(source=source, start_date=start_date, end_date=end_date) or []

    if stype == "tec_html":
        return fetch_tec_html(source=source, start_date=start_date, end_date=end_date) or []

    if stype == "simpleview_html":
        if not url: raise RuntimeError("simpleview_html: missing url")
        return fetch_simpleview_html(url) or []

    if stype == "ics_feed":
        if _fetch_ics_raw is None:
            raise RuntimeError("ics_feed: parser not available")
        if not url:
            raise RuntimeError("ics_feed: missing url")
        return _fetch_ics_raw(url, _ymd(start_date), _ymd(end_date)) or []

    if stype == "stgermain_wp":
        if fetch_stgermain_wp is None:
            raise RuntimeError("stgermain_wp: parser not available")
        return fetch_stgermain_wp(source=source, start_date=start_date, end_date=end_date) or []

    raise RuntimeError(f"Unsupported source type: {stype}")

def _ensure_dir(path: str) -> None:
    try: os.makedirs(path, exist_ok=True)
    except Exception: pass

def _write_json(path: str, payload: dict) -> None:
    _ensure_dir(os.path.dirname(path) or ".")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

def _mirror_report(report: Dict[str, Any]) -> None:
    # Primary
    _write_json(REPORT_JSON_PATH, report)
    # Always create and write GitHub Pages mirrors so you can view online
    for root in ("github-pages", "docs"):
        _write_json(os.path.join(root, "report.json"), report)

def _write_debug_source(sid: str, name: str, stype: str, url: str,
                        ok: bool, err_msg: Optional[str], events: List[Dict[str, Any]]) -> None:
    blob = {
        "source": {"id": sid, "name": name, "type": stype, "url": url},
        "ok": ok,
        "error": err_msg,
        "count": len(events),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "events": events[:500],
    }
    # local
    _write_json(os.path.join(BY_SOURCE_DIR, f"{sid or name}.json"), blob)
    # pages mirrors
    for root in ("github-pages", "docs"):
        _write_json(os.path.join(root, "by-source", f"{sid or name}.json"), blob)

def main() -> int:
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

    _ensure_dir(BY_SOURCE_DIR)
    _ensure_dir("github-pages/by-source")
    _ensure_dir("docs/by-source")

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

        # write per-source debug in two places (local + pages)
        try:
            _write_debug_source(sid, name, stype, url, err_msg is None, err_msg, per_source_events)
        except Exception:
            pass

        source_logs.append({
            "id": sid, "name": name, "type": stype, "url": url,
            "ok": err_msg is None, "count": len(per_source_events), "error": err_msg,
        })
        all_events.extend(per_source_events)

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
        _mirror_report(report)
    except Exception as e:
        print(f"[northwoods] ERROR writing report.json: {e}")

    print(json.dumps({"ok": True, "events": len(all_events)}))
    return 0

if __name__ == "__main__":
    sys.exit(main())
