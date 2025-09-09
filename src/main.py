# src/main.py
from __future__ import annotations

import json
import sys
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import yaml

# Required parsers (present in your repo)
from src.parsers import (
    fetch_tec_rest,
    fetch_growthzone_html,
    fetch_simpleview_html,
    fetch_tec_html,  # used only when type == "tec_html"
)

# Optional parsers: guard imports so the build never breaks if they’re absent
try:
    from src.parsers import fetch_ics_feed  # available in your repo
except Exception:
    fetch_ics_feed = None  # safe fallback

try:
    # NEW: WordPress archive/detail crawler for St. Germain
    from src.parsers import fetch_stgermain_wp
except Exception:
    fetch_stgermain_wp = None  # only used if you add a st-germain-wp source


# ---------------------- config ----------------------

DEFAULT_WINDOW_DAYS_FWD = int(os.getenv("NW_WINDOW_FWD_DAYS", "180"))
REPORT_JSON_PATH = os.getenv("NW_REPORT_JSON", "report.json")
SOURCES_YAML = os.getenv("NW_SOURCES_YAML", "config/sources.yaml")


def _window() -> (datetime, datetime):
    now = datetime.now(timezone.utc)
    return now - timedelta(days=1), now + timedelta(days=DEFAULT_WINDOW_DAYS_FWD)


def _normalize_event(raw: Dict[str, Any], src: Dict[str, Any]) -> Dict[str, Any]:
    """Lenient normalization for preview/report.json."""
    title = raw.get("title") or raw.get("name") or "(untitled)"
    start = raw.get("start_utc") or raw.get("start")
    end = raw.get("end_utc") or raw.get("end")
    out = {
        "calendar": src.get("name") or src.get("id") or "Unknown",
        "title": title,
        "start_utc": start,
        "end_utc": end,
        "location": raw.get("location"),
        "url": raw.get("url") or raw.get("link"),
        "source": raw.get("source") or src.get("name"),
    }
    # keep a small meta peek to help debug
    for k in ("jsonld", "meta", "_source"):
        if k in raw:
            out[k] = raw[k]
    return out


def _fetch_one(source: Dict[str, Any], start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
    """Route by type -> fetcher, with guarded calls and consistent kwargs."""
    stype = (source.get("type") or "").strip()
    url = source.get("url")
    name = source.get("name") or source.get("id") or stype

    # Parse router (safely include optional fetchers)
    router = {
        "tec_rest": fetch_tec_rest,
        "growthzone_html": fetch_growthzone_html,
        "tec_html": fetch_tec_html,
        "simpleview_html": fetch_simpleview_html,
    }
    if fetch_ics_feed is not None:
        router["ics_feed"] = fetch_ics_feed
    if fetch_stgermain_wp is not None:
        router["stgermain_wp"] = fetch_stgermain_wp  # NEW: WP archive/detail

    fn = router.get(stype)
    if fn is None:
        raise RuntimeError(f"Unsupported source type: {stype}")

    # Call with kwargs (all built-in fetchers accept these names)
    return fn(
        source=source,
        start_date=start_date,
        end_date=end_date,
    )


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
        name = src.get("name") or sid or stype or "Unknown"
        url = src.get("url") or ""

        print(f"[northwoods] Fetching: {name} ({sid}) [{stype}] -> {url}")

        per_source_events: List[Dict[str, Any]] = []
        err_msg: Optional[str] = None

        try:
            per_source_events = _fetch_one(src, start_date, end_date) or []
        except Exception as e:
            err_msg = str(e)
            print(f"[northwoods] ERROR while fetching {name}: {err_msg}")

        # Record log
        source_logs.append({
            "id": sid,
            "name": name,
            "type": stype,
            "url": url,
            "ok": err_msg is None,
            "count": len(per_source_events),
            "error": err_msg,
        })

        # Accumulate
        all_events.extend([
            {**ev, "source": ev.get("source") or name} for ev in per_source_events
        ])

    # 3) Normalize preview for report.json
    normalized_preview = [_normalize_event(e, {"name": "unknown"}) for e in all_events]

    # 4) Assemble report
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "sources_processed": len(source_logs),
        "total_events": len(all_events),
        "source_logs": source_logs,
        "normalized_events": normalized_preview[:500],  # keep report small
        "events_preview_count": min(500, len(normalized_preview)),
    }

    # 5) Write report.json
    try:
        with open(REPORT_JSON_PATH, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"[northwoods] ERROR writing report.json: {e}")

    # 6) Output summary for CI logs
    print(json.dumps({"ok": True, "events": len(all_events)}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
