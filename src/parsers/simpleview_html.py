from __future__ import annotations
import json
import re
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup
from dateutil import parser as dtparse

DETAIL_ALLOW = re.compile(r"/(event|events)/[^/?#]+/?$", re.I)
DETAIL_BLOCKLIST = (
    "/events/",
    "/events/this-weekend/",
    "/events/annual-events/",
    "/events/categories/",
    "/events/search/",
)

def fetch_simpleview_html(source: Dict[str, Any], start_date: str, end_date: str) -> List[Dict[str, Any]]:
    base = source.get("url", "").rstrip("/")
    tz = ZoneInfo(source.get("timezone", "America/Chicago"))
    name = source.get("name") or source.get("id") or "Calendar"
    out: List[Dict[str, Any]] = []

    # 1) Gather candidate detail links from the listing page
    try:
        html = requests.get(base, timeout=25).text
        soup = BeautifulSoup(html, "html.parser")
        links = []
        for a in soup.find_all("a", href=True):
            href = a["href"]
            url = href if href.startswith("http") else f"{base.rstrip('/')}/{href.lstrip('/')}"
            path_l = url.lower()
            if any(path_l.endswith(b) or b in path_l for b in DETAIL_BLOCKLIST):
                continue
            if DETAIL_ALLOW.search(url):
                links.append(url)
        # de-dupe + cap
        uniq = []
        seen = set()
        for u in links:
            if u not in seen:
                seen.add(u)
                uniq.append(u)
        links = uniq[:120]
    except Exception:
        links = []

    # 2) Visit detail pages and accept only real JSON-LD Events with startDate
    for link in links:
        ev = _extract_simpleview_event(link, name, tz)
        if ev:
            out.append(ev)

    return out


def _extract_simpleview_event(url: str, calendar_name: str, tz: ZoneInfo) -> Optional[Dict[str, Any]]:
    try:
        resp = requests.get(url, timeout=25)
        if resp.status_code != 200:
            return None
        soup = BeautifulSoup(resp.text, "html.parser")

        # Prefer JSON-LD (Event with startDate)
        for tag in soup.find_all("script", type="application/ld+json"):
            data = None
            try:
                data = json.loads(tag.string or "{}")
            except Exception:
                continue

            candidates = []
            if isinstance(data, dict):
                if data.get("@type") == "Event":
                    candidates = [data]
                elif "@graph" in data and isinstance(data["@graph"], list):
                    candidates = [x for x in data["@graph"] if isinstance(x, dict) and x.get("@type") == "Event"]
            elif isinstance(data, list):
                candidates = [x for x in data if isinstance(x, dict) and x.get("@type") == "Event"]

            for ev in candidates:
                st = _safe_dt(ev.get("startDate"), tz)
                if not st:
                    continue
                en = _safe_dt(ev.get("endDate"), tz) or (st + timedelta(hours=1))
                title = (ev.get("name") or "").strip()
                if not title:
                    # avoid heading pages
                    continue
                loc = _ld_loc(ev)
                return {
                    "uid": f"{url}@northwoods-v2",
                    "title": title,
                    "start_utc": st.strftime("%Y-%m-%d %H:%M:%S"),
                    "end_utc": en.strftime("%Y-%m-%d %H:%M:%S") if en else None,
                    "url": url,
                    "location": loc,
                    "source": calendar_name,
                    "calendar": calendar_name,
                }

        # If no JSON-LD event, skip (prevents grabbing landing pages/headings)
        return None
    except Exception:
        return None


# ---------- local helpers ----------

def _safe_dt(raw: Optional[str], tz: ZoneInfo) -> Optional[datetime]:
    if not raw:
        return None
    try:
        dt = dtparse.parse(raw)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=tz)
        return dt.astimezone(ZoneInfo("UTC"))
    except Exception:
        return None

def _ld_loc(ev: Dict[str, Any]) -> Optional[str]:
    loc = ev.get("location")
    if isinstance(loc, dict):
        nm = (loc.get("name") or "").strip()
        adr = loc.get("address")
        adr_txt = ""
        if isinstance(adr, dict):
            adr_txt = ", ".join([adr.get("streetAddress") or "", adr.get("addressLocality") or "", adr.get("addressRegion") or "", adr.get("postalCode") or ""]).strip(", ")
        return ", ".join([p for p in [nm, adr_txt] if p])
    if isinstance(loc, str):
        return loc.strip()
    return None
