# src/parsers/__init__.py

from .tec_rest import fetch_tec_rest, TEC_DEFAULT_WINDOW_DAYS
from .tec_html import fetch_tec_html
from .growthzone_html import fetch_growthzone_html
from .simpleview_html import fetch_simpleview_html

__all__ = [
    "fetch_tec_rest",
    "TEC_DEFAULT_WINDOW_DAYS",
    "fetch_tec_html",
    "fetch_growthzone_html",
    "fetch_simpleview_html",
]
