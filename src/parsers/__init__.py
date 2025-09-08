# src/parsers/__init__.py
from __future__ import annotations

from typing import Callable, Dict, Any, List
import importlib

# -----------------------------
# Helpers
# -----------------------------
def _stub_fetcher(name: str) -> Callable[..., List[dict]]:
    def _stub(url: str, *args: Any, **kwargs: Any) -> List[dict]:
        print(f"[parsers] STUB for {name} url={url}")
        return []  # always a list
    return _stub

def _wrap_fetcher(name: str, fn: Callable[..., Any] | None) -> Callable[..., List[dict]]:
    """
    Wrap a parser so callers always get List[dict].
    - Accepts (events, diag) -> returns events
    - None -> []
    - list -> list
    - generator/iterable -> list(...)
    - Anything else -> TypeError
    """
    if fn is None:
        return _stub_fetcher(name)

    def _wrapped(*args: Any, **kwargs: Any) -> List[dict]:
        res = fn(*args, **kwargs)
        if res is None:
            return []
        if isinstance(res, tuple):
            # favor first list-like element
            for part in res:
                if isinstance(part, list):
                    return part
            return []
        if isinstance(res, list):
            return res
        try:
            return list(res)
        except Exception as e:
            raise TypeError(f"Fetcher {name} returned non-list: {type(res)}") from e
    return _wrapped

def _try_import_module(*module_names: str):
    errors: List[str] = []
    for mod in module_names:
        try:
            return importlib.import_module(mod), None
        except Exception as e:
            errors.append(f"{mod}: {e}")
    return None, " | ".join(errors)

def _resolve_attr(mod, *attr_names: str):
    for nm in attr_names:
        fn = getattr(mod, nm, None)
        if callable(fn):
            return fn
    return None

# -----------------------------
# GrowthZone HTML
# -----------------------------
_fetch_growthzone = None
try:
    from .growthzone_html import fetch_growthzone_html as _fetch_growthzone  # local package layout
except Exception as e:
    print(f"[parsers] import error growthzone_html.fetch_growthzone_html: {e}")

# -----------------------------
# Simpleview HTML
# -----------------------------
_fetch_simpleview = None
try:
    from .simpleview_html import fetch_simpleview_html as _fetch_simpleview
except Exception as e:
    print(f"[parsers] import error simpleview_html.fetch_simpleview_html: {e}")

# -----------------------------
# TEC REST
# -----------------------------
_fetch_tec_rest = None
_tec_mod, _tec_errs = _try_import_module("src.tec_rest", "src.parsers.tec_rest", "tec_rest")
if _tec_mod:
    _fetch_tec_rest = _resolve_attr(_tec_mod, "fetch_tec_rest")
else:
    print(f"[parsers] import error tec_rest.fetch_tec_rest: {_tec_errs}")

# -----------------------------
# ICS fetcher (robust resolution)
# -----------------------------
_fetch_ics = None
_ics_mod, _ics_errs = _try_import_module("src.ics_fetch", "ics_fetch", "src.icsbuild", "icsbuild")
if _ics_mod:
    # try a few common function names
    _fetch_ics = _resolve_attr(
        _ics_mod,
        "fetch_ics_feed", "fetch_ics", "fetch_feed", "fetch"
    )
    if _fetch_ics is None:
        print("[parsers] import error ics_fetch: module found but no fetch function (tried: fetch_ics_feed, fetch_ics, fetch_feed, fetch)")
else:
    print(f"[parsers] import error ics_fetch.fetch_ics_feed: {_ics_errs}")

# -----------------------------
# Public fetcher map
# -----------------------------
FETCHERS: Dict[str, Callable[..., List[dict]]] = {
    "tec_rest": _wrap_fetcher("tec_rest.fetch_tec_rest", _fetch_tec_rest),
    "growthzone_html": _wrap_fetcher("growthzone_html.fetch_growthzone_html", _fetch_growthzone),
    "simpleview_html": _wrap_fetcher("simpleview_html.fetch_simpleview_html", _fetch_simpleview),
    # Support both names in YAML
    "ics_fetch": _wrap_fetcher("ics_fetch.fetch_ics_feed", _fetch_ics),
    "ics_feed": _wrap_fetcher("ics_fetch.fetch_ics_feed", _fetch_ics),
}

def get_fetcher(source_type: str) -> Callable[..., List[dict]]:
    try:
        return FETCHERS[source_type]
    except KeyError:
        raise ValueError(f"Unsupported source type: {source_type}")

# -----------------------------
# Back-compat named exports expected by main.py
# (pass-throughs that still normalize to List[dict])
# -----------------------------
def fetch_tec_rest(url: str, *args: Any, **kwargs: Any) -> List[dict]:
    return FETCHERS["tec_rest"](url, *args, **kwargs)

def fetch_growthzone_html(url: str, *args: Any, **kwargs: Any) -> List[dict]:
    return FETCHERS["growthzone_html"](url, *args, **kwargs)

def fetch_simpleview_html(url: str, *args: Any, **kwargs: Any) -> List[dict]:
    return FETCHERS["simpleview_html"](url, *args, **kwargs)

def fetch_ics_feed(url: str, *args: Any, **kwargs: Any) -> List[dict]:
    # prefer the canonical key if present
    key = "ics_fetch" if "ics_fetch" in FETCHERS else "ics_feed"
    return FETCHERS[key](url, *args, **kwargs)

__all__ = [
    "FETCHERS",
    "get_fetcher",
    "fetch_tec_rest",
    "fetch_growthzone_html",
    "fetch_simpleview_html",
    "fetch_ics_feed",
]
