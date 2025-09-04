# src/main.py
from __future__ import annotations

import sys
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Tuple

import yaml

from src.parsers import (
    fetch_tec_rest,
    fetch_tec_html,
    fetch_growthzone_html,
    fetch_simpleview_html,
)
from src.ics_writer import write_combined_ics, write_per_source_ics
from src.report import write_report

CONFIG_PATH = "config/sources.yaml"
PUBLIC_DIR = Path("public")
BY_SOURCE_DIR = PUBLIC_DIR / "by-source"
COMBINED_ICS_PATH = PUBLIC_DIR / "combined.ics"
REPORT_JSON_PATH = PUBLIC_DIR / "report.json"
INDEX_HTML_PATH = PUBLIC_DIR / "index.html"

# How far ahead to fetch events
WINDOW_DAYS = 120


def _slug(s: str) -> str:
    """
    Minimal slugify to avoid external dependencies.
    - lowercases
    - keeps alphanumerics
    - turns everything else into single '-'
    - trims leading/trailing '-'
    """
    out = []
    prev_dash = False
    for ch in s.lower():
        if ch.isalnum():
            out.append(ch)
            prev_dash = False
        else:
            if not prev_dash:
                out.append("-")
                prev_dash = True
    slug = "".join(out).strip("-")
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug


def _load_sources() -> List[Dict]:
    print("[northwoods] Loading sources from:", CONFIG_PATH)
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    # Accept either a list or {sources: [...]}
    if isinstance(data, dict) and "sources" in data:
        data = data["sources"]

    if not isinstance(data, list):
        raise ValueError(f"Expected a list or {{sources: [...]}} in {CONFIG_PATH}")

    # Ensure each source has an id
    for i, s in enumerate(data):
        if "id" not in s or not s["id"]:
            gen = f"{_slug(s.get('name', 'src'))}-{_slug(s.get('type', ''))}"
            s["id"] = gen
            print(f"[northwoods] Source #{i} missing 'id' -> auto-generated '{gen}'")
    return data


def _tec_with_fallback(src: Dict, start: datetime, end: datetime) -> Tuple[List[Dict], Dict]:
    """
    Try TEC REST; on 403/404 or empty, fall back to TEC HTML.
    Other exceptions bubble to caller and will be logged per-source.
    """
    try:
        events, diag = fetch_tec_rest(src, start, end)
        if events:
            return events, diag
    except Exception as e:
        # Only fall back silently on typical REST unavailability
        err = str(e)
        if "403" not in err and "404" not in err:
            # Bubble up (caller will wrap and log)
            raise

    # Fallback to HTML list view
    events_html, diag_html = fetch_tec_html(src, start, end)
    return events_html, diag_html


def main() -> int:
    sources = _load_sources()
    now = datetime.utcnow()
    start = now
    end = now + timedelta(days=WINDOW_DAYS)

    all_events: List[Dict] = []
    events_by_source: Dict[str, List[Dict]] = []
    events_by_source = {}
    source_logs: List[Dict] = []

    for src in sources:
        name = src["name"]
        typ = src["type"]
        url = src["url"]
        sid = src["id"]
        print(f"[northwoods] Fetching: {name} ({sid})")

        try:
            if typ in ("tec_rest", "tec"):
                events, diag = _tec_with_fallback(src, start, end)
            elif typ == "tec_html":
                events, diag = fetch_tec_html(src, start, end)
            elif typ == "growthzone_html":
                events, diag = fetch_growthzone_html(src, start, end)
            elif typ == "simpleview_html":
                events, diag = fetch_simpleview_html(src, start, end)
            else:
                events, diag = [], {"ok": False, "error": f"Unknown type: {typ}", "diag": {}}
        except Exception as e:
            events, diag = [], {"ok": False, "error": repr(e), "diag": {}}

        # Normalize tagging
        for e in events:
            e["source"] = name
            e["calendar"] = name

        count = len(events)
        all_events.extend(events)
        events_by_source[_slug(name)] = events

        source_logs.append({
            "name": name,
            "type": typ,
            "url": url,
            "count": count,
            "ok": bool(events),
            "error": "" if events else (diag.get("error") if isinstance(diag, dict) else ""),
            "diag": diag,
            "id": sid,
        })

    # Write outputs
    write_per_source_ics(events_by_source, str(BY_SOURCE_DIR))
    write_combined_ics(all_events, str(COMBINED_ICS_PATH))
    write_report(str(REPORT_JSON_PATH), source_logs, all_events)

    # Console summary for CI logs
    print(json.dumps({"ok": True, "events": len(all_events)}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
