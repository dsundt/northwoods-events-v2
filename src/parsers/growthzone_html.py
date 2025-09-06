from __future__ import annotations
import json
import re
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup
from dateutil import parser as dtparse

DETAIL_RX = re.compile(r"/events/details/[^/?#]+", re.I)

def fetch_growthzone_html(source: Dict[str, Any], start_date: str, end_date: str) -> List[Dict[str, Any]]:
    base = source.get("url", "").rstrip("/")
    tz = ZoneInfo(source.get("timezone", "America/Chicago"))
    name = source.get("name") or source.get("id") or "Calendar"
    out: List[Dict[str, Any]] = []

    # 1) load listing and collect only proper detail links
    try:
        html = requests.get(base, timeout=25).text
        soup = BeautifulSoup(html, "html.parser")
        detail_links = []
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if href.startswith("http"):
                url = href
            else:
                url = f"{base.rstrip('/')}/{href.lstrip('/')}"
            if DETAIL_RX.search(url):
                detail_links.append(url)
        # de-dupe and cap (avoid hammering)
        seen = set()
        detail_links_uni = []
        for u in detail_links:
            if u not in seen:
                seen.add(u)
                detail_links_uni.append(u)
        detail_links = detail_links_uni[:120]
    except Exception:
        detail_links = []

    # 2) visit details and extract robustly
    for link in detail_links:
        ev = _parse_growthzone_detail(link, name, tz)
        if ev and ev.get("start_utc"):
            out.append(ev)

    return out


def _parse_growthzone_detail(url: str, calendar_name: str, tz: ZoneInfo) -> Optional[Dict[str, Any]]:
    try:
        resp = requests.get(url, timeout=25)
        if resp.status_code != 200:
            return None
        soup = BeautifulSoup(resp.text, "html.parser")

        # a) Prefer JSON-LD event with parseable startDate
        for tag in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(tag.string or "{}")
            except Exception:
                continue
            # could be dict or list
            candidates = []
            if isinstance(data, list):
                candidates = [x for x in data if isinstance(x, dict)]
            elif isinstance(data, dict):
                if data.get("@type") == "Event":
                    candidates = [data]
                elif "@graph" in data and isinstance(data["@graph"], list):
                    candidates = [x for x in data["@graph"] if isinstance(x, dict) and x.get("@type") == "Event"]
            for ev in candidates:
                st = _safe_dt(ev.get("startDate"), tz)
                if not st:
                    continue
                en = _safe_dt(ev.get("endDate"), tz) or (st + timedelta(hours=1))
                loc = _ld_loc(ev)
                title = (ev.get("name") or "").strip()
                if title:
                    return {
                        "uid": f"{url}@northwoods-v2",
                        "title": title,
                        "start_utc": st.strftime("%Y-%m-%d %H:%M:%S"),
                        "end_utc": en.strftime("%Y-%m-%d %H:%M:%S"),
                        "url": url,
                        "location": loc,
                        "source": calendar_name,
                        "calendar": calendar_name,
                    }

        # b) Fallback to label-based scrape (Date/Time/Location)
        title = _text_or_none(soup.select_one("h1, h2, .event-title, .Title"))
        date_text = _labeled_value(soup, r"^\s*Date\s*:")  # "Date: September 27, 2025"
        time_text = _labeled_value(soup, r"^\s*Time\s*:")  # "Time: 11:00 AM - 4:00 PM CDT"
        # Some sites put combined "Date and Time"
        if not date_text and not time_text:
            combo = _labeled_value(soup, r"^\s*Date\s*/?\s*Time\s*:") or _labeled_value(soup, r"^\s*Date and Time\s*:")
            if combo:
                # try splitting
                m = re.search(r"^(.+?)\s+(?:\|\s+)?(\d{1,2}:\d{2}\s*[AP]M.*)$", combo)
                if m:
                    date_text, time_text = m.group(1), m.group(2)
                else:
                    date_text = combo

        start_dt, end_dt = _compose_dt(date_text, time_text, tz)
        if not start_dt:
            return None

        loc = _location_block(soup)

        return {
            "uid": f"{url}@northwoods-v2",
            "title": (title or "Event").strip(),
            "start_utc": start_dt.strftime("%Y-%m-%d %H:%M:%S"),
            "end_utc": end_dt.strftime("%Y-%m-%d %H:%M:%S") if end_dt else None,
            "url": url,
            "location": loc,
            "source": calendar_name,
            "calendar": calendar_name,
        }
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

def _compose_dt(date_text: Optional[str], time_text: Optional[str], tz: ZoneInfo) -> (Optional[datetime], Optional[datetime]):
    if not date_text:
        return None, None
    date_text = date_text.strip()
    st_dt_local = None
    en_dt_local = None

    # Times like "11:00 AM - 4:00 PM CDT"
    if time_text:
        time_text = re.sub(r"\s+CDT|CST|CT\b", "", time_text, flags=re.I).strip()
        rng = re.split(r"\s*-\s*", time_text)
        try:
            st_dt_local = dtparse.parse(f"{date_text} {rng[0]}")
        except Exception:
            st_dt_local = None
        if st_dt_local is not None and st_dt_local.tzinfo is None:
            st_dt_local = st_dt_local.replace(tzinfo=tz)
        if len(rng) > 1:
            try:
                en_dt_local = dtparse.parse(f"{date_text} {rng[1]}")
                if en_dt_local.tzinfo is None:
                    en_dt_local = en_dt_local.replace(tzinfo=tz)
            except Exception:
                en_dt_local = None

    if not st_dt_local:
        try:
            st_dt_local = dtparse.parse(date_text)
            if st_dt_local.tzinfo is None:
                st_dt_local = st_dt_local.replace(tzinfo=tz)
        except Exception:
            return None, None

    if not en_dt_local and st_dt_local:
        en_dt_local = st_dt_local + timedelta(hours=1)

    return st_dt_local.astimezone(ZoneInfo("UTC")), (en_dt_local.astimezone(ZoneInfo("UTC")) if en_dt_local else None)

def _labeled_value(soup: BeautifulSoup, label_rx: str) -> Optional[str]:
    rx = re.compile(label_rx, re.I)
    # Find a node that contains "Label:" and read the immediate following text
    for el in soup.find_all(text=rx):
        # Typical structure: <strong>Date:</strong> September 27, 2025
        parent = el.parent
        if parent:
            # Grab tail text of label node and siblings up to a break
            texts = []
            for sib in parent.next_siblings:
                if getattr(sib, "name", "").lower() in {"br", "hr"}:
                    break
                t = getattr(sib, "get_text", lambda: str(sib))()
                t = t.strip()
                if t:
                    texts.append(t)
            if texts:
                return " ".join(texts).strip()
    return None

def _location_block(soup: BeautifulSoup) -> Optional[str]:
    # Look for "Location:" label, then collect tight block text only
    val = _labeled_value(soup, r"^\s*Location\s*:")
    if val:
        # collapse multiple lines into a concise single-line location
        val = re.sub(r"\s+", " ", val)
        return val.strip()
    # Fallback: microdata
    cand = soup.select_one('[itemprop="location"]')
    if cand:
        txt = cand.get_text(" ", strip=True)
        return re.sub(r"\s+", " ", txt)
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

def _text_or_none(tag) -> Optional[str]:
    if not tag:
        return None
    return tag.get_text(strip=True) or None
