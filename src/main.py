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
    parse_simpleview_html,  # NEW
)
from src.public_fallback import ensure_index

ROOT_DIR = os.path.dirname(os.path.dirname(__file__))
PUBLIC_DIR = os.path.join(ROOT_DIR, "public")
CONFIG_PATH = os.path.join(ROOT_DIR, "config", "sources.yaml")


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


def process_sources(cfg: Dict[str, Any]) -> (List[Event], Dict[str, List[Event]], List[Dict[str, Any]]):
    all_events: List[Event] = []
    by_source: Dict[str, List[Event]] = {}
    logs: List[Dict[str, Any]] = []

    for src in cfg.get("sources", []):
        name = src["name"]
        url = src["url"]
        typ = src["type"]
        calendar = src.get("calendar", "General")

        entry_log = {"name": name, "type": typ, "url": url, "count": 0, "ok": False, "error": ""}
        try:
            resp = get(url)
            content = resp.content

            if typ == "ics":
                events = parse_ics_feed(content, name, calendar)
            elif typ == "tec_html":
                events = parse_tec_html(content, name, calendar, base_url=url)
            elif typ == "growthzone_html":
                events = parse_growthzone_html(content, name, calendar, base_url=url)
            elif typ == "ai1ec_html":
                events = parse_ai1ec_html(content, name, calendar, base_url=url)
            elif typ == "simpleview_html":  # NEW
                events = parse_simpleview_html(content, name, calendar, base_url=url)
            else:
                raise ValueError(f"Unsupported source type: {typ}")

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

    final_events = []
    seen_global = set()
    for e in all_events:
        if e.uid in seen_global:
            continue
        seen_global.add(e.uid)
        final_events.append(e)

    final_events.sort(key=lambda e: e.start_utc)
    return final_events, by_source, logs


def main() -> int:
    run_started = datetime.now(timezone.utc)
    cfg = load_config(CONFIG_PATH)

    try:
        events, by_source, logs = process_sources(cfg)
        ensure_index(PUBLIC_DIR)
        write_outputs(PUBLIC_DIR, events, by_source)

        report = {
            "version": "2.0",
            "run_started_utc": run_started.isoformat(),
            "success": True,
            "total_events": len(events),
            "sources_processed": len(cfg.get("sources", [])),
            "source_logs": logs,
        }
        write_report(PUBLIC_DIR, report)

        print(json.dumps({"ok": True, "events": len(events)}, indent=2))
        return 0

    except Exception as exc:
        try:
            ensure_index(PUBLIC_DIR)
        except Exception:
            pass
        err_report = {
            "version": "2.0",
            "run_started_utc": run_started.isoformat(),
            "success": False,
            "error": f"{exc.__class__.__name__}: {exc}",
            "trace": traceback.format_exc(),
        }
        os.makedirs(PUBLIC_DIR, exist_ok=True)
        write_report(PUBLIC_DIR, err_report)
        print(json.dumps({"ok": False, "error": str(exc)}, indent=2))
        return 1


if __name__ == "__main__":
    sys.exit(main())
