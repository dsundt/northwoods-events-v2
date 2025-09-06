# src/main.py
from __future__ import annotations

import json
import os
import sys
import traceback
from datetime import datetime, timedelta
from typing import Any, Dict, List, Tuple
import inspect
import yaml

# Parsers: rely on your existing src/parsers package
from src.parsers import (
    fetch_tec_rest,
    fetch_tec_html,
    fetch_growthzone_html,
    fetch_simpleview_html,
)

# ICS writer: support both existing signatures (with/without explicit paths)
from src import ics_writer as icsw


# -------------------------
# Configuration & constants
# -------------------------

CONFIG_PATH = "config/sources.yaml"
OUTPUT_DIR = "public"
BY_SOURCE_DIR = os.path.join(OUTPUT_DIR, "by-source")
COMBINED_ICS_PATH = os.path.join(OUTPUT_DIR, "combined.ics")
REPORT_PATH = os.path.join(OUTPUT_DIR, "report.json")

# Default window (align with v1 behavior)
DEFAULT_DAYS_FWD = 120


# -------------------------
# Small local utilities
# -------------------------

def _slugify(text: str) -> str:
    """Tiny slugifier (no external deps)."""
    allowed = "abcdefghijklmnopqrstuvwxyz0123456789-"
    s = "".join(ch.lower() if ch.isalnum() else "-" for ch in (text or ""))
    while "--" in s:
        s = s.replace("--", "-")
    s = s.strip("-")
    return "".join(ch for ch in s if ch in allowed) or "source"

def _now_iso() -> str:
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

def _date_str(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d")


# -------------------------
# Loading sources.yaml
# -------------------------

def _load_sources(path: str = CONFIG_PATH) -> List[Dict[str, Any]]:
    print(f"[northwoods] Loading sources from: {path}")
    if not os.path.exists(path):
        raise FileNotFoundError(f"{path} not found")

    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if isinstance(data, dict) and "sources" in data and isinstance(data["sources"], list):
        sources = data["sources"]
    elif isinstance(data, list):
        sources = data
    else:
        raise ValueError(f"Expected a list or a dict with 'sources' in {path}, got {type(data)}")

    # Normalize & backfill ids
    norm: List[Dict[str, Any]] = []
    for idx, s in enumerate(sources):
        if not isinstance(s, dict):
            raise ValueError(f"Source #{idx} must be a mapping, got {type(s)}")

        for key in ("name", "type", "url"):
            if key not in s or not s[key]:
                raise ValueError(f"Source #{idx} missing required key: {key}")

        if "id" not in s or not s["id"]:
            nid = f"{_slugify(s['name'])}-{_slugify(s['type'])}"
            print(f"[northwoods] Source #{idx} missing 'id' -> auto-generated '{nid}'")
            s = {**s, "id": nid}

        norm.append(s)

    return norm


# -------------------------
# Parser dispatch helpers
# -------------------------

_PARSER_MAP = {
    "tec_rest": fetch_tec_rest,
    "tec_html": fetch_tec_html,
    "growthzone_html": fetch_growthzone_html,
    "simpleview_html": fetch_simpleview_html,
}

def _call_parser(fn, source: Dict[str, Any], start_date: str, end_date: str) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Call parser in a way that supports both signatures:
      (source)  or  (source, start_date, end_date)  or  (source, start_date=None, end_date=None)
    Prefer keyword args so older signatures don't break; fall back to positional 1-arg.
    """
    try:
        # Try with keywords first (most modern, non-breaking)
        return fn(source, start_date=start_date, end_date=end_date)
    except TypeError:
        # Fall back to simple signature
        return fn(source)
    # Other exceptions propagate to caller


# -------------------------
# ICS writing wrapper (compat)
# -------------------------

def _write_combined(events: List[Dict[str, Any]], path: str = COMBINED_ICS_PATH) -> None:
    """
    Support both:
      write_combined_ics(events)                 # writes its own default path
      write_combined_ics(events, path)           # explicit path
    """
    try:
        sig = inspect.signature(icsw.write_combined_ics)
        if len(sig.parameters) >= 2:
            icsw.write_combined_ics(events, path)  # type: ignore[arg-type]
        else:
            icsw.write_combined_ics(events)        # type: ignore[call-arg]
    except Exception as e:
        print("[northwoods] WARN: write_combined_ics failed:", e)
        traceback.print_exc()

def _write_per_source(events_by_source: Dict[str, List[Dict[str, Any]]], out_dir: str = BY_SOURCE_DIR) -> None:
    """
    Support both:
      write_per_source_ics(events_by_source)                 # uses default dir
      write_per_source_ics(events_by_source, out_dir)        # explicit dir
    """
    try:
        if hasattr(icsw, "write_per_source_ics"):
            sig = inspect.signature(icsw.write_per_source_ics)
            if len(sig.parameters) >= 2:
                icsw.write_per_source_ics(events_by_source, out_dir)  # type: ignore[arg-type]
            else:
                icsw.write_per_source_ics(events_by_source)           # type: ignore[call-arg]
        else:
            # Older build path variants: some repos expose similar function on a different name
            if hasattr(icsw, "write_by_source"):
                icsw.write_by_source(events_by_source, out_dir)       # type: ignore[attr-defined]
    except Exception as e:
        print("[northwoods] WARN: write_per_source_ics failed:", e)
        traceback.print_exc()


# -------------------------
# Normalization
# -------------------------

def _normalize_event(ev: Dict[str, Any], src: Dict[str, Any]) -> Dict[str, Any]:
    """Ensure keys the viewer expects are present."""
    out = dict(ev)
    cal_name = src.get("name") or src.get("id")
    out.setdefault("calendar", cal_name)
    out.setdefault("source", cal_name)

    # Normalize time keys (keep original if present; viewer is tolerant but we ensure a common one)
    if "start_utc" not in out and "start" in out and isinstance(out["start"], str):
        out["start_utc"] = out["start"]
    if "end_utc" not in out and "end" in out and isinstance(out["end"], str):
        out["end_utc"] = out["end"]

    return out


# -------------------------
# Main
# -------------------------

def main() -> int:
    start_utc = _now_iso()

    try:
        sources = _load_sources()
    except Exception as e:
        print(f"[northwoods] ERROR loading sources: {e}")
        traceback.print_exc()
        return 1

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(BY_SOURCE_DIR, exist_ok=True)

    start_date = _date_str(datetime.utcnow())
    end_date = _date_str(datetime.utcnow() + timedelta(days=DEFAULT_DAYS_FWD))

    all_events: List[Dict[str, Any]] = []
    per_source: Dict[str, List[Dict[str, Any]]] = {}
    source_logs: List[Dict[str, Any]] = []

    for src in sources:
        sid = src["id"]
        sname = src["name"]
        stype = src["type"]
        url = src["url"]

        print(f"[northwoods] Fetching: {sname} ({stype}) ({sid})")

        fn = _PARSER_MAP.get(stype)
        if not fn:
            msg = f"Unknown type '{stype}'"
            source_logs.append({
                "name": sname, "type": stype, "url": url, "count": 0,
                "ok": False, "error": msg, "diag": {"error": msg}, "id": sid,
            })
            continue

        events: List[Dict[str, Any]] = []
        diag: Dict[str, Any] = {}
        ok = True
        err_text = ""

        try:
            events_raw, diag = _call_parser(fn, src, start_date, end_date)
            # Normalize
            events = [_normalize_event(e, src) for e in (events_raw or [])]
        except Exception as e:
            ok = False
            err_text = f"{type(e).__name__}('{e}')"
            diag = {"ok": False, "error": err_text}
            traceback.print_exc()

        count = len(events)
        per_source[sid] = events
        all_events.extend(events)

        source_logs.append({
            "name": sname,
            "type": stype,
            "url": url,
            "count": count,
            "ok": ok and count >= 0,  # keep 'ok' true even if zero so UI shows source; detailed error still present
            "error": "" if ok else err_text,
            "diag": diag if isinstance(diag, dict) else {"diag": diag},
            "id": sid,
        })

    # Write ICS artifacts
    try:
        _write_per_source(per_source, BY_SOURCE_DIR)
    except Exception:
        pass

    try:
        _write_combined(all_events, COMBINED_ICS_PATH)
    except Exception:
        pass

    # ---- ADDITIVE TWEAK: ALWAYS include a full 'events' array in report.json ----
    report = {
        "version": "2.0",
        "run_started_utc": start_utc,
        "success": True,
        "total_events": len(all_events),
        "sources_processed": len(sources),
        "source_logs": source_logs,
        # Always include full events list:
        "events": all_events,
        # Keep preview (first 100) for quick inspection tools:
        "events_preview": all_events[:100],
    }

    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    # small console summary (kept from earlier builds)
    print(json.dumps({"ok": True, "events": len(all_events)}))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
