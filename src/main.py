import os
import sys
import json
import traceback
from datetime import datetime, timezone
from typing import List, Dict, Any

import yaml

from src.models import Event
from src.fetch import get
from src.ics_writer import write_outputs, write_report
from src.parsers import (
    parse_ics_feed,
    parse_tec_html,
    parse_growthzone_html,
    parse_ai1ec_html,
)
# optional: include other parsers you’ve added, e.g. simpleview
try:
    from src.parsers.simpleview_parser import parse_simpleview_html  # noqa: F401
    HAS_SIMPLEVIEW = True
except Exception:
    HAS_SIMPLEVIEW = False

# Resolve repo root relative to this file
ROOT_DIR = os.path.dirname(os.path.dirname(__file__))
PUBLIC_DIR = os.path.join(ROOT_DIR, "public")
CONFIG_PATH = os.path.join(ROOT_DIR, "config", "sources.yaml")

# Controls how many events get embedded in report.json for quick browser inspection.
REPORT_EVENTS_LIMIT = int(os.environ.get("REPORT_EVENTS_LIMIT", "50"))


def load_config(path: str) -> Dict[str, Any]:
    if not os.path.exists(path):
        return {"sources": []}
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if "sources" not in data or not isinstance(data["sources"], list):
        data["sources"] = []
    cleaned = []
    for s in data["sources"]:
        if not isinstance(s, dict):
            continue
        if not s.get("enabled", False):
            continue
        if not s.get("url") or not s.get("type"):
            continue
        s.setdefault("name", s.get("url"))
        s.setdefault("calendar", "General")
        cleaned.append(s)
    return {"sources": cleaned}


def parse_dispatch(typ: str, content: bytes, name: str, calendar: str, url: str) -> List[Event]:
    if typ == "ics":
        return parse_ics_feed(content, name, calendar)
    if typ == "tec_html":
        return parse_tec_html(content, name, calendar, base_url=url)
    if typ == "growthzone_html":
        return parse_growthzone_html(content, name, calendar, base_url=url)
    if typ == "ai1ec_html":
        return parse_ai1ec_html(content, name, calendar, base_url=url)
    if typ == "simpleview_html" and HAS_SIMPLEVIEW:
        from src.parsers.simpleview_parser import parse_simpleview_html  # local import
        return parse_simpleview_html(content, name, calendar, base_url=url)
    raise ValueError(f"Unsupported source type: {typ}")


def process_sources(cfg: Dict[str, Any]) -> (List[Event], Dict[str, List[Event]], List[Dict[str, Any]], List[str]):
    """
    Returns:
      final_events: deduped, sorted
      by_source: dict[name] -> events
      logs: per-source logs
      all_source_names: every enabled source name (for empty ICS creation)
    """
    all_events: List[Event] = []
    by_source: Dict[str, List[Event]] = {}
    logs: List[Dict[str, Any]] = []
    all_source_names: List[str] = []

    for src in cfg.get("sources", []):
        name = src["name"]
        url = src["url"]
        typ = src["type"]
        calendar = src.get("calendar", "General")
        all_source_names.append(name)

        entry_log = {"name": name, "type": typ, "url": url, "count": 0, "ok": False, "error": ""}

        try:
            resp = get(url)
            content = resp.content

            events = parse_dispatch(typ, content, name, calendar, url)

            # Deduplicate within this source
            seen = set()
            unique = []
            for e in events:
                if e.uid not in seen:
                    unique.append(e)
                    seen.add(e.uid)
            events = unique

            entry_log["count"] = len(events)
            entry_log["ok"] = True

            by_source.setdefault(name, []).extend(events)
            all_events.extend(events)

        except Exception as exc:
            entry_log["ok"] = False
            entry_log["error"] = f"{exc.__class__.__name__}: {exc}"
            entry_log["trace"] = traceback.format_exc()

        logs.append(entry_log)

    # Global dedupe and sort
    final_events = []
    seen_global = set()
    for e in all_events:
        if e.uid in seen_global:
            continue
        seen_global.add(e.uid)
        final_events.append(e)
    final_events.sort(key=lambda e: e.start_utc)

    return final_events, by_source, logs, all_source_names


def _event_to_preview(e: Event) -> Dict[str, Any]:
    # Keep this tiny; it’s for visual verification in the browser.
    return {
        "uid": e.uid,
        "title": e.title,
        "start_utc": e.start_utc.isoformat(),
        "end_utc": e.end_utc.isoformat() if e.end_utc else None,
        "source": e.source_name,
        "calendar": e.calendar,
        "url": e.url,
        "location": e.location,
    }


def main() -> int:
    run_started = datetime.now(timezone.utc)
    os.makedirs(PUBLIC_DIR, exist_ok=True)  # Ensure output path exists early
    cfg = load_config(CONFIG_PATH)

    try:
        events, by_source, logs, all_source_names = process_sources(cfg)

        # Build a small event preview into the report for browser verification
        preview = [_event_to_preview(e) for e in events[:REPORT_EVENTS_LIMIT]]

        # Write outputs (and ensure empty per-source files also exist)
        write_outputs(PUBLIC_DIR, events, by_source, all_source_names)

        report = {
            "version": "2.0",
            "run_started_utc": run_started.isoformat(),
            "success": True,
            "total_events": len(events),
            "sources_processed": len(cfg.get("sources", [])),
            "source_logs": logs,
            "events_preview": preview,
            "events_preview_count": len(preview),
        }
        write_report(PUBLIC_DIR, report)

        print(json.dumps({"ok": True, "events": len(events)}, indent=2))
        return 0

    except Exception as exc:
        # Always attempt to write a failure report
        err_report = {
            "version": "2.0",
            "run_started_utc": run_started.isoformat(),
            "success": False,
            "error": f"{exc.__class__.__name__}: {exc}",
            "trace": traceback.format_exc(),
        }
        try:
            write_report(PUBLIC_DIR, err_report)
        finally:
            print(json.dumps({"ok": False, "error": str(exc)}, indent=2))
        return 1


if __name__ == "__main__":
    sys.exit(main())
