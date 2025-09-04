#!/usr/bin/env python3
"""
northwoods-events-v2 main entrypoint

Revisions in this drop-in:
- Robust YAML normalization (list, {sources: [...]}, or {id: {...}}) retained.
- NEW: Autogenerate stable, unique 'id' for any source missing it:
    * Prefer slug(name); fallback to slug(hostname from url); finally slug(url).
    * Deduplicate with -2/-3 suffixes if needed.
    * Log each auto-generated id for traceability.
- Validation remains strict for required keys (id, name, type, url) AFTER backfilling.
- No file/dir names or paths changed; continues to prefer config/sources.yaml.
"""

from __future__ import annotations

import json
import os
import re
import sys
from datetime import date, timedelta
from typing import Any, Dict, List, Tuple
from urllib.parse import urlparse

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


def _slug(value: str) -> str:
    """
    Make a conservative, filesystem/URL-friendly slug:
    - Lowercase
    - Replace non-alphanumerics with hyphens
    - Compress repeated hyphens
    - Trim leading/trailing hyphens
    """
    v = value.strip().lower()
    v = re.sub(r"[^a-z0-9]+", "-", v)
    v = re.sub(r"-{2,}", "-", v).strip("-")
    return v or "source"


def _hostname_from_url(u: str) -> str:
    try:
        host = urlparse(u).hostname or ""
        return host.split(":")[0] if host else ""
    except Exception:
        return ""


def _autogen_id_for(source: Dict[str, Any]) -> str:
    """
    Generate a deterministic id for a source that lacks one.
    Priority for base string:
      1) name
      2) hostname from url
      3) full url
    Also include type as a suffix if present to reduce collisions.
    """
    name = (source.get("name") or "").strip()
    url = (source.get("url") or "").strip()
    typ = (source.get("type") or "").strip()

    base = name or _hostname_from_url(url) or url or "source"
    slug = _slug(base)
    if typ:
        slug = f"{slug}-{_slug(typ)}"
    return slug


def _normalize_sources(data: Any, path: str) -> List[Dict[str, Any]]:
    """
    Accept several YAML shapes and normalize to a list of {id,name,type,url,...}.
      - If data is a list: return as-is (we'll backfill ids and validate later).
      - If data is a dict:
          * If it contains 'sources' key and that value is a list -> return it.
          * Else treat it as { <id>: { ... }, ... }:
              - Convert each entry to a source dict, injecting 'id' if missing.
    """
    if isinstance(data, list):
        return data

    if isinstance(data, dict):
        # Case B: { sources: [...] }
        if "sources" in data:
            s = data["sources"]
            if not isinstance(s, list):
                raise ValueError(f"In {path}, 'sources' should be a list, got {type(s)}")
            return s

        # Case C: { <id>: { ... }, ... }
        normalized: List[Dict[str, Any]] = []
        for sid, cfg in data.items():
            if not isinstance(cfg, dict):
                raise ValueError(f"In {path}, source '{sid}' should be a mapping, got {type(cfg)}")
            item = dict(cfg)  # shallow copy
            item.setdefault("id", sid)
            normalized.append(item)
        return normalized

    raise ValueError(f"Unsupported YAML structure in {path}: {type(data)}")


def _backfill_and_validate_ids(sources: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Ensure every source has a stable, unique 'id'.
    - Autogenerate if missing (using name/hostname/url + type).
    - Deduplicate by appending -2/-3/... suffix.
    """
    seen: Dict[str, int] = {}
    for idx, s in enumerate(sources):
        sid = (s.get("id") or "").strip()
        if not sid:
            auto_id = _autogen_id_for(s)
            print(f"[northwoods] Source #{idx} missing 'id' -> auto-generated '{auto_id}'")
            sid = auto_id

        sid = _slug(sid)
        # Deduplicate if necessary
        base = sid
        n = seen.get(base, 0)
        if n:
            # already seen; find next available suffix
            k = n + 1
            while f"{base}-{k}" in seen:
                k += 1
            sid = f"{base}-{k}"
            seen[base] = k  # update base count
            print(f"[northwoods] Duplicate id '{base}' -> using '{sid}'")
        else:
            seen[base] = 1

        s["id"] = sid

    return sources


def _load_sources() -> List[Dict[str, Any]]:
    import yaml

    path = _find_sources_file()
    print(f"[northwoods] Loading sources from: {path}")

    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    sources = _normalize_sources(raw, path)
    sources = _backfill_and_validate_ids(sources)

    # minimal validation (AFTER id backfill)
    for idx, s in enumerate(sources):
        for key in ("id", "name", "type", "url"):
            if key not in s or not s[key]:
                raise ValueError(f"Source #{idx} missing required key: {key}")

    return sources


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
            "id": sid,
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
