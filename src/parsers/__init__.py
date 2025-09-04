"""
Exports parser entrypoints with a consistent 3-arg signature:
    fetch_<type>(source: dict, start_date: str, end_date: str) -> list[dict]

This matches how src.main invokes the parsers.
"""

from .tec_rest import fetch_tec_rest  # existing and working

# Non-REST handlers fixed to accept (source, start_date, end_date)
from .tec_html import fetch_tec_html
from .growthzone_html import fetch_growthzone_html
from .simpleview_html import fetch_simpleview_html

__all__ = [
    "fetch_tec_rest",
    "fetch_tec_html",
    "fetch_growthzone_html",
    "fetch_simpleview_html",
]
