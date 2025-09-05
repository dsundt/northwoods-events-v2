# src/parsers/__init__.py
# Minimal, explicit exports to avoid dynamic import surprises.

from .tec_rest import fetch_tec_rest
from .tec_html import fetch_tec_html
from .growthzone_html import fetch_growthzone_html
from .simpleview_html import fetch_simpleview_html

__all__ = [
    "fetch_tec_rest",
    "fetch_tec_html",
    "fetch_growthzone_html",
    "fetch_simpleview_html",
]
