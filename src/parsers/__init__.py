# src/parsers/__init__.py
from importlib import import_module
from typing import Callable, List, Dict, Any

def _diag(msg: str) -> None:
    try:
        print(msg, flush=True)
    except Exception:
        pass

def _safe_import(modname: str, funcname: str) -> Callable:
    try:
        mod = import_module(f".{modname}", __package__)
        fn = getattr(mod, funcname, None)
        if callable(fn):
            return fn
        _diag(f"[parsers] {modname}.{funcname} not found, using stub")
    except Exception as e:
        _diag(f"[parsers] import error {modname}.{funcname}: {e}")

    def _stub(url: str, start_utc: str = None, end_utc: str = None) -> List[Dict[str, Any]]:
        _diag(f"[parsers] STUB for {modname}.{funcname} url={url}")
        return []
    return _stub

def _wrap_3(fn: Callable, name: str) -> Callable:
    def _wrapped(url: str, start_utc: str = None, end_utc: str = None):
        try:
            return fn(url, start_utc, end_utc)  # preferred
        except TypeError:
            return fn(url)  # legacy 1-arg fallback
    _wrapped.__name__ = name
    return _wrapped

fetch_tec_rest        = _wrap_3(_safe_import("tec_rest", "fetch_tec_rest"), "fetch_tec_rest")
fetch_tec_html        = _wrap_3(_safe_import("tec_html", "fetch_tec_html"), "fetch_tec_html")
fetch_growthzone_html = _wrap_3(_safe_import("growthzone_html", "fetch_growthzone_html"), "fetch_growthzone_html")
fetch_simpleview_html = _wrap_3(_safe_import("simpleview_html", "fetch_simpleview_html"), "fetch_simpleview_html")

__all__ = [
    "fetch_tec_rest",
    "fetch_tec_html",
    "fetch_growthzone_html",
    "fetch_simpleview_html",
]
