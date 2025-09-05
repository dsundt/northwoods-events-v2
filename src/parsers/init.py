# src/parsers/__init__.py
"""
Stable export surface for all parsers.

This module exposes a consistent function signature for each parser:

    fetch_tec_rest(url: str, start_date: str, end_date: str) -> list[dict]
    fetch_tec_html(url: str, start_date: str, end_date: str) -> list[dict]
    fetch_growthzone_html(url: str, start_date: str, end_date: str) -> list[dict]
    fetch_simpleview_html(url: str, start_date: str, end_date: str) -> list[dict]

All functions MUST exist and accept exactly three positional args, even if a
specific parser ignores dates internally. This keeps main.py simple & robust.
"""

from .tec_rest import fetch_tec_rest, fetch_tec_html
from .growthzone_html import fetch_growthzone_html
from .simpleview_html import fetch_simpleview_html

__all__ = [
    "fetch_tec_rest",
    "fetch_tec_html",
    "fetch_growthzone_html",
    "fetch_simpleview_html",
]
