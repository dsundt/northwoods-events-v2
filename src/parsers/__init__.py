# src/parsers/__init__.py
from __future__ import annotations

from typing import Callable, Dict, Any, List
import traceback

# -----------------------------
# Helper: wrap fetchers to normalize return type to List[dict]
# -----------------------------
def _stub_fetcher(name: str) -> Callable[..., List[dict]]:
    def _stub(url: str, *args: Any, **kwargs: Any) -> List[dict]:
        print(f"[parsers] STUB for {name} url={url}")
        return []  # IMPORTANT: return a list (never a tuple)
    return _stub

def _wrap_fetcher(name: str, fn: Callable[..., Any] | None) -> Callable[..., List[dict]]:
    """
    Wrap a parser fetcher so callers always get List[dict].
    - (events, diag) -> events
    - None -> []
    - Iterable -> list(iterable)
    - Otherwise -> TypeError with clear message
    """
    if fn is None:
        return _stub_fetcher(name)

    def _wrapped(*args: Any, **kwargs: Any) -> List[dict]:
        res = fn(*args, **kwargs)
        if res is None:
            return []
        # Old pattern: (events, diag)
        if isinstance(res, tuple):
            # Prefer the first list-like element
            for part in res:
                if isinstance(part, list):
                    return part
            return []
        if isinstance(res, list):
            return res
        # Last resort: try to list() it (for generators)
        try:
            return list(res)
        except Exception as e:
            raise TypeError(f"Fetcher {name} returned non-list: {type(res)}") from e

    return _wrapped

# -----------------------------
# Imports with resilient fallbacks & logging
# -----------------------------

# growthzone_html
_fetch_growthzone = None
try:
    from .growthzone_html import fetch_growthzone_html as _fetch_growthzone
except Exception as e:
    print(f"[parsers] import error growthzone_html.fetch_growthzone_html: {e}")

# simpleview_html
_fetch_simpleview = None
try:
    from .simpleview_html import fetch_simpleview_html as _fetch_simpleview
except Exception as e:
    print(f"[parsers] import error simpleview_html.fetch_simpleview_html: {e}")

# tec_rest (try common locations)
_fetch_tec_rest = None
_tec_errors: List[str] = []
if _fetch_tec_rest is None:
    try:
        from .tec_rest import fetch_tec_rest as _fetch_tec_rest  # typical layout
    except Exception as e:
        _tec_errors.append(str(e))
if _fetch_tec_rest is None:
    try:
        from src.tec_rest import fetch_tec_rest as _fetch_tec_rest  # alternate project layout
    except Exception as e:
        _tec_errors.append(str(e))
if _fetch_tec_rest is None and _tec_errors:
    print(f"[parsers] import error tec_rest.fetch_tec_rest: {' | '.join(_tec_errors)}")

# ics_fetch (existing file in repo: src/ics_fetch.py)
_fetch_ics = None
_ics_errors: List[str] = []
if _fetch_ics is None:
    try:
        from src.ics_fetch import fetch_ics_feed as _fetch_ics
    except Exception as e:
        _ics_errors.append(str(e))
if _fetch_ics is None:
    # Relative import fallback if package structure differs
    try:
        from ..ics_fetch import fetch_ics_feed as _fetch_ics  # type: ignore
    except Exception as e:
        _ics_errors.append(str(e))
if _fetch_ics is None and _ics_errors:
    print(f"[parsers] import error ics_fetch.fetch_ics_feed: {' | '.join(_ics_errors)}")

# -----------------------------
# Public fetcher map
# -----------------------------
FETCHERS: Dict[str, Callable[..., List[dict]]] = {
    # Keep existing, working TEC REST sources unchanged
    "tec_rest": _wrap_fetcher("tec_rest.fetch_tec_rest", _fetch_tec_rest),

    # GrowthZone HTML (Rhinelander)
    "growthzone_html": _wrap_fetcher("growthzone_html.fetch_growthzone_html", _fetch_growthzone),

    # Simpleview HTML (Minocqua)
    "simpleview_html": _wrap_fetcher("simpleview_html.fetch_simpleview_html", _fetch_simpleview),

    # ICS calendar fetcher (St. Germain) — supports both keys to be forgiving
    "ics_fetch": _wrap_fetcher("ics_fetch.fetch_ics_feed", _fetch_ics),
    "ics_feed": _wrap_fetcher("ics_fetch.fetch_ics_feed", _fetch_ics),  # alias, prevents "Unsupported source type"
}

def get_fetcher(source_type: str) -> Callable[..., List[dict]]:
    try:
        return FETCHERS[source_type]
    except KeyError:
        raise ValueError(f"Unsupported source type: {source_type}")
