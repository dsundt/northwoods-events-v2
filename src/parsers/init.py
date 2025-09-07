# src/parsers/__init__.py
"""
Unified import surface for parser functions.

main.py imports:
  - fetch_tec_rest(url, start_utc=None, end_utc=None)
  - fetch_tec_html(url, start_utc=None, end_utc=None)
  - fetch_growthzone_html(url, start_utc=None, end_utc=None)
  - fetch_simpleview_html(url, start_utc=None, end_utc=None)

This module guarantees those names exist with the correct 3-arg signature,
wrapping the underlying implementations if needed, and falling back to a
safe no-op that returns [] (and logs) rather than raising import errors.
"""

from importlib import import_module
from typing import Callable, List, Dict, Any

def _safe_get(attr_module: str, attr_name: str) -> Callable:
    """
    Try importing `attr_module` from this package and pulling `attr_name`.
    If missing/invalid, return a stub function with the correct signature.
    """
    try:
        mod = import_module(f".{attr_module}", __package__)
        func = getattr(mod, attr_name, None)
        if callable(func):
            return func
    except Exception as e:
        # Soft-fail to keep the rest of the pipeline running
        _diag_log(f"[parsers] Failed to import {attr_module}.{attr_name}: {e}")

    # Return a stub with the correct signature
    def _stub(url: str, start_utc: str = None, end_utc: str = None) -> List[Dict[str, Any]]:
        _diag_log(f"[parsers] STUB invoked for {attr_module}.{attr_name} (url={url})")
        return []
    return _stub

def _wrap_3arg(func: Callable, name: str) -> Callable:
    """
    Ensure the callable accepts exactly (url, start_utc=None, end_utc=None).
    If it already does, return as-is; otherwise wrap.
    """
    def _wrapped(url: str, start_utc: str = None, end_utc: str = None):
        try:
            # Most of our real implementations already accept (url, start, end).
            # If the underlying func only accepts (url), this will TypeError; retry.
            return func(url, start_utc, end_utc)
        except TypeError:
            # Fallback: call with just (url)
            return func(url)
    _wrapped.__name__ = name
    return _wrapped

def _diag_log(msg: str) -> None:
    try:
        print(msg, flush=True)
    except Exception:
        pass

# Load underlying implementations (if present)
_tec_rest_raw = _safe_get("tec_rest", "fetch_tec_rest")
_tec_html_raw = _safe_get("tec_html", "fetch_tec_html")
_growthzone_raw = _safe_get("growthzone_html", "fetch_growthzone_html")
_simpleview_raw = _safe_get("simpleview_html", "fetch_simpleview_html")

# Wrap to enforce a uniform 3-arg signature
fetch_tec_rest = _wrap_3arg(_tec_rest_raw, "fetch_tec_rest")
fetch_tec_html = _wrap_3arg(_tec_html_raw, "fetch_tec_html")
fetch_growthzone_html = _wrap_3arg(_growthzone_raw, "fetch_growthzone_html")
fetch_simpleview_html = _wrap_3arg(_simpleview_raw, "fetch_simpleview_html")

__all__ = [
    "fetch_tec_rest",
    "fetch_tec_html",
    "fetch_growthzone_html",
    "fetch_simpleview_html",
]
