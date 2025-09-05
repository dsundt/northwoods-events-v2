# src/main.py
# - Loads config/sources.yaml
# - Calls fetchers with aligned signatures
# - Writes public/by-source/*.ics, public/combined.ics, public/report.json
# - Tolerates ics_writer two different signatures (repo variants)

import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

import yaml

from src.parsers import (
    fetch_tec_rest,
    fetch_tec_html,
    fetch_growthzone_html,
    fetch_simpleview_html,
)

# Writer signatures vary across revisions; we tolerate both
from src import ics_writer

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config" / "sources.yaml"
PUBLIC_DIR = ROOT / "public"
BY_SOURCE_DIR = PUBLIC_DIR / "by-source"
COMBINED_ICS_PATH = PUBLIC_DIR / "combined.ics"
INDEX_HTML_PATH = PUBLIC_DIR / "index.html"
REPORT_JSON_PATH = PUBLIC_DIR / "report.json"

def _slugify(s: str) -> str:
    s = (s or "").strip().lower()
    out = []
    for ch in s:
        if ch.isalnum():
            out.append(ch)
        elif ch in " -_/":
            out.append("-")
    slug = "".join(out)
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug.strip("-") or "calendar"

def _load_sources():
    print(f"[northwoods] Loading sources from: {CONFIG_PATH}")
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"{CONFIG_PATH} not found")
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if isinstance(data, dict) and "sources" in data:
        sources = data["sources"]
    elif isinstance(data, list):
        sources = data
    else:
        raise ValueError(f"Expected a list or {{sources:[]}} in {CONFIG_PATH}, got {type(data)}")

    # Ensure minimal keys and IDs
    for i, s in enumerate(sources):
        if "id" not in s or not s["id"]:
            gen = f"{_slugify(s.get('name') or s.get('url') or 'source')}-{_slugify(s.get('type'))}"
            print(f"[northwoods] Source #{i} missing 'id' -> auto-generated '{gen}'")
            s["id"] = gen
        if "name" not in s:
            s["name"] = s["id"]
        if "enabled" not in s:
            s["enabled"] = True
    return sources

def _write_json_report(report: dict):
    PUBLIC_DIR.mkdir(parents=True, exist_ok=True)
    with open(REPORT_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

def _write_index_if_missing():
    if not INDEX_HTML_PATH.exists():
        # leave creation to repo; do not auto-synthesize
        return

def _call_writer_combined(events):
    # Try (events, path) first; fall back to (events)
    try:
        ics_writer.write_combined_ics(events, str(COMBINED_ICS_PATH))
    except TypeError:
        ics_writer.write_combined_ics(events)

def _call_writer_per_source(by_source):
    BY_SOURCE_DIR.mkdir(parents=True, exist_ok=True)
    try:
        ics_writer.write_per_source_ics(by_source, str(BY_SOURCE_DIR))
    except TypeError:
        ics_writer.write_per_source_ics(by_source)

def main():
    start = datetime.utcnow()
    sources = _load_sources()
    # Date window: today -> +120 days (consistent with prior runs)
    start_date = datetime.utcnow().date()
    end_date = start_date + timedelta(days=120)

    all_events = []
    by_source = {}
    source_logs = []

    fetchers = {
        "tec_rest": fetch_tec_rest,
        "tec_html": fetch_tec_html,            # includes Eventastic mode
        "growthzone_html": fetch_growthzone_html,
        "simpleview_html": fetch_simpleview_html,
    }

    for s in sources:
        if not s.get("enabled", True):
            source_logs.append({
                "name": s["name"], "type": s["type"], "url": s.get("url"),
                "count": 0, "ok": True, "error": "", "diag": {"skipped": "disabled"}, "id": s["id"]
            })
            continue

        print(f"[northwoods] Fetching: {s['name']} ({s['id']})")
        f = fetchers.get(s["type"])
        if not f:
            source_logs.append({
                "name": s["name"], "type": s["type"], "url": s.get("url"),
                "count": 0, "ok": False, "error": f"unknown type: {s['type']}", "diag": {}, "id": s["id"]
            })
            continue

        ok = True
        err = ""
        diag = {}
        events = []
        try:
            events, fetch_diag = f(s, start_date=start_date, end_date=end_date, session=None)
            diag = fetch_diag or {}
        except Exception as e:
            ok = False
            err = f"{type(e).__name__}('{e}')"

        # Normalize minimal required fields; fill calendar/source
        norm = []
        for e in (events or []):
            e = dict(e)
            e["calendar"] = e.get("calendar") or s["name"]
            e["source"] = e.get("source") or s["name"]
            # UID fallback
            if not e.get("uid"):
                base = e.get("url") or f"{s['id']}:{e.get('title','')}"
                e["uid"] = f"{_slugify(base)}@northwoods-v2"
            # Ensure start_utc present
            if not e.get("start_utc"):
                e["start_utc"] = None
            norm.append(e)

        all_events.extend(norm)
        by_source[s["id"]] = norm
        source_logs.append({
            "name": s["name"],
            "type": s["type"],
            "url": s.get("url"),
            "count": len(norm),
            "ok": ok,
            "error": err,
            "diag": diag,
            "id": s["id"],
        })

    # Write ICS artifacts
    _call_writer_combined(all_events)
    _call_writer_per_source(by_source)

    # Report
    report = {
        "version": "2.0",
        "run_started_utc": start.replace(microsecond=0).isoformat() + "Z",
        "success": True,
        "total_events": len(all_events),
        "sources_processed": sum(1 for s in sources if s.get("enabled", True)),
        "source_logs": source_logs,
        "events": all_events[:100],  # preview slice for viewer
        "events_preview_count": min(100, len(all_events)),
    }
    _write_json_report(report)
    _write_index_if_missing()
    print(json.dumps({"ok": True, "events": len(all_events)}))
    return 0

if __name__ == "__main__":
    sys.exit(main())
