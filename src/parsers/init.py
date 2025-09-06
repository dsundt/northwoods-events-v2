# Path: src/parsers/__init__.py
"""
Unified export surface for parsers. Every fetcher MUST accept:
    fetch_X(source: dict, start_date: str, end_date: str) -> list[dict]

This module exposes:
    fetch_tec_rest
    fetch_tec_html
    fetch_growthzone_html
    fetch_simpleview_html
"""

from importlib import import_module

__all__ = [
    "fetch_tec_rest",
    "fetch_tec_html",
    "fetch_growthzone_html",
    "fetch_simpleview_html",
]

def _load_attr(module_name: str, attr: str):
    mod = import_module(f"src.parsers.{module_name}")
    fn = getattr(mod, attr, None)
    if fn is None or not callable(fn):
        raise ImportError(
            f"Failed to expose '{attr}' from parsers.{module_name}: "
            f"callable not found."
        )
    return fn

# Explicit, stable bindings (no magic registry here).
fetch_tec_rest = _load_attr("tec_rest", "fetch_tec_rest")
fetch_tec_html = _load_attr("tec_html", "fetch_tec_html")
fetch_growthzone_html = _load_attr("growthzone_html", "fetch_growthzone_html")
fetch_simpleview_html = _load_attr("simpleview_html", "fetch_simpleview_html")
