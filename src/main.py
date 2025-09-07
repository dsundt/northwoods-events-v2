import json
import sys
import os
from datetime import datetime, timezone

import yaml

# Parsers: do not rename – these must match existing modules in your repo
from src.parsers import (
    fetch_tec_rest,
    fetch_growthzone_html,
    fetch_simpleview_html,
    # If you also support HTML TEC as a fallback:
    fetch_tec_html,  # safe to import; only used if type == "tec_html"
)

# ICS writer – different repos of v2 have slightly different call signatures.
# We'll call them defensively so we don't break either variant.
from src.ics_writer import write_combined_ics, write_per_source_ics


SOURCES_PATH = "config/sources.yaml"
PUBLIC_DIR = "public"
BY_SOURCE_DIR = os.path.join(PUBLIC_DIR, "by-source")
COMBINED_ICS_PATH = os.path.join(PUBLIC_DIR, "combined.ics")
REPORT_JSON_PATH = os.path.join(PUBLIC_DIR, "report.json")


def _slugify(text: str) -> str:
    """
    Minimal, dependency-free slugify to keep IDs/filenames stable
    without adding new packages.
    """
    text = (text or "").strip().lower()
    out = []
    prev_dash = False
    for ch in text:
        if ch.isalnum():
            out.append(ch)
            prev_dash = False
        else:
            if not prev_dash:
                out.append("-")
            prev_dash = True
    slug = "".join(out).strip("-")
    return slug or "source"


def _ensure_dirs():
    os.makedirs(PUBLIC_DIR, exist_ok=True)
    os.makedirs(BY_SOURCE_DIR, exist_ok=True)


def _load_sources() -> list:
    print(f"[northwoods] Loading sources from: {SOURCES_PATH}")
    with open(SOURCES_PATH, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not isinstance(data, list):
        raise ValueError(f"Expected a list of sources in {SOURCES_PATH}, got {type(data)}")

    cleaned = []
    for idx, src in enumerate(data):
        if not isinstance(src, dict):
            raise ValueError(f"Source #{idx} must be a mapping, got {type(src)}")

        name = src.get("name") or f"Source {idx+1}"
        typ = src.get("type")
        url = src.get("url")

        if not typ:
            raise ValueError(f"Source #{idx} ({name}) missing required key: type")
        if not url:
            raise ValueError(f"Source #{idx} ({name}) missing required key: url")

        # Keep user-provided ids; else generate stable, predictable one
        if "id" not in src or not src["id"]:
            gen_id = f"{_slugify(name)}-{_slugify(typ)}"
            print(f"[northwoods] Source #{idx} missing 'id' -> auto-generated '{gen_id}'")
            src["id"] = gen_id

        cleaned.append(
            {
                "name": name,
                "id": src["id"],
                "type": typ,
                "url": url.strip(),
                # Pass-through any optional fields without assuming schema changes
                **{k: v for k, v in src.items() if k not in {"name", "id", "type", "url"}},
            }
        )
    return cleaned


def _dispatch_fetch(src_type: str, url: str):
    """
    IMPORTANT: Always pass the URL string to fetchers.
    This prevents InvalidSchema when a dict accidentally reaches requests.get().
    """
    if src_type == "tec_rest":
        return fetch_tec_rest(url)
    if src_type == "growthzone_html":
        return fetch_growthzone_html(url)
    if src_type == "simpleview_html":
        return fetch_simpleview_html(url)
    if src_type == "tec_html":
        # Only used if you have Oneida on TEC HTML fallback.
        return fetch_tec_html(url)

    raise ValueError(f"Unsupported source type: {src_type}")


def _write_per_source_ics_safe(source_id: str, events: list):
    """
    Adapt to either signature:
      - write_per_source_ics(source_id, events)
      - write_per_source_ics(events, source_id)
    """
    try:
        return write_per_source_ics(source_id, events)
    except TypeError:
        return write_per_source_ics(events, source_id)


def _write_combined_ics_safe(all_events: list):
    """
    Adapt to either signature:
      - write_combined_ics(all_events)
      - write_combined_ics(all_events, COMBINED_ICS_PATH)
    """
    try:
        return write_combined_ics(all_events)
    except TypeError:
        return write_combined_ics(all_events, COMBINED_ICS_PATH)


def _normalize_for_report(ev: dict, source_name: str) -> dict:
    """
    Create a stable shape for the debug viewer. We do not change the parser’s output,
    we only map known keys if present. Missing keys stay None.
    """
    return {
        "uid": ev.get("uid"),
        "title": ev.get("title"),
        "start_utc": ev.get("start_utc"),
        "end_utc": ev.get("end_utc"),
        "url": ev.get("url"),
        "location": ev.get("location"),
        "source": source_name,
        "calendar": source_name,
    }


def main() -> int:
    _ensure_dirs()
    sources = _load_sources()

    run_started = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    source_logs = []
    all_events = []
    events_by_source = {}

    for src in sources:
        name = src["name"]
        sid = src["id"]
        typ = src["type"]
        url = src["url"]

        print(f"[northwoods] Fetching: {name} ({sid}) [{typ}] -> {url}")

        log = {
            "name": name,
            "type": typ,
            "url": url,
            "count": 0,
            "ok": False,
            "error": "",
            "diag": {"ok": False, "error": "", "diag": {}},
            "id": sid,
        }

        try:
            # *** CORE FIX: always pass 'url' string, not the entire source dict. ***
            events = _dispatch_fetch(typ, url) or []
            if not isinstance(events, list):
                raise TypeError(f"Fetcher for {name} returned non-list: {type(events)}")

            # Track, then write per-source ICS using a signature-safe wrapper
            log["count"] = len(events)
            log["ok"] = True
            log["diag"]["ok"] = True

            # Keep events grouped by source for front-end filtering
            events_by_source[sid] = events

            try:
                _write_per_source_ics_safe(sid, events)
            except Exception as ics_err:
                # Do not fail the run if single-source ICS write has issues
                log["diag"]["error"] = f"per-source-ics: {repr(ics_err)}"
                print(f"[northwoods] WARN per-source ICS ({sid}): {ics_err}")

            # Attach source metadata to the event record for combined output/report
            for ev in events:
                ev["_source_id"] = sid
                ev["_source_name"] = name

            all_events.extend(events)

        except Exception as e:
            log["error"] = repr(e)
            log["diag"]["error"] = repr(e)
            print(f"[northwoods] ERROR while fetching {name}: {e}")

        source_logs.append(log)

    # Combined ICS – signature-safe
    try:
        _write_combined_ics_safe(all_events)
    except Exception as e:
        print(f"[northwoods] ERROR writing combined ICS: {e}")

    # Build report.json with both keys some index.html variants expect
    normalized = [_normalize_for_report(ev, ev.get("_source_name") or "") for ev in all_events]

    report = {
        "version": "2.0",
        "run_started_utc": run_started,
        "success": True,
        "total_events": len(all_events),
        "sources_processed": len(sources),
        "source_logs": source_logs,
        # Keep both for compatibility with different frontends you tried:
        "events": normalized,
        "normalized_events": normalized,
        # Helpful previews used by a prior debug UI
        "events_preview": normalized[:100],
        "events_preview_count": min(100, len(normalized)),
    }

    try:
        with open(REPORT_JSON_PATH, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"[northwoods] ERROR writing report.json: {e}")

    print(json.dumps({"ok": True, "events": len(all_events)}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
