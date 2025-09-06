"""
Central export for parser entrypoints.

We keep the public API stable so main.py can:
    from src.parsers import fetch_tec_rest, fetch_growthzone_html, fetch_simpleview_html, fetch_tec_html

Each fetch_* must accept:
    (source: dict, start_date: Optional[str] = None, end_date: Optional[str] = None, **kwargs)
and return:
    (events: list[dict], diag: dict)

This file ONLY wires and lightly wraps imports to guarantee signatures.
"""

from importlib import import_module
from typing import Any, Callable, Dict, Tuple, List


def _safe_wrap(func: Callable) -> Callable:
    """
    Wrap a fetcher so it always accepts (source, start_date=None, end_date=None, **kwargs)
    and always returns (events, diag).
    """
    def wrapped(source: Dict[str, Any], start_date: str | None = None, end_date: str | None = None, **kwargs) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        # Some older implementations might ignore dates; that’s OK.
        res = func(source, start_date, end_date, **kwargs) if func.__code__.co_argcount >= 3 else func(source)
        # Normalize return type
        if isinstance(res, tuple) and len(res) == 2:
            events, diag = res
        else:
            events, diag = res, {}
        # Ensure types
        events = events or []
        if not isinstance(diag, dict):
            diag = {"note": "non-dict diag coerced"}
        return events, diag
    return wrapped


def _load(module: str, attr: str) -> Callable:
    m = import_module(f".{module}", __name__)
    f = getattr(m, attr, None)
    if f is None or not callable(f):
        raise ImportError(f"Failed to expose '{attr}' from parsers.{module}: not found or not callable.")
    return _safe_wrap(f)


# Public exports used by src/main.py (do not rename)
fetch_tec_rest = _load("tec_rest", "fetch_tec_rest")
fetch_tec_html = _load("tec_html", "fetch_tec_html")  # HTML fallback (auto-delegates to REST if present)
fetch_growthzone_html = _load("growthzone_html", "fetch_growthzone_html")
fetch_simpleview_html = _load("simpleview_html", "fetch_simpleview_html")

__all__ = [
    "fetch_tec_rest",
    "fetch_tec_html",
    "fetch_growthzone_html",
    "fetch_simpleview_html",
]
