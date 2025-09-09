# src/parsers/__init__.py
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List, Tuple, Optional
import inspect

# -------------------- time windows --------------------

def _default_window() -> Tuple[datetime, datetime]:
    now = datetime.now(timezone.utc)
    # match your typical window: yesterday .. +180d
    return now - timedelta(days=1), now + timedelta(days=180)

def _window(start_date: Optional[datetime], end_date: Optional[datetime]) -> Tuple[datetime, datetime]:
    return _default_window() if (start_date is None or end_date is None) else (start_date, end_date)

# -------------------- normalization helpers --------------------

def _normalize(ret: Any, func) -> List[Dict[str, Any]]:
    """
    Accepts:
      - list[dict]
      - dict (single event)
      - None
      - iterables
    Returns list[dict] and filters out falsy/empty items.
    """
    if ret is None:
        return []
    if isinstance(ret, dict):
        return [ret]
    if isinstance(ret, list):
        return [r for r in ret if r]
    if isinstance(ret, Iterable):
        try:
            return [r for r in ret if r]
        except Exception:
            return []
    # unknown shape
    return []

def _smart_call(func, source: Dict[str, Any], start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
    """
    Call `func` with whatever parameters it supports:
    supported names: source, start_date, end_date, session, logger
    """
    sig = inspect.signature(func)
    # Build kwargs only for parameters the function actually accepts.
    kwargs: Dict[str, Any] = {}
    for name in sig.parameters:
        if name == "source":
            kwargs[name] = source
        elif name == "start_date":
            kwargs[name] = start_date
        elif name == "end_date":
            kwargs[name] = end_date
        elif name == "session":
            kwargs[name] = None     # let fetchers create their own Session if needed
        elif name == "logger":
            kwargs[name] = None
        # ignore unknowns; keep defaults

    try:
        ret = func(**kwargs)
    except TypeError:
        # Fallback: try positional (source, start_date, end_date)
        try:
            ret = func(source, start_date, end_date)
        except Exception:
            # Last resort: just (source,)
            ret = func(source)
    return _normalize(ret, func)

# -------------------- public wrappers (lazy imports) --------------------

def fetch_tec_rest(source: Dict[str, Any], start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> List[Dict[str, Any]]:
    s, e = _window(start_date, end_date)
    try:
        from .tec_rest import fetch_tec_rest as _impl
    except Exception:
        return []
    return _smart_call(_impl, source, s, e)

def fetch_growthzone_html(source: Dict[str, Any], start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> List[Dict[str, Any]]:
    s, e = _window(start_date, end_date)
    try:
        from .growthzone_html import fetch_growthzone_html as _impl
    except Exception:
        return []
    return _smart_call(_impl, source, s, e)

def fetch_tec_html(source: Dict[str, Any], start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> List[Dict[str, Any]]:
    s, e = _window(start_date, end_date)
    try:
        from .tec_html import fetch_tec_html as _impl
    except Exception:
        return []
    return _smart_call(_impl, source, s, e)

def fetch_simpleview_html(source: Dict[str, Any], start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> List[Dict[str, Any]]:
    s, e = _window(start_date, end_date)
    try:
        from .simpleview_html import fetch_simpleview_html as _impl
    except Exception:
        return []
    return _smart_call(_impl, source, s, e)

def fetch_ics_feed(source: Dict[str, Any], start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> List[Dict[str, Any]]:
    s, e = _window(start_date, end_date)
    try:
        from .ics_feed import fetch_ics_feed as _impl
    except Exception:
        return []
    return _smart_call(_impl, source, s, e)

def fetch_icsbuild(source: Dict[str, Any], start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> List[Dict[str, Any]]:
    s, e = _window(start_date, end_date)
    try:
        # If it's provided as a top-level module in your env
        from icsbuild import fetch_icsbuild as _impl  # type: ignore
    except Exception:
        # Or vendored locally
        try:
            from .icsbuild import fetch_icsbuild as _impl  # type: ignore
        except Exception:
            return []
    return _smart_call(_impl, source, s, e)

# -------------------- NEW: St. Germain WP crawler --------------------

def fetch_stgermain_wp(source: Dict[str, Any], start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> List[Dict[str, Any]]:
    """
    Host-scoped crawler for https://st-germain.com/events/ (WordPress).
    This is isolated from GrowthZone so it cannot affect other sources.
    """
    s, e = _window(start_date, end_date)
    try:
        from .stgermain_wp import fetch_stgermain_wp as _impl
    except Exception:
        return []
    return _smart_call(_impl, source, s, e)

# -------------------- exports --------------------

__all__ = [
    "fetch_tec_rest",
    "fetch_growthzone_html",
    "fetch_tec_html",
    "fetch_simpleview_html",
    "fetch_ics_feed",
    "fetch_icsbuild",
    # new
    "fetch_stgermain_wp",
]
