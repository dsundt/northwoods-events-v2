# src/main.py
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import yaml

# ---- Required parsers available in this repo ----
from src.parsers import (
    fetch_tec_rest,          # expects: (url: str, start_utc: str | None, end_utc: str | None)
    fetch_growthzone_html,   # expects: (source: dict, [session], [start_date], [end_date])
    fetch_simpleview_html,   # expects: (url: str, timeout=20, max_items=200)
    fetch_tec_html,          # expects: (source: dict, [session], [start_date], [end_date])
)

# ---- Optional parsers (guard so builds never break if missing) ----
try:
    # In this repo, ICS fetcher is named fetch_ics(url, start_utc, end_utc)
    from src.parsers.ics_feed import fetch_ics as _fetch_ics_raw  # type: ignore
except Exception:
    _fetch_ics_raw = None

try:
    # St. Germain WordPress crawler (only used if you add a st-germain-wp source)
    from src.parsers import fetch_stgermain_wp  # from __init__ wrapper
except Exception:
    fetch_stgermain_wp = None


# ---------------------- config ----------------------

DEFAULT_WINDOW_FWD = int(os.getenv("NW_WINDOW_FWD_DAYS", "180"))
REPORT_JSON_PATH = os.getenv("NW_REPORT_JSON", "report.json")
SOURCES_YAML = os.getenv("NW_SOURCES_YAML", "config/sources.yaml")


def _window() -> (datetime, datetime):
    now = datetime.now(timezone.utc)
    return now - timedelta(days=1), now + timedelta(days=DEFAULT_WINDOW_FWD)


def _fmt_date_only(dt: datetime) -> str:
    # For TEC/ICS REST endpoints that want YYYY-MM-DD
    return dt.strftime("%Y-%m-%d")


def _normalize_event(raw: Dict[str, Any], s
