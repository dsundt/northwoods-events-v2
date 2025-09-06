from __future__ import annotations
import json
import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from typing import List, Dict, Any, Optional

import requests
from bs4 import BeautifulSoup
from dateutil import parser as dtparse

# Public entry point – keep signature as-is
def fetch_tec_html(source: Dict[str, Any], start_date: str, end_date: str) -> List[Dict[str, Any]]:
    """
    Hardened TEC HTML fallback:
    1) Try TEC REST directly (two endpoint shapes).
    2) Try TEC ICS (?ical=1) and parse.
    3) Fallback to HTML + JSON-LD scan.
    """
    base = source.get("url", "").rstrip("/")
    tz = ZoneInfo(source.get("timezone", "America/Chicago"))
    out: List[Dict[str, Any]] = []

    # 1) Try TEC REST on the site domain (non-breaking for other sources)
    rest_params = {
        "start_date": start_date,
        "end_date": end_date,
        "per_page": 50,
        "page": 1,
    }
    for rest_path in ("/wp-json/tribe/events/v1/events", "/?rest_route=/tribe/events/v1/events"):
        try:
            page = 1
            while True:
                rest_params["page"] = page
                resp = requests.get(f"{base}{rest_path}", params=rest_params, timeout=20)
                if resp.status_code != 200:
                    break
                data = resp.json()
                events = data.get("events") or []
                if not events:
                    break
                out.extend(_from_tec_rest_chunk(events, source, tz))
                if not data.get("next_rest_url"):
                    break
                page += 1
            if out:
                return out
        except Exception:
            # fall through to ICS/HTML
            pass

    # 2) Try sitewide ICS export (?ical=1) – many TEC sites provide this
    try:
        ics_url = f"{base}/?ical=1"
        ics = requests.get(ics_url, timeout=20)
        if ics.status_code == 200 and "BEGIN:VCALENDAR" in ics.text:
            out = _from_ics_text(ics.text, source, tz, start_date, end_date)
            if out:
                return out
    except Exception:
        pass

    # 3) Fallback: HTML listing → JSON-LD @type Event
    try:
        html = requests.get(base, timeout=20).text
        out = _from_jsonld_listing(html, source, tz, start_date, end_date)
    except Exception:
        out = []

    return out


# ------ Helpers (local to this file; no new modules introduced) ------

def _from_tec_rest_chunk(events: List[Dict[str, Any]], source: Dict[str, Any], tz: ZoneInfo) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    name = source.get("name") or source.get("id") or "Calendar"
    for e in events:
        try:
            start_raw = e.get("start_date")
            end_raw = e.get("end_date") or start_raw
            start_dt = _as_utc(start_raw, tz)
            end_dt = _as_utc(end_raw, tz)
            if not start_dt:
                continue
            rows.append({
                "uid": f"{e.get('id')}@northwoods-v2",
                "title": (e.get("title") or "").strip(),
                "start_utc": start_dt.strftime("%Y-%m-%d %H:%M:%S"),
                "end_utc": end_dt.strftime("%Y-%m-%d %H:%M:%S"),
                "url": (e.get("url") or "").strip(),
                "location": _clean_location(e.get("venue", {}).get("address") if isinstance(e.get("venue"), dict) else e.get("venue")),
                "source": name,
                "calendar": name,
            })
        except Exception:
            continue
    return rows


def _from_ics_text(text: str, source: Dict[str, Any], tz: ZoneInfo, start_date: str, end_date: str) -> List[Dict[str, Any]]:
    # Minimal ICS parser without extra deps: parse DTSTART/DTEND lines
    # Accept both Zulu and local times; coerce to tz then UTC.
    rows: List[Dict[str, Any]] = []
    name = source.get("name") or source.get("id") or "Calendar"
    # Split by VEVENT
    for block in text.split("BEGIN:VEVENT")[1:]:
        try:
            lines = block.splitlines()
            fields = {}
            for ln in lines:
                if ":" not in ln:
                    continue
                k, v = ln.split(":", 1)
                fields[k.strip()] = v.strip()
            summary = fields.get("SUMMARY", "").strip()
            url = fields.get("URL", "").strip() or fields.get("UID", "").strip()
            loc = fields.get("LOCATION", "").strip() or None
            dtstart = _ics_dt(fields, "DTSTART", tz)
            dtend = _ics_dt(fields, "DTEND", tz) or (dtstart + timedelta(hours=1) if dtstart else None)
            if not dtstart:
                continue
            # window filter
            if not _within_window(dtstart, start_date, end_date, tz):
                continue
            rows.append({
                "uid": f"{fields.get('UID', summary)}@northwoods-v2",
                "title": summary,
                "start_utc": dtstart.astimezone(ZoneInfo("UTC")).strftime("%Y-%m-%d %H:%M:%S"),
                "end_utc": dtend.astimezone(ZoneInfo("UTC")).strftime("%Y-%m-%d %H:%M:%S") if dtend else None,
                "url": url,
                "location": loc,
                "source": name,
                "calendar": name,
            })
        except Exception:
            continue
    return rows


def _from_jsonld_listing(html: str, source: Dict[str, Any], tz: ZoneInfo, start_date: str, end_date: str) -> List[Dict[str, Any]]:
    soup = BeautifulSoup(html, "html.parser")
    name = source.get("name") or source.get("id") or "Calendar"
    rows: List[Dict[str, Any]] = []
    for tag in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(tag.string or "{}")
        except Exception:
            continue
        # Accept either a single Event or a graph
        candidates = []
        if isinstance(data, dict) and data.get("@type") == "Event":
            candidates = [data]
        elif isinstance(data, dict) and "@graph" in data and isinstance(data["@graph"], list):
            candidates = [x for x in data["@graph"] if isinstance(x, dict) and x.get("@type") == "Event"]
        for ev in candidates:
            start_dt = _as_utc(ev.get("startDate"), tz)
            end_dt = _as_utc(ev.get("endDate") or ev.get("endDateTime"), tz) or (start_dt + timedelta(hours=1) if start_dt else None)
            if not start_dt:
                continue
            if not _within_window(start_dt, start_date, end_date, tz):
                continue
            rows.append({
                "uid": f"{ev.get('@id') or ev.get('url') or ev.get('name')}@northwoods-v2",
                "title": (ev.get("name") or "").strip(),
                "start_utc": start_dt.strftime("%Y-%m-%d %H:%M:%S"),
                "end_utc": end_dt.strftime("%Y-%m-%d %H:%M:%S") if end_dt else None,
                "url": (ev.get("url") or "").strip(),
                "location": _extract_ld_location(ev),
                "source": name,
                "calendar": name,
            })
    return rows


def _ics_dt(fields: Dict[str, str], key: str, tz: ZoneInfo) -> Optional[datetime]:
    v = fields.get(key)
    if not v:
        return None
    # Handle VALUE=DATE or date-time; strip params like DTSTART;TZID=America/Chicago
    if ";" in key:
        # not used here (we looked up pure key), but keep placeholder
        pass
    val = v
    try:
        # Zulu?
        if val.endswith("Z"):
            dt = dtparse.parse(val)
        else:
            # Might be local; coerce
            dt = dtparse.parse(val)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=tz)
        return dt.astimezone(ZoneInfo("UTC"))
    except Exception:
        return None


def _within_window(start_dt: datetime, start_date: str, end_date: str, tz: ZoneInfo) -> bool:
    try:
        ws = dtparse.parse(start_date).replace(tzinfo=tz)
        we = dtparse.parse(end_date).replace(tzinfo=tz) + timedelta(days=1)
        return ws <= start_dt <= we
    except Exception:
        return True


def _as_utc(raw: Any, tz: ZoneInfo) -> Optional[datetime]:
    if not raw:
        return None
    try:
        dt = dtparse.parse(str(raw))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=tz)
        return dt.astimezone(ZoneInfo("UTC"))
    except Exception:
        return None


def _clean_location(loc: Any) -> Optional[str]:
    if not loc:
        return None
    if isinstance(loc, dict):
        parts = [
            loc.get("venue"),
            loc.get("address"),
            loc.get("city"),
            loc.get("region"),
            loc.get("postal_code"),
        ]
        return ", ".join([p for p in parts if p])
    return str(loc).strip() or None


def _extract_ld_location(ev: Dict[str, Any]) -> Optional[str]:
    loc = ev.get("location")
    if isinstance(loc, dict):
        nm = loc.get("name")
        adr = loc.get("address")
        adr_str = None
        if isinstance(adr, dict):
            adr_str = ", ".join([adr.get("streetAddress") or "", adr.get("addressLocality") or "", adr.get("addressRegion") or "", adr.get("postalCode") or ""]).strip(", ")
        return ", ".join([p for p in [nm, adr_str] if p])
    if isinstance(loc, str):
        return loc.strip()
    return None
