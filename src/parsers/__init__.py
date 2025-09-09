# src/parsers/__init__.py
from __future__ import annotations

import inspect
from typing import Any, Dict, List, Optional

# Import concrete fetchers
from .tec_rest import fetch_tec_rest as _tec_rest
from .growthzone_html import fetch_growthzone_html as _growthzone_html
from .tec_html import fetch_tec_html as _tec_html
from .simpleview_html import fetch_simpleview_html as _simpleview_html
from .ics_feed import fetch_ics_feed as _ics_feed

# Optional icsbuild (vendored or external)
try:
    from .icsbuild import fetch_icsbuild as _icsbuild  # type: ignore
except Exception:  # pragma: no cover
    _icsbuild = None

# NEW: St. Germain WordPress crawler (host-scoped)
from .stgermain_wp import fetch_stgermain_wp as _stgermain_wp


def _call(fetcher, source: Dict[str, Any], session=None, start_date=None, end_date=None, logger=None):
    """
    Call a fetcher with whatever it supports, but ALWAYS pass a non-None `source`.
    Order of attempts:
      1) kwargs with all names (most robust)
      2) (source, session, start_date, end_date)
      3) (source, start_date, end_date)
      4) (source,)
    """
    if source is None:
        source = {}
    try:
        return fetcher(
            source=source,
            session=session,
            start_date=start_date,
            end_date=end_date,
            logger=logger,
        )
    except TypeError:
        # Some fetchers may not accept logger/session kwargs
        try:
            return fetcher(source, session, start_date, end_date)
        except TypeError:
            try:
                return fetcher(source, start_date, end_date)
            except TypeError:
                return fetcher(source)


# Public adapter functions with the runner’s expected signature
def tec_rest(source: Dict[str, Any], session=None, start_date=None, end_date=None, logger=None):
    return _call(_tec_rest, source, session, start_date, end_date, logger)

def growthzone_html(source: Dict[str, Any], session=None, start_date=None, end_date=None, logger=None):
    return _call(_growthzone_html, source, session, start_date, end_date, logger)

def tec_html(source: Dict[str, Any], session=None, start_date=None, end_date=None, logger=None):
    return _call(_tec_html, source, session, start_date, end_date, logger)

def simpleview_html(source: Dict[str, Any], session=None, start_date=None, end_date=None, logger=None):
    return _call(_simpleview_html, source, session, start_date, end_date, logger)

def ics_feed(source: Dict[str, Any], session=None, start_date=None, end_date=None, logger=None):
    return _call(_ics_feed, source, start_date=start_date, end_date=end_date, session=session, logger=logger)

def icsbuild(source: Dict[str, Any], session=None, start_date=None, end_date=None, logger=None):
    if _icsbuild is None:
        return []
    return _call(_icsbuild, source, session, start_date, end_date, logger)

def stgermain_wp(source: Dict[str, Any], session=None, start_date=None, end_date=None, logger=None):
    return _call(_stgermain_wp, source, session, start_date, end_date, logger)


# The runner uses this mapping to resolve `type:` in sources.yaml
PARSERS = {
    "tec_rest": tec_rest,
    "growthzone_html": growthzone_html,
    "tec_html": tec_html,
    "simpleview_html": simpleview_html,
    "ics_feed": ics_feed,
    "icsbuild": icsbuild,         # optional; returns [] if not available
    "stgermain_wp": stgermain_wp, # NEW: WP archive/detail crawler for St. Germain
}

__all__ = ["PARSERS"]
