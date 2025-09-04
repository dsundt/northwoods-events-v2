from __future__ import annotations
import os, sys, json
from pathlib import Path
from datetime import datetime, timedelta, timezone
import yaml

from src.parsers import (
    fetch_tec_rest,
    fetch_tec_auto,
    fetch_growthzone_html,
    fetch_simpleview_html,
)
from src.ics_writer import write_per_source_ics, write_combined_ics
from src.report_writer import write_report
from src.index_writer import write_index

PARSER_MAP = {
    "tec_rest": fetch_tec_rest,
    "tec_auto": fetch_tec_auto,
    "growthzone_html": fetch_growthzone_html,
    "simpleview_html": fetch_simpleview_html,
}

def _daterange(days_ahead: int):
    start = datetime.now(timezone.utc).date()
    end = start + timedelta(days=days_ahead)
    return start.isoformat(), end.isoformat()

def main():
    project_root = Path(__file__).resolve().parents[1]
    sources_file = project_root / "sources.yaml"
    public_dir = project_root / "public"
    by_source_dir = public_dir / "by-source"

    with open(sources_file, "r", encoding="utf-8") as f:
        sources = yaml.safe_load(f)

    run_meta = {"run_started_utc": datetime.now(timezone.utc).isoformat()}
    per_source_logs = []
    all_events = []
    grouped = {}

    for src in sources:
        name = src["name"]; slug = src["slug"]; typ = src["type"]
        days = int(src.get("days_ahead", 120))
        start_iso, end_iso = _daterange(days)
        parser = PARSER_MAP.get(typ)
        ok = True; err = ""
        diag = {}
        if parser is None:
            ok = False
            err = f"Unknown parser type: {typ}"
            items = []
        else:
            try:
                items, diag = parser(src, start_iso, end_iso)
            except Exception as e:
                ok = False
                err = f"{type(e).__name__}: {e}"
                items = []

        # Build log
        per_source_logs.append({
            "name": name, "type": typ, "url": src["url"],
            "count": len(items), "ok": ok, "error": err, "diag": diag, "slug": slug
        })

        if not ok and not src.get("allow_zero", False):
            # If the parser failed completely, keep going, but we'll fail the build later.
            pass

        grouped[slug] = items
        all_events.extend(items)

    # Write ICS per-source and combined
    write_per_source_ics(by_source_dir, grouped)
    write_combined_ics(public_dir / "combined.ics", all_events)

    # Report & viewer
    # For viewer, include a 100-event preview
    preview = []
    for src in sources:
        for ev in grouped.get(src["slug"], []):
            if len(preview) >= 100: break
            preview.append(ev)
        if len(preview) >= 100: break

    write_report(public_dir / "report.json", run_meta, per_source_logs, preview)
    write_index(public_dir / "index.html")

    # Fail build if any source had 0 events and doesn't allow zero (regression guard)
    failures = [s for s in per_source_logs if (s["count"] == 0 and not next((x for x in sources if x["name"]==s["name"]), {}).get("allow_zero", False))]
    # Also fail if any source explicitly error'ed
    failed_errors = [s for s in per_source_logs if (not s["ok"] and not next((x for x in sources if x["name"]==s["name"]), {}).get("allow_zero", False))]
    if failures or failed_errors:
        print(json.dumps({"ok": False, "failures": failures, "errors": failed_errors}, indent=2))
        sys.exit(1)
    else:
        print(json.dumps({"ok": True, "events": len(all_events)}, indent=2))

if __name__ == "__main__":
    main()
