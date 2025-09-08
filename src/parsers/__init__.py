# src/parsers/__init__.py
from __future__ import annotations

from typing import Callable, Dict, Any, List, Optional, Iterable, Tuple
import importlib
import re
import urllib.request

# ------------------------------------------------------------
# Utility: import resolution + safe wrapping to always return list[dict]
# ------------------------------------------------------------
def _stub_fetcher(name: str) -> Callable[..., List[dict]]:
    def _stub(url: str, *args: Any, **kwargs: Any) -> List[dict]:
        print(f"[parsers] STUB for {name} url={url}")
        return []
    return _stub

def _wrap_fetcher(name: str, fn: Optional[Callable[..., Any]]) -> Callable[..., List[dict]]:
    if fn is None:
        return _stub_fetcher(name)

    def _wrapped(*args: Any, **kwargs: Any) -> List[dict]:
        res = fn(*args, **kwargs)
        if res is None:
            return []
        if isinstance(res, tuple):
            # Accept common (events, diag) pattern
            for part in res:
                if isinstance(part, list):
                    return part
            return []
        if isinstance(res, list):
            return res
        if isinstance(res, Iterable):
            try:
                return list(res)
            except Exception:
                pass
        raise TypeError(f"Fetcher {name} returned non-list: {type(res)}")
    return _wrapped

def _try_import_module(*module_names: str) -> Tuple[Optional[Any], Optional[str]]:
    errors: List[str] = []
    for mod in module_names:
        try:
            return importlib.import_module(mod), None
        except Exception as e:
            errors.append(f"{mod}: {e}")
    return None, " | ".join(errors)

def _resolve_attr(mod: Any, *attr_names: str) -> Optional[Callable[..., Any]]:
    for nm in attr_names:
        fn = getattr(mod, nm, None)
        if callable(fn):
            return fn
    return None

# ------------------------------------------------------------
# Built-in minimal ICS parser (fallback when no module exists)
# ------------------------------------------------------------
def _ics_unfold(text: str) -> str:
    # RFC 5545 line folding (continuations start with space or tab)
    lines = text.splitlines()
    out: List[str] = []
    for ln in lines:
        if ln.startswith((" ", "\t")) and out:
            out[-1] += ln.lstrip()
        else:
            out.append(ln)
    return "\n".join(out)

_ICS_DT_RE = re.compile(r"^(DTSTART|DTEND)(?:;[^:]+)?:([\dTzZ]+)$", re.I | re.M)

def _ics_parse_dt(value: str) -> Optional[str]:
    v = value.strip().upper()
    # Supported: YYYYMMDD or YYYYMMDDTHHMMSSZ (or without Z)
    if len(v) == 8 and v.isdigit():
        # all-day date
        return f"{v[0:4]}-{v[4:6]}-{v[6:8]} 00:00:00"
    m = re.match(r"^(\d{8})T(\d{6})(Z)?$", v)
    if m:
        ymd, hms, _ = m.groups()
        return f"{ymd[0:4]}-{ymd[4:6]}-{ymd[6:8]} {hms[0:2]}:{hms[2:4]}:{hms[4:6]}"
    return None

def _fallback_fetch_ics(url: str, *args: Any, **kwargs: Any) -> List[dict]:
    try:
        with urllib.request.urlopen(url) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        print(f"[parsers] fallback ICS fetch error: {e}")
        return []

    txt = _ics_unfold(raw)
    # Split VEVENT blocks
    blocks = re.findall(r"BEGIN:VEVENT(.*?)END:VEVENT", txt, re.S | re.I)
    events: List[dict] = []
    for blk in blocks:
        def get(prop: str) -> Optional[str]:
            # Match property (with optional params)
            m = re.search(rf"^{prop}(?:;[^:]+)?:([^\n\r]+)$", blk, re.I | re.M)
            return m.group(1).strip() if m else None

        summary = get("SUMMARY")
        uid = get("UID") or (summary or "")[:64]
        urlp = get("URL") or get("X-ALT-DESC")  # sometimes URL only in description
        loc = get("LOCATION")
        # Dates
        sdt = None
        edt = None
        for name, val in re.findall(r"^(DTSTART|DTEND)(?:;[^:]+)?:([^\r\n]+)$", blk, re.I | re.M):
            parsed = _ics_parse_dt(val)
            if name.upper() == "DTSTART":
                sdt = sdt or parsed
            else:
                edt = edt or parsed

        if summary:
            events.append({
                "uid": uid,
                "title": summary,
                "start_utc": sdt,
                "end_utc": edt,
                "url": urlp,
                "location": loc,
            })
    return events

# ------------------------------------------------------------
# GrowthZone HTML
# ------------------------------------------------------------
_fetch_growthzone = None
try:
    from .growthzone_html import fetch_growthzone_html as _fetch_growthzone
except Exception as e:
    print(f"[parsers] import error growthzone_html.fetch_growthzone_html: {e}")

# ------------------------------------------------------------
# Simpleview HTML
# ------------------------------------------------------------
_fetch_simpleview = None
try:
    from .simpleview_html import fetch_simpleview_html as _fetch_simpleview
except Exception as e:
    print(f"[parsers] import error simpleview_html.fetch_simpleview_html: {e}")

# ------------------------------------------------------------
# TEC REST
# ------------------------------------------------------------
_fetch_tec_rest = None
_tec_rest_mod, _tec_rest_err = _try_import_module("src.tec_rest", "src.parsers.tec_rest", "tec_rest")
if _tec_rest_mod:
    _fetch_tec_rest = _resolve_attr(_tec_rest_mod, "fetch_tec_rest")
else:
    print(f"[parsers] import error tec_rest.fetch_tec_rest: {_tec_rest_err}")

# ------------------------------------------------------------
# TEC HTML (some sites expose TEC without REST)
# ------------------------------------------------------------
_fetch_tec_html = None
_tec_html_mod, _tec_html_err = _try_import_module("src.tec_html", "src.parsers.tec_html", "tec_html")
if _tec_html_mod:
    _fetch_tec_html = _resolve_attr(_tec_html_mod, "fetch_tec_html", "fetch_tec", "fetch_html")
else:
    # It's okay if not present; provide a stub so imports succeed.
    print(f"[parsers] import error tec_html.fetch_tec_html: {_tec_html_err}")

# ------------------------------------------------------------
# ICS (prefer repo implementation; else fallback above)
# ------------------------------------------------------------
_fetch_ics = None
_ics_mod, _ics_errs = _try_import_module("src.ics_fetch", "ics_fetch", "src.icsbuild", "icsbuild")
if _ics_mod:
    _fetch_ics = _resolve_attr(_ics_mod, "fetch_ics_feed", "fetch_ics", "fetch_feed", "fetch")
    if _fetch_ics is None:
        print("[parsers] import error ics module found but no fetch fn (tried: fetch_ics_feed, fetch_ics, fetch_feed, fetch)")
else:
    print(f"[parsers] import error ics_fetch.fetch_ics_feed: {_ics_errs}")
# If no module, use built-in fallback
if _fetch_ics is None:
    _fetch_ics = _fallback_fetch_ics

# ------------------------------------------------------------
# Public registry + accessors
# ------------------------------------------------------------
FETCHERS: Dict[str, Callable[..., List[dict]]] = {
    "tec_rest": _wrap_fetcher("tec_rest.fetch_tec_rest", _fetch_tec_rest),
    "tec_html": _wrap_fetcher("tec_html.fetch_tec_html", _fetch_tec_html),
    "growthzone_html": _wrap_fetcher("growthzone_html.fetch_growthzone_html", _fetch_growthzone),
    "simpleview_html": _wrap_fetcher("simpleview_html.fetch_simpleview_html", _fetch_simpleview),
    # support both keys for YAML
    "ics_fetch": _wrap_fetcher("ics_fetch.fetch_ics_feed", _fetch_ics),
    "ics_feed": _wrap_fetcher("ics_fetch.fetch_ics_feed", _fetch_ics),
}

def get_fetcher(source_type: str) -> Callable[..., List[dict]]:
    try:
        return FETCHERS[source_type]
    except KeyError:
        raise ValueError(f"Unsupported source type: {source_type}")

# ------------------------------------------------------------
# Back-compat named exports expected by main.py
# ------------------------------------------------------------
def fetch_tec_rest(url: str, *args: Any, **kwargs: Any) -> List[dict]:
    return FETCHERS["tec_rest"](url, *args, **kwargs)

def fetch_tec_html(url: str, *args: Any, **kwargs: Any) -> List[dict]:
    return FETCHERS["tec_html"](url, *args, **kwargs)

def fetch_growthzone_html(url: str, *args: Any, **kwargs: Any) -> List[dict]:
    return FETCHERS["growthzone_html"](url, *args, **kwargs)

def fetch_simpleview_html(url: str, *args: Any, **kwargs: Any) -> List[dict]:
    return FETCHERS["simpleview_html"](url, *args, **kwargs)

def fetch_ics_feed(url: str, *args: Any, **kwargs: Any) -> List[dict]:
    key = "ics_fetch" if "ics_fetch" in FETCHERS else "ics_feed"
    return FETCHERS[key](url, *args, **kwargs)

__all__ = [
    "FETCHERS",
    "get_fetcher",
    "fetch_tec_rest",
    "fetch_tec_html",
    "fetch_growthzone_html",
    "fetch_simpleview_html",
    "fetch_ics_feed",
]
