# src/parsers/tec_rest.py
from typing import List, Dict, Any, Optional
from urllib.parse import urljoin, urlparse, urlencode
from datetime import datetime, timedelta
from dateutil import parser as dtp

from src.fetch import get

def _dtstr(dt: Optional[datetime]) -> Optional[str]:
    return dt.strftime("%Y-%m-%d %H:%M:%S") if dt else None

def _rest_base(site_url: str) -> str:
    parsed = urlparse(site_url)
    root = f"{parsed.scheme}://{parsed.netloc}/"
    return urljoin(root, "wp-json/tribe/events/v1/events")

def _make_window(start_utc: Optional[str], end_utc: Optional[str]) -> (str, str):
    now = datetime.utcnow()
    start = dtp.parse(start_utc) if start_utc else now
    end   = dtp.parse(end_utc) if end_utc else (now + timedelta(days=120))
    return start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")

def fetch_tec_rest(url: str, start_utc: str = None, end_utc: str = None) -> List[Dict[str, Any]]:
    api = _rest_base(url)
    start_d, end_d = _make_window(start_utc, end_utc)

    per_page = 50
    page = 1
    events: List[Dict[str, Any]] = []

    while True:
        params = {
            "start_date": start_d,
            "end_date": end_d,
            "per_page": per_page,
            "page": page,
        }
        # IMPORTANT: src.fetch.get() does not support params=...
        r = get(f"{api}?{urlencode(params)}")
        data = r.json()
        objs = data.get("events") or []
        if not objs:
            break

        for ev in objs:
            title = (ev.get("title") or "").strip()
            url_e = ev.get("url") or None
            start_s = ev.get("start_date")
            end_s   = ev.get("end_date")

            try:
                start_dt = dtp.parse(start_s) if start_s else None
            except Exception:
                start_dt = None
            try:
                end_dt = dtp.parse(end_s) if end_s else None
            except Exception:
                end_dt = None

            # Venue normalization
            loc = None
            v = ev.get("venue") or {}
            if isinstance(v, dict):
                parts = [v.get("venue"), v.get("address"), v.get("city"), v.get("state")]
                loc = ", ".join([p for p in parts if p]) or None

            uid = str(ev.get("id") or f"tec-{hash((title, start_s or '', url_e or ''))}")

            events.append({
                "uid": uid,
                "title": title or "Event",
                "start_utc": _dtstr(start_dt),
                "end_utc": _dtstr(end_dt),
                "url": url_e,
                "location": loc,
            })

        if len(objs) < per_page:
            break
        page += 1

    return events
