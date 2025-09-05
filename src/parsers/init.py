# src/parsers/__init__.py
"""
Unified export surface for parser callables.

Each callable MUST use the signature:
    fetch_*(source: dict, start_date: str, end_date: str) -> list[dict]

Where each dict is a normalized event with (at minimum):
    {
      "uid": str,
      "title": str,
      "start_utc": str,     # "YYYY-MM-DD HH:MM:SS"
      "end_utc": str | None,
      "url": str | None,
      "location": str | None,
      "source": str,        # human-friendly name
      "calendar": str       # usually same as source
    }
"""

from importlib import import_module

__all__ = [
    "fetch_tec_rest",
    "fetch_tec_html",
    "fetch_growthzone_html",
    "fetch_simpleview_html",
]

def _export(name: str, module: str, attr: str) -> None:
    mod = import_module(f"src.parsers.{module}")
    fn = getattr(mod, attr, None)
    if fn is None:
        raise ImportError(
            f"Failed to expose '{attr}' from parsers.{module}: "
            f"module 'src.parsers.{module}' has no attribute '{attr}'"
        )
    globals()[name] = fn

# Make sure each binding points to the *correct* module/attr.
_export("fetch_tec_rest", "tec_rest", "fetch_tec_rest")
_export("fetch_tec_html", "tec_html", "fetch_tec_html")
_export("fetch_growthzone_html", "growthzone_html", "fetch_growthzone_html")
_export("fetch_simpleview_html", "simpleview_html", "fetch_simpleview_html")
