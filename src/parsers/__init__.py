# src/parsers/__init__.py
from __future__ import annotations

from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple
from datetime import datetime, timedelta, timezone

# ---- helpers ---------------------------------------------------------------

def _default_window() -> Tuple[datetime, datetime]:
    # Conservative default: yesterday .. +6 months
    now_utc = datetime.now(timezone.utc)
    start = now_utc - timedelta(days=1)
    end = now_utc + timedelta(days=180)
    return start, end

def _window_if_needed(start_date: Optional[datetime],
                      end_date: Optional[datetime]) -> Tuple[datetime, datetime]:
    if start_date is None or end_date is None:
        return _default_window()
    return start_date, end_date

def _normalize_return(ret: Any, func: Callable) -> List[Dict[str, Any]]:
    if ret is None:
        return []
    if isinstance(ret, tuple):
        # Some older fetchers return (events, diag) -> take the events
        ret = ret[0]
    if isinstance(ret, list):
        return ret
    if isinstance(ret, Iterable):
        try:
            return list(ret)
        except Exception:
            pass
    raise TypeError(f"Fetcher {func.__module__}.{func.__name__} returned non-list: {type(ret)}")

def _call_fetcher(func: Callable,
                  source: Dict[str, Any],
                  start_date: datetime,
                  end_date: datetime) -> List[Dict[str, Any]]:
    """
    Be backward/forward compatible with multiple call signatures:
      - func(source, start_date, end_date)
      - func(source, start_date=start_date, end_date=end_date)
      - func(source)  (legacy)
    Normalize the return to a list.
    """
    # 1) Positional 3-arg
    try:
        ret = func(source, start_date, end_date)
        return _normalize_return(ret, func)
    except TypeError:
        pass

    # 2) Keyword 3-arg
    try:
        ret = func(source=source, start_date=start_date, end_date=end_date)
        return _normalize_return(ret, func)
    except TypeError:
        pass

    # 3) Legacy 1-arg
    ret = func(source)
    return _normalize_return(ret, func)

# ---- wrappers (stable import surface for main.py) --------------------------

def fetch_tec_rest(source: Dict[str, Any],
                   start_date: Optional[datetime] = None,
                   end_date: Optional[datetime] = None) -> List[Dict[str, Any]]:
    from . import tec_rest as _impl  # local module
    s, e = _window_if_needed(start_date, end_date)
    return _call_fetcher(_impl.fetch_tec_rest, source, s, e)

def fetch_growthzone_html(source: Dict[str, Any],
                          start_date: Optional[datetime] = None,
                          end_date: Optional[datetime] = None) -> List[Dict[str, Any]]:
    from .growthzone_html import fetch_growthzone_html as _impl
    s, e = _window_if_needed(start_date, end_date)
    return _call_fetcher(_impl, source, s, e)

def fetch_tec_html(source: Dict[str, Any],
                   start_date: Optional[datetime] = None,
                   end_date: Optional[datetime] = None) -> List[Dict[str, Any]]:
    from .tec_html import fetch_tec_html as _impl
    s, e = _window_if_needed(start_date, end_date)
    return _call_fetcher(_impl, source, s, e)

def fetch_simpleview_html(source: Dict[str, Any],
                          start_date: Optional[datetime] = None,
                          end_date: Optional[datetime] = None) -> List[Dict[str, Any]]:
    from .simpleview_html import fetch_simpleview_html as _impl
    s, e = _window_if_needed(start_date, end_date)
    return _call_fetcher(_impl, source, s, e)

# ---- OPTIONAL fetchers (no hard dependency; safe if modules absent) --------

def fetch_ics_feed(source: Dict[str, Any],
                   start_date: Optional[datetime] = None,
                   end_date: Optional[datetime] = None) -> List[Dict[str, Any]]:
    """
    Only used if you actually configure a source with type 'ics_feed'.
    If the ics modules aren't present, we fail closed by returning [] (no events)
    instead of crashing imports during build.
    """
    try:
        # Try absolute then relative import patterns
        try:
            from src.ics_fetch import fetch_ics_feed as _impl
        except Exception:
            from ics_fetch import fetch_ics_feed as _impl  # pragma: no cover
    except Exception:
        return []
    s, e = _window_if_needed(start_date, end_date)
    return _call_fetcher(_impl, source, s, e)

def fetch_icsbuild(source: Dict[str, Any],
                   start_date: Optional[datetime] = None,
                   end_date: Optional[datetime] = None) -> List[Dict[str, Any]]:
    try:
        try:
            from src.icsbuild import fetch_icsbuild as _impl
        except Exception:
            from icsbuild import fetch_icsbuild as _impl  # pragma: no cover
    except Exception:
        return []
    s, e = _window_if_needed(start_date, end_date)
    return _call_fetcher(_impl, source, s, e)

__all__ = [
    "fetch_tec_rest",
    "fetch_growthzone_html",
    "fetch_tec_html",
    "fetch_simpleview_html",
    # optional
    "fetch_ics_feed",
    "fetch_icsbuild",
]
