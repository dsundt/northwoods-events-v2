#!/usr/bin/env python3
"""
northwoods-events-v2 main entrypoint

Fix in this revision:
- _find_sources_file() now searches for config/sources.yaml first (the location you already use).
- Still supports SOURCES_FILE env override, then falls back to ./sources.yaml and ./src/sources.yaml.
- Prints which path was loaded for traceability.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import date, timedelta
from typing import Any, Dict, List, Tuple

from src.parsers import fetch_tec_rest, fetch_growthzone_html, fetch_simpleview_html
from src.ics_writer import write_per_source_ics, write_combined_ics


PUBLIC_DIR = "public"
BY_SOURCE_DIR = os.path.join(PUBLIC_DIR, "by-source")
COMBINED_ICS_PATH = os.path.join(PUBLIC_DIR, "combined.ics")
REPORT_JSON_PATH = os.path.join(PUBLIC_DIR, "report.json")


def _find_sources_file() -> str:
    """
    Return a readable path to the sources.yaml file.

    Priority:
      1) Environment variable SOURCES_FILE (absolute or relative)
      2) config/sources.yaml
      3) sources.yaml (repo root)
      4) src/sources.yaml
    """
    candidates: List[str] = []

    env_override = os.environ.get("SOURCES_FILE", "").strip()
    if env_override:
        candidates.append(env_override)

    candidates.extend([
        os.path.join("config", "sources.yaml"),
        "sources.yaml",
        os.path.join("src", "sources.yaml"),
    ])

    for p in candidates:
        if os.path.isfile(p):
            return p

    raise FileNotFoundError(
        "Could not locate sources.yaml. Tried (in order): "
        + ", ".join(candidates)
        + ". Set SOURCES_FILE to override."
    )


def _load_sources() -> List[Dict[str, Any]]:
    import yaml

    path = _find_sources_file()
    print(f"[northwoods] Loading sources from: {path}")

    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or []

    if not isinstance(data, list):
        raise ValueError(f"Expected a list of sources in {path}, got {type(data)}")

    for idx, s in enumerate(data):
        for key in ("id", "name", "type", "url"):
            if key not in s or not s[key]:
                raise ValueError(f"Source #{idx} missing required key: {key}")

    return data


def _date_window() -> Tuple[date, date]:
    start_days = int(os.environ.get("START_DAYS", "0"))
    end_days = int(os.environ.get("END_DAYS", "120"))
    start = date.today() + timedelta(days=start_days)
    end = date.today() + timedelta(days=end_days)
    return start, end


def _ensure_dirs() -> None:
    os.makedirs(BY_SOURCE_DIR, exist_ok=True)


def _fetch_for_source(source: Dict[str, Any], start: date, end: date) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    stype = source["type"]
    url = source["url"]

    if stype == "tec_rest":
        events, diag = fetch_tec_rest(url, start, end)
    elif stype == "growthzone_html":
        events, diag = fetch_growthzone_html(url, start, end)
    elif stype == "simpleview_html":
        events, diag = fetch_simpleview_html(url, start, end)
    else:
        raise ValueError(f"Unknown source type: {stype}")

    for e in events:
        e.setdefault("source", source["name"])
        e.setdefault("calendar", source["name"])

    return events, diag or {}


def main() -> int:
    _ensure_dirs()
    sources = _load_sources()
    start, end = _date_window()

    all_events: List[Dict[str, Any]] = []
    source_logs: List[Dict[str, Any]] = []

    for src_cfg in sources:
        sid = src_cfg["id"]
        sname = src_cfg["name"]
        print(f"[northwoods] Fetching: {sname} ({sid})")

        ok = True
        err = ""
        diag: Dict[str, Any] = {}
        events: List[Dict[str, Any]] = []

        try:
            events, diag = _fetch_for_source(src_cfg, start, end)
        except Exception as ex:
            ok = False
            err = f"{type(ex).__name__}: {ex}"
            events = []

        try:
            write_per_source_ics(events, os.path.join(BY_SOURCE_DIR, f"{sid}.ics"))
        except Exception as ex:
            ok = False
            err = (err + " | " if err else "") + f"ICSWriteError: {ex}"

        all_events.extend(events)

        source_logs.append({
            "name": sname,
            "type": src_cfg["type"],
            "url": src_cfg["url"],
            "count": len(events),
            "ok": ok,
            "error": err,
            "diag": diag,
        })

    write_combined_ics(all_events, COMBINED_ICS_PATH)

    preview = all_events[:100]
    report = {
        "version": "2.0",
        "run_started_utc": os.environ.get("GITHUB_RUN_STARTED_AT", ""),
        "success": True,
        "total_events": len(all_events),
        "sources_processed": len(sources),
        "source_logs": source_logs,
        "events_preview": preview,
        "events_preview_count": len(preview),
    }
    with open(REPORT_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(json.dumps({"ok": True, "events": len(all_events)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
