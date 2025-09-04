from __future__ import annotations
import os
import sys
import json
import datetime as dt
import yaml
from typing import List, Dict, Any
from src.parsers import fetch_tec_rest, fetch_growthzone_html, fetch_simpleview_html
from src.ics_writer import write_per_source_ics, write_combined_ics
from src.report_writer import write_report

# Minimal utilities
def _today() -> dt.date:
    return dt.date.today()

def _date_window() -> tuple[dt.date, dt.date]:
    start = _today()
    end = start + dt.timedelta(days=120)
    return start, end

def _load_sources(path: str = "sources.yaml") -> List[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}
    return cfg.get("sources", [])

def _route_fetch(src: Dict[str, Any], start: dt.date, end: dt.date) -> tuple[List[Dict], Dict[str, Any]]:
    stype = (src.get("type") or "").lower()
    url = src.get("url")
    name = src.get("name", url)
    if stype == "tec_rest":
        evs, diag = fetch_tec_rest(url, start, end)
    elif stype == "growthzone_html":
        evs, diag = fetch_growthzone_html(url, start, end)
    elif stype == "simpleview_html":
        evs, diag = fetch_simpleview_html(url, start, end)
    else:
        evs, diag = [], {"ok": False, "error": f"Unknown type '{stype}'", "diag": {}}

    # Stamp source label on returned events
    for e in evs:
        e["source"] = e["calendar"] = name

    # Normalize URL fields (ensure absolute if site-relative slipped through)
    for e in evs:
        if e.get("url") and e["url"].startswith("/"):
            e["url"] = url.rstrip("/") + e["url"]

    return evs, {"name": name, "type": stype, "url": url, "count": len(evs), **diag}

def main():
    start, end = _date_window()
    sources = _load_sources()
    all_events: List[Dict] = []
    source_logs: List[Dict[str, Any]] = []

    for src in sources:
        evs, log = _route_fetch(src, start, end)
        all_events.extend(evs)
        source_logs.append(log)

    # Outputs
    ok = True
    write_per_source_ics(all_events)
    write_combined_ics(all_events)
    write_report(ok, all_events, source_logs)

    # Lightweight console summary (helps GH logs)
    print(json.dumps({"ok": ok, "events": len(all_events)}, indent=2))

if __name__ == "__main__":
    sys.exit(main())
