# Expose fetchers for main.py
from .tec_rest import fetch_tec_rest
from .growthzone_html import fetch_growthzone_html
from .simpleview_html import fetch_simpleview_html

__all__ = [
    "fetch_tec_rest",
    "fetch_growthzone_html",
    "fetch_simpleview_html",
]
