# src/parsers/__init__.py
"""
Unified exports for parser entrypoints. This keeps main.py stable and ensures
every fetch_* function accepts the same signature:
    fetch_*(source: dict, start_date: str, end_date: str) -> list[dict]
"""

from importlib import import_module

__all__ = [
    "fetch_tec_rest",
    "fetch_tec_html",
    "fetch_growthzone_html",
    "fetch_simpleview_html",
]

def _load(module_name, func_name):
    mod = import_module(f"src.parsers.{module_name}")
    fn = getattr(mod, func_name, None)
    if fn is None:
        raise ImportError(
            f"Failed to expose '{func_name}' from parsers.{module_name}: "
            f"module 'src.parsers.{module_name}' has no attribute '{func_name}'"
        )
    return fn

# Export callables with consistent names
fetch_tec_rest = _load("tec_rest", "fetch_tec_rest")
fetch_tec_html = _load("tec_html", "fetch_tec_html")
fetch_growthzone_html = _load("growthzone_html", "fetch_growthzone_html")
fetch_simpleview_html = _load("simpleview_html", "fetch_simpleview_html")
