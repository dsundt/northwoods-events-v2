# src/main.py
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from importlib import import_module

import yaml

# ---- Parsers in this repo (unchanged) ----
from src.parsers import (
    fetch_tec_rest,          # POSitional: (url: str, start_utc: str|None, end_utc: str|None)
    fetch_growthzone_html,   # kwargs:     (source: dict, [session], [start_date], [end_date])
    fetch_simpleview_html,   # POSitional: (url: str, timeout=20, max_items=200)
    fetch_tec_html,          # kwargs:     (source: dict, [session], [start_date], [end_date])
)

# Optional: ICS (POSitional fetch_ics(url, start_utc, end_utc))
try:
    from src.parsers.ics_feed import fetch_ics as _fetch_ics_raw  # type: ignore
except Exception:
    _fetch_ics_raw = None

DEFAULT_WINDOW_FWD = int(os.getenv("NW_WINDOW_FWD_DAYS", "180"))
REPORT_JSON_PATH = os.getenv("NW_REPORT_JSON", "report.json")
BY_SOURCE_DIR = os.getenv("NW_BY_SOURCE_DIR", "by-source")
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
    return {
        "calendar": raw.get("source") or "Unknown",
        "title": title,
        "start_utc": start,
        "end_utc": end,
        "location": raw.get("location"),
        "url": raw.get("url") or raw.get("link"),
        "_source": raw.get("_source"),
    }

# ---------- Rhinelander-only GrowthZone label fallback (surgical, opt-in by id) ----------
def _gz_label(text: str, label: str) -> Optional[str]:
    import re
    m = re.search(rf"(?im)^{label}\s*:\s*(.+)$", text)
    return m.group(1).strip() if m else None

def _parse_rhinelander_detail_with_labels(html: str) -> Optional[Dict[str, Any]]:
    import re
    from html import unescape
    from datetime import datetime
    # strip to text
    t = re.sub(r"(?is)<script[^>]*>.*?</script>|<style[^>]*>.*?</style>", "", html)
    t = re.sub(r"(?is)<br\s*/?>|</p>", "\n", t)
    t = re.sub(r"(?is)<[^>]+>", "", t)
    t = unescape(t)

    date_s = _gz_label(t, "Date")
    if not date_s:
        return None
    m = re.search(r"(?i)\b([A-Z][a-z]+)\s+(\d{1,2})(?:st|nd|rd|th)?,\s*(\d{4})", date_s)
    if not m:
        return None
    mon, d, y = m.groups()
    months = {m: i for i, m in enumerate(
        ["January","February","March","April","May","June","July","August","September","October","November","December"], 1)}
    M = months.get(mon)
    if not M:
        return None
    start = datetime(int(y), M, int(d))
    end = None

    time_s = _gz_label(t, "Time")
    if time_s:
        rng = re.search(r"(?i)(\d{1,2}(?::\d{2})?\s*(am|pm))\s*(?:–|-|to)\s*(\d{1,2}(?::\d{2})?\s*(am|pm))", time_s)
        single = re.search(r"(?i)(\d{1,2})(?::(\d{
