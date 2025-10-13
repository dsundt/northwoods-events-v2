# src/main.py
from __future__ import annotations

import json
import os
import shutil
import sys
from datetime import date, datetime, time, timedelta, timezone
from dateutil import parser as dtparse
from importlib import import_module
from typing import Any, Dict, List, Optional

import yaml

# shared helpers
from src.ics_writer import write_combined_ics, write_per_source_ics
from src.util import slugify, json_default, expand_tec_ics_urls

# ---- Parsers in this repo (unchanged) ----
from src.parsers import (
    fetch_tec_rest,          # POSitional: (url: str, start_utc: str|None, end_utc: str|None)
    fetch_growthzone_html,   # kwargs:     (source: dict, [session], [start_date], [end_date])
    fetch_simpleview_html,   # POSitional: (url: str, timeout=20, max_items=200)
    fetch_tec_html,          # kwargs:     (source: dict, [session], [start_date], [end_date])
    fetch_tec_rss,           # kwargs:     (source: dict, [start_date], [end_date])
)

# Optional: ICS (POSitional fetch_ics(url, start_utc, end_utc))
try:
    from src.parsers.ics_feed import fetch_ics as _fetch_ics_raw  # type: ignore
except Exception:
    _fetch_ics_raw = None

DEFAULT_WINDOW_FWD = int(os.getenv("NW_WINDOW_FWD_DAYS", "180"))
REPORT_JSON_PATH = os.getenv("NW_REPORT_JSON", "report.json")
BY_SOURCE_DIR = os.getenv("NW_BY_SOURCE_DIR", "by-source")
COMBINED_ICS_PATH = os.getenv("NW_COMBINED_ICS", os.path.join("public", "combined.ics"))
SOURCES_YAML = os.getenv("NW_SOURCES_YAML", "config/sources.yaml")

def _window() -> tuple[datetime, datetime]:
    now = datetime.now(timezone.utc)
    return now - timedelta(days=1), now + timedelta(days=DEFAULT_WINDOW_FWD)

def _ymd(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d")

def _normalize_event(raw: Dict[str, Any]) -> Dict[str, Any]:
    title = raw.get("title") or raw.get("name") or "(untitled)"
    start = raw.get("start_utc") or raw.get("start")
    end = raw.get("end_utc") or raw.get("end")
    calendar = raw.get("source") or "Unknown"
    return {
        "calendar": calendar,
        "source": calendar,
        "title": title,
        "start_utc": start,
        "end_utc": end,
        "location": raw.get("location"),
        "url": raw.get("url") or raw.get("link"),
        "_source": raw.get("_source"),
    }

# ---------- Fetch router ----------
def _to_utc(dt_val: Any) -> Optional[datetime]:
    if isinstance(dt_val, datetime):
        if dt_val.tzinfo is None:
            return dt_val.replace(tzinfo=timezone.utc)
        return dt_val.astimezone(timezone.utc)

    if isinstance(dt_val, date) and not isinstance(dt_val, datetime):
        return datetime(dt_val.year, dt_val.month, dt_val.day, tzinfo=timezone.utc)

    if isinstance(dt_val, str):
        text = dt_val.strip()
        if not text:
            return None
        try:
            normalized = text[:-1] + "+00:00" if text.endswith("Z") else text
            parsed = datetime.fromisoformat(normalized)
        except ValueError:
            try:
                parsed = dtparse.parse(text)
            except (ValueError, TypeError):
                return None
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        else:
            parsed = parsed.astimezone(timezone.utc)
        return parsed

    return None


def _ics_events_as_dicts(items: Any, calendar_name: str, source_url: str,
                         start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    if not items:
        return out

    for ev in items:
        title = getattr(ev, "title", None) or "Event"
        start_dt = _to_utc(getattr(ev, "start_utc", None))
        end_dt = _to_utc(getattr(ev, "end_utc", None))

        if start_dt and (start_dt < start_date or start_dt > (end_date + timedelta(days=1))):
            continue

        out.append({
            "title": title,
            "start_utc": start_dt.isoformat() if start_dt else None,
            "end_utc": end_dt.isoformat() if end_dt else None,
            "url": getattr(ev, "url", None),
            "location": getattr(ev, "location", None),
            "description": getattr(ev, "description", None) or None,
            "uid": getattr(ev, "uid", None),
            "source": calendar_name,
            "calendar": calendar_name,
            "source_url": source_url,
        })

    return out


def _set_meta(source: Dict[str, Any], meta: Dict[str, Any]) -> None:
    if meta:
        source_meta = source.setdefault("_fetch_meta", {})
        source_meta.update({k: v for k, v in meta.items() if v})


def _fetch_one(source: Dict[str, Any], start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
    stype = (source.get("type") or "").strip()
    url = source.get("url") or ""
    sid = (source.get("id") or "").strip()
    name = source.get("name") or sid or (stype or "Source")

    if stype == "tec_rest":
        if not url:
            raise RuntimeError("tec_rest: missing url")

        meta: Dict[str, Any] = {}
        tec_err: Optional[Exception] = None
        events: List[Dict[str, Any]] = []
        prefer_fallback = bool(source.get("prefer_fallback") or source.get("fallback_only"))

        if not prefer_fallback:
            try:
                events = fetch_tec_rest(url, _ymd(start_date), _ymd(end_date)) or []
                if events:
                    _set_meta(source, meta)
                    return events
            except Exception as exc:
                tec_err = exc
                meta.setdefault("warnings", []).append(f"tec_rest request failed: {exc}")

        fallback_ics = source.get("fallback_ics") or source.get("ics_url")
        allow_html_fallback = bool(source.get("allow_html_fallback") or prefer_fallback)
        if fallback_ics and _fetch_ics_raw is not None:
            ics_attempt_warnings: List[str] = []
            for candidate in expand_tec_ics_urls(str(fallback_ics), start_date, end_date):
                try:
                    ics_events, _ = _fetch_ics_raw(candidate, _ymd(start_date), _ymd(end_date))
                except Exception as exc:
                    ics_attempt_warnings.append(f"ics fallback failed for {name}: {exc} ({candidate})")
                    continue

                converted = _ics_events_as_dicts(ics_events, name, candidate, start_date, end_date)
                if converted:
                    note_msg = f"Used TEC ICS fallback: {candidate}"
                    if prefer_fallback:
                        meta.setdefault("notes", []).append(note_msg)
                    else:
                        meta.setdefault("warnings", []).append(note_msg)
                    if ics_attempt_warnings:
                        meta.setdefault("warnings", []).extend(ics_attempt_warnings)
                    _set_meta(source, meta)
                    print(f"[northwoods] INFO: tec_rest fallback via ICS for {name}")
                    return converted

                ics_attempt_warnings.append(f"ics fallback returned no events ({candidate})")

            if ics_attempt_warnings:
                meta.setdefault("warnings", []).extend(ics_attempt_warnings)

        if allow_html_fallback and not events:
            try:
                html_events = fetch_tec_html(source=source, start_date=start_date, end_date=end_date) or []
                if html_events:
                    note_msg = f"Used TEC HTML fallback: {source.get('url') or name}"
                    if prefer_fallback:
                        meta.setdefault("notes", []).append(note_msg)
                    else:
                        meta.setdefault("warnings", []).append(note_msg)
                    _set_meta(source, meta)
                    print(f"[northwoods] INFO: tec_rest fallback via HTML for {name}")
                    return html_events
            except Exception as exc:
                meta.setdefault("warnings", []).append(f"tec_html fallback failed for {name}: {exc}")

        if prefer_fallback and fallback_ics and _fetch_ics_raw is None:
            meta.setdefault("warnings", []).append("ics fallback requested but parser unavailable")

        if tec_err:
            _set_meta(source, meta)
            raise tec_err

        _set_meta(source, meta)
        return events

    if stype == "growthzone_html":
        return fetch_growthzone_html(source=source, start_date=start_date, end_date=end_date) or []

    if stype == "tec_html":
        return fetch_tec_html(source=source, start_date=start_date, end_date=end_date) or []

    if stype == "tec_rss":
        meta: Dict[str, Any] = {}
        events: List[Dict[str, Any]] = []
        rss_exc: Optional[Exception] = None

        prefer_fallback = bool(source.get("prefer_fallback") or source.get("fallback_only"))
        fallback_ics = source.get("fallback_ics") or source.get("ics_url")
        allow_html_fallback = bool(source.get("allow_html_fallback") or prefer_fallback)

        if not prefer_fallback:
            try:
                events = fetch_tec_rss(source=source, start_date=start_date, end_date=end_date) or []
                if events:
                    _set_meta(source, meta)
                    return events
            except Exception as exc:
                rss_exc = exc
                meta.setdefault("warnings", []).append(f"tec_rss failed: {exc}")

        if fallback_ics and _fetch_ics_raw is not None:
            ics_attempt_warnings: List[str] = []
            for candidate in expand_tec_ics_urls(str(fallback_ics), start_date, end_date):
                try:
                    ics_events, _ = _fetch_ics_raw(candidate, _ymd(start_date), _ymd(end_date))
                except Exception as exc:
                    ics_attempt_warnings.append(f"ics fallback failed for {name}: {exc} ({candidate})")
                    continue

                converted = _ics_events_as_dicts(ics_events, name, candidate, start_date, end_date)
                if converted:
                    note_msg = f"Used TEC ICS fallback: {candidate}"
                    if prefer_fallback:
                        meta.setdefault("notes", []).append(note_msg)
                    else:
                        meta.setdefault("warnings", []).append(note_msg)
                    if ics_attempt_warnings:
                        meta.setdefault("warnings", []).extend(ics_attempt_warnings)
                    _set_meta(source, meta)
                    print(f"[northwoods] INFO: tec_rss fallback via ICS for {name}")
                    return converted

                ics_attempt_warnings.append(f"ics fallback returned no events ({candidate})")

            if ics_attempt_warnings:
                meta.setdefault("warnings", []).extend(ics_attempt_warnings)

        if allow_html_fallback:
            try:
                html_events = fetch_tec_html(source=source, start_date=start_date, end_date=end_date) or []
                if html_events:
                    note_msg = f"Used TEC HTML fallback: {source.get('calendar') or source.get('url') or name}"
                    if prefer_fallback:
                        meta.setdefault("notes", []).append(note_msg)
                    else:
                        meta.setdefault("warnings", []).append(note_msg)
                    _set_meta(source, meta)
                    print(f"[northwoods] INFO: tec_rss fallback via HTML for {name}")
                    return html_events
            except Exception as exc:
                meta.setdefault("warnings", []).append(f"tec_html fallback failed for {name}: {exc}")

        if fallback_ics and _fetch_ics_raw is None:
            meta.setdefault("warnings", []).append("ics fallback requested but parser unavailable")

        if rss_exc:
            _set_meta(source, meta)
            raise rss_exc

        _set_meta(source, meta)
        return events

    if stype == "simpleview_html":
        if not url: raise RuntimeError("simpleview_html: missing url")
        return fetch_simpleview_html(url) or []

    if stype == "ics_feed":
        if _fetch_ics_raw is None:
            raise RuntimeError("ics_feed: parser not available")
        if not url:
            raise RuntimeError("ics_feed: missing url")
        return _fetch_ics_raw(url, _ymd(start_date), _ymd(end_date)) or []

    if stype == "stgermain_wp":
        # dynamic import so __init__.py need not be changed
        try:
            mod = import_module("src.parsers.stgermain_wp")
            fetcher = getattr(mod, "fetch_stgermain_wp", None)
        except Exception:
            fetcher = None
        if fetcher is None:
            raise RuntimeError("stgermain_wp: parser not available")
        meta: Dict[str, Any] = {}
        events: List[Dict[str, Any]] = []
        try:
            events = fetcher(source=source, start_date=start_date, end_date=end_date) or []
        except Exception as exc:
            meta.setdefault("warnings", []).append(f"stgermain_wp fetch failed: {exc}")

        if not events:
            try:
                html_events = fetch_tec_html(source=source, start_date=start_date, end_date=end_date) or []
                if html_events:
                    meta.setdefault("notes", []).append("Used TEC HTML fallback")
                    events = html_events
            except Exception as exc:
                meta.setdefault("warnings", []).append(f"TEC HTML fallback failed: {exc}")

        _set_meta(source, meta)
        return events

    raise RuntimeError(f"Unsupported source type: {stype}")

# ---------- IO helpers ----------
def _ensure_dir(path: str) -> None:
    try:
        os.makedirs(path, exist_ok=True)
    except Exception:
        pass


def _ensure_unique_slug(base: str, used: set[str]) -> str:
    slug = base
    suffix = 1
    while slug in used:
        suffix += 1
        slug = f"{base}-{suffix}"
    used.add(slug)
    return slug


def _mirror_to_roots(src_path: str, rel_path: str, roots: List[str]) -> None:
    for root in roots:
        target = os.path.join(root, rel_path)
        _ensure_dir(os.path.dirname(target) or ".")
        try:
            shutil.copy2(src_path, target)
        except Exception as exc:
            print(f"[northwoods] WARN: failed to mirror {src_path} -> {target}: {exc}")


def _rel_path_for_public(path: str) -> str:
    norm = os.path.normpath(path)
    public_root = os.path.normpath("public")
    if os.path.commonpath([public_root, norm]) == public_root:
        return os.path.relpath(norm, public_root)
    return os.path.basename(norm)

def _write_json(path: str, payload: dict) -> None:
    d = os.path.dirname(path) or "."
    _ensure_dir(d)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False, default=json_default)

def _mirror_report(report: Dict[str, Any]) -> None:
    # Primary
    _write_json(REPORT_JSON_PATH, report)
    # Always mirror to Pages-friendly dirs (created if missing)
    for root in ("public", "github-pages", "docs"):
        _write_json(os.path.join(root, "report.json"), report)

def _write_debug_source(sid: str, name: str, stype: str, url: str,
                        ok: bool, err_msg: Optional[str], events: List[Dict[str, Any]],
                        slug: str, ics_path: Optional[str],
                        warnings: Optional[List[str]] = None,
                        notes: Optional[List[str]] = None) -> None:
    blob = {
        "source": {
            "id": sid,
            "name": name,
            "type": stype,
            "url": url,
            "slug": slug,
            "ics_path": ics_path,
        },
        "ok": ok,
        "error": err_msg,
        "count": len(events),
        "warnings": warnings or [],
        "notes": notes or [],
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "events": events[:500],
    }
    filename = f"{slug}.json"
    # local
    _write_json(os.path.join(BY_SOURCE_DIR, filename), blob)
    # pages mirrors
    for root in ("public", "github-pages", "docs"):
        _write_json(os.path.join(root, "by-source", filename), blob)

def main() -> int:
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
    per_source_groups: Dict[str, Dict[str, Any]] = {}
    used_slugs: set[str] = set()

    _ensure_dir(BY_SOURCE_DIR)
    _ensure_dir("public/by-source")
    _ensure_dir("github-pages/by-source")
    _ensure_dir("docs/by-source")

    for src in sources:
        stype = src.get("type")
        sid = src.get("id")
        name = src.get("name") or sid or (stype or "Unknown")
        url = src.get("url") or ""

        print(f"[northwoods] Fetching: {name} ({sid}) [{stype}] -> {url}")

        per_source_events: List[Dict[str, Any]] = []
        err_msg: Optional[str] = None
        warnings: List[str] = []
        notes: List[str] = []
        try:
            per_source_events = _fetch_one(src, start_date, end_date) or []
        except Exception as e:
            err_msg = str(e)
            print(f"[northwoods] ERROR while fetching {name}: {err_msg}")

        meta = src.pop("_fetch_meta", {}) if isinstance(src, dict) else {}
        if isinstance(meta, dict):
            warn_items = meta.get("warnings")
            note_items = meta.get("notes")
            if isinstance(warn_items, list):
                warnings.extend(str(w) for w in warn_items if w)
            elif isinstance(warn_items, str):
                warnings.append(warn_items)
            if isinstance(note_items, list):
                notes.extend(str(n) for n in note_items if n)
            elif isinstance(note_items, str):
                notes.append(note_items)

        base_slug = slugify(name or sid or stype or "source")
        slug = _ensure_unique_slug(base_slug, used_slugs)
        ics_rel_path: Optional[str] = None
        if per_source_events:
            for ev in per_source_events:
                ev.setdefault("calendar", name)
                ev.setdefault("source", name)
                ev["calendar_slug"] = slug
            per_source_groups[slug] = {
                "name": name,
                "slug": slug,
                "events": per_source_events,
            }
            ics_rel_path = f"by-source/{slug}.ics"
        try:
            _write_debug_source(
                sid,
                name,
                stype,
                url,
                err_msg is None,
                err_msg,
                per_source_events,
                slug,
                ics_rel_path,
                warnings,
                notes,
            )
        except Exception:
            pass

        source_logs.append({
            "id": sid, "name": name, "type": stype, "url": url,
            "ok": err_msg is None, "count": len(per_source_events), "error": err_msg,
            "slug": slug,
            "ics_path": ics_rel_path,
            "warnings": warnings,
            "notes": notes,
        })
        all_events.extend(per_source_events)

    try:
        count, combined_path = write_combined_ics(all_events, COMBINED_ICS_PATH)
        rel_combined = _rel_path_for_public(combined_path)
        _mirror_to_roots(combined_path, rel_combined, ["github-pages", "docs"])
        print(f"[northwoods] Wrote combined ICS ({count} events): {combined_path}")
    except Exception as e:
        print(f"[northwoods] ERROR writing combined ICS: {e}")

    per_source_written: Dict[str, str] = {}
    try:
        per_source_written = write_per_source_ics(
            per_source_groups,
            os.path.join("public", "by-source"),
        )
        for slug, path in per_source_written.items():
            rel = _rel_path_for_public(path)
            _mirror_to_roots(path, rel, ["github-pages", "docs"])
            for log in source_logs:
                if log["slug"] == slug:
                    log["ics_path"] = rel
    except Exception as e:
        print(f"[northwoods] ERROR writing per-source ICS: {e}")

    normalized_preview = [_normalize_event(e) for e in all_events]
    preview = normalized_preview[:500]
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "sources_processed": len(source_logs),
        "total_events": len(all_events),
        "source_logs": source_logs,
        "events_preview": preview,
        "normalized_events": preview,
        "events_preview_count": min(500, len(normalized_preview)),
    }

    try:
        _mirror_report(report)
    except Exception as e:
        print(f"[northwoods] ERROR writing report.json: {e}")

    print(json.dumps({"ok": True, "events": len(all_events)}))
    return 0

if __name__ == "__main__":
    sys.exit(main())
