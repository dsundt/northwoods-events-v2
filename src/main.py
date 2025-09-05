# src/main.py
from __future__ import annotations

import json
import os
import sys
import traceback
from datetime import datetime, timedelta
from typing import Dict, List, Any

import yaml

from src.parsers import (
    fetch_tec_rest,
    fetch_tec_html,
    fetch_growthzone_html,
    fetch_simpleview_html,
)
from src.ics_writer import write_combined_ics, write_per_source_ics  # existing file

PUBLIC_DIR = "public"
BY_SOURCE_DIR = os.path.join(PUBLIC_DIR, "by-source")
COMBINED_ICS_PATH = os.path.join(PUBLIC_DIR, "combined.ics")
REPORT_JSON_PATH = os.path.join(PUBLIC_DIR, "report.json")
INDEX_HTML_PATH = os.path.join(PUBLIC_DIR, "index.html")

SOURCES_YAML = "config/sources.yaml"
DEFAULT_WINDOW_DAYS = 120  # about 4 months


def _slugify(s: str) -> str:
    """Lightweight slugify (no external deps)."""
    return (
        (s or "")
        .lower()
        .strip()
        .replace("’", "")
        .replace("'", "")
        .replace("&", "and")
        .replace(" ", "-")
        .replace("--", "-")
    )


def _load_sources() -> List[Dict[str, Any]]:
    path = SOURCES_YAML
    print(f"[northwoods] Loading sources from: {path}")
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if isinstance(data, dict) and "sources" in data:
        sources = data["sources"]
    elif isinstance(data, list):
        sources = data
    else:
        raise ValueError(f"Expected a list or 'sources' map in {path}, got {type(data)}")

    # Normalize and ensure IDs
    for i, src in enumerate(sources):
        if "id" not in src or not src["id"]:
            gen = f"{_slugify(src.get('name') or 'source')}-{_slugify(src.get('type') or 'type')}"
            print(f"[northwoods] Source #{i} missing 'id' -> auto-generated '{gen}'")
            src["id"] = gen
    return sources


def _ensure_dirs() -> None:
    os.makedirs(PUBLIC_DIR, exist_ok=True)
    os.makedirs(BY_SOURCE_DIR, exist_ok=True)


def _date_window() -> (str, str):
    start = datetime.utcnow().strftime("%Y-%m-%d")
    end = (datetime.utcnow() + timedelta(days=DEFAULT_WINDOW_DAYS)).strftime("%Y-%m-%d")
    return start, end


def _dispatch_fetch(source: Dict[str, Any], start_date: str, end_date: str) -> List[Dict[str, Any]]:
    stype = (source.get("type") or "").strip().lower()
    if stype == "tec_rest":
        return fetch_tec_rest(source, start_date, end_date)
    if stype == "tec_html":
        return fetch_tec_html(source, start_date, end_date)
    if stype == "growthzone_html":
        return fetch_growthzone_html(source, start_date, end_date)
    if stype == "simpleview_html":
        return fetch_simpleview_html(source, start_date, end_date)
    # Unsupported type
    return []


def main() -> int:
    try:
        sources = _load_sources()
    except Exception as e:
        print(f"[northwoods] Failed to load sources: {e}")
        return 1

    _ensure_dirs()
    start_date, end_date = _date_window()

    all_events: List[Dict[str, Any]] = []
    source_logs: List[Dict[str, Any]] = []

    for src in sources:
        sid = src["id"]
        sname = src.get("name") or sid
        print(f"[northwoods] Fetching: {sname} ({sid})")
        ok = True
        err = ""
        count = 0
        diag = {}
        try:
            events = _dispatch_fetch(src, start_date, end_date)
            # Attach IDs & names for ICS grouping
            for e in events:
                e.setdefault("source", sname)
                e.setdefault("calendar", sname)
            count = len(events)
            all_events.extend(events)
        except Exception as ex:
            ok = False
            err = f"{type(ex).__name__}: {ex}"
            traceback.print_exc()

        source_logs.append({
            "name": sname,
            "type": src.get("type"),
            "url": src.get("url"),
            "count": count,
            "ok": ok,
            "error": err,
            "diag": {"ok": ok, "error": err, "diag": diag},
            "id": sid,
        })

    # Write ICS outputs (support both old/new signatures in your local ics_writer)
    try:
        write_combined_ics(all_events, COMBINED_ICS_PATH)
    except TypeError:
        write_combined_ics(all_events)

    try:
        write_per_source_ics(all_events, BY_SOURCE_DIR)
    except TypeError:
        write_per_source_ics(all_events)

    # Always write a viewer-friendly report.json with normalized_events
    report = {
        "version": "2.0",
        "run_started_utc": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "success": True,
        "total_events": len(all_events),
        "sources_processed": len(sources),
        "source_logs": source_logs,
        "normalized_events": all_events[:1000],  # cap to keep file small
        "events_preview_count": min(len(all_events), 1000),
    }
    with open(REPORT_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    # Keep an index.html present (no-op if already committed)
    if not os.path.exists(INDEX_HTML_PATH):
        with open(INDEX_HTML_PATH, "w", encoding="utf-8") as f:
            f.write("<!doctype html><meta charset='utf-8'><title>Northwoods Events</title><p>Run completed.</p>")

    print(json.dumps({"ok": True, "events": len(all_events)}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
