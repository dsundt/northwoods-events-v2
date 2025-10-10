# src/parsers/__init__.py
from __future__ import annotations
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List, Tuple, Optional
import inspect

def _default_window() -> Tuple[datetime, datetime]:
    now = datetime.now(timezone.utc)
    return now - timedelta(days=1), now + timedelta(days=180)

def _window(start_date: Optional[datetime], end_date: Optional[datetime]):
    return _default_window() if (start_date is None or end_date is None) else (start_date, end_date)

def _normalize(ret: Any, func) -> List[Dict[str, Any]]:
    if ret is None:
        return []
    if isinstance(ret, tuple):  # some fetchers return (events, meta)
        ret = ret[0]
    if isinstance(ret, list):
        return ret
    if isinstance(ret, Iterable):
        return list(ret)
    raise TypeError(f"Fetcher {func.__module__}.{func.__name__} returned non-list: {type(ret)}")

def _smart_call(func, source, start_date: datetime, end_date: datetime):
    """Use kwargs only if the function declares them; never pass dates positionally."""
    sig = inspect.signature(func)
    params = sig.parameters
    kwargs = {}
    if "start_date" in params:
        kwargs["start_date"] = start_date
    if "end_date" in params:
        kwargs["end_date"] = end_date
    if kwargs:
        ret = func(source, **kwargs)
    else:
        ret = func(source)
    return _normalize(ret, func)

def fetch_tec_rest(source,
                   start_date: Optional[datetime] = None,
                   end_date: Optional[datetime] = None):
    from . import tec_rest as _m
    s, e = _window(start_date, end_date)
    return _smart_call(_m.fetch_tec_rest, source, s, e)

def fetch_growthzone_html(source,
                          start_date: Optional[datetime] = None,
                          end_date: Optional[datetime] = None):
    from . import growthzone_html as _m
    s, e = _window(start_date, end_date)
    return _smart_call(_m.fetch_growthzone_html, source, s, e)

def fetch_tec_html(source,
                   start_date: Optional[datetime] = None,
                   end_date: Optional[datetime] = None):
    from . import tec_html as _m
    s, e = _window(start_date, end_date)
    return _smart_call(_m.fetch_tec_html, source, s, e)

def fetch_tec_rss(source,
                  start_date: Optional[datetime] = None,
                  end_date: Optional[datetime] = None):
    from . import tec_rss as _m
    s, e = _window(start_date, end_date)
    return _smart_call(_m.fetch_tec_rss, source, s, e)

def fetch_simpleview_html(source,
                          start_date: Optional[datetime] = None,
                          end_date: Optional[datetime] = None):
    from . import simpleview_html as _m
    s, e = _window(start_date, end_date)
    return _smart_call(_m.fetch_simpleview_html, source, s, e)

def fetch_ics_feed(source,
                   start_date: Optional[datetime] = None,
                   end_date: Optional[datetime] = None):
    # In this repo the function is named fetch_ics
    try:
        from .ics_feed import fetch_ics as _impl
    except Exception:
        return []
    s, e = _window(start_date, end_date)
    # The ics fetcher expects a URL string
    url = source if isinstance(source, str) else (source.get("url") if isinstance(source, dict) else None)
    if not url:
        return []
    return _normalize(_impl(url, s, e), _impl)

def fetch_icsbuild(source,
                   start_date: Optional[datetime] = None,
                   end_date: Optional[datetime] = None):
    try:
        try:
            from .icsbuild import fetch_icsbuild as _impl  # vendored
        except Exception:
            from icsbuild import fetch_icsbuild as _impl  # external
    except Exception:
        return []
    s, e = _window(start_date, end_date)
    return _smart_call(_impl, source, s, e)

# NEW: exported so main.py can import it
def fetch_stgermain_wp(source,
                       start_date: Optional[datetime] = None,
                       end_date: Optional[datetime] = None):
    from .stgermain_wp import fetch_stgermain_wp as _impl
    s, e = _window(start_date, end_date)
    return _smart_call(_impl, source, s, e)

__all__ = [
    "fetch_tec_rest",
    "fetch_growthzone_html",
    "fetch_tec_html",
    "fetch_tec_rss",
    "fetch_simpleview_html",
    "fetch_ics_feed",
    "fetch_icsbuild",
    "fetch_stgermain_wp",  # NEW
]
