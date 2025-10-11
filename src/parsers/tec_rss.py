from __future__ import annotations

"""RSS parser for The Events Calendar feeds."""

import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Dict, List, Optional

from bs4 import BeautifulSoup
from dateutil import parser as dtparse

from src.fetch import session


def _local(tag: str) -> str:
    """Return the local part of an XML tag."""
    if "}" in tag:
        return tag.split("}", 1)[1]
    return tag


def _clean_text(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    soup = BeautifulSoup(value, "html.parser")
    text = soup.get_text(" ", strip=True)
    return text or None


def _find_text(item: ET.Element, *names: str) -> Optional[str]:
    want = {name.lower() for name in names}
    for child in list(item):
        local = _local(child.tag).lower()
        if local in want:
            text = child.text or ""
            if not text:
                text = "".join(child.itertext())
            text = text.strip()
            if text:
                return text
    return None


def _coerce_dt(value: Optional[str], tz_name: Optional[str]) -> Optional[str]:
    if not value:
        return None
    value = value.strip()
    if not value:
        return None
    try:
        dt = dtparse.parse(value)
    except Exception:
        return None
    if dt.tzinfo is None:
        try:
            from zoneinfo import ZoneInfo

            tz = ZoneInfo(tz_name) if tz_name else timezone.utc
        except Exception:
            tz = timezone.utc
        dt = dt.replace(tzinfo=tz)
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def _find_datetime(item: ET.Element, tz_name: Optional[str], *candidates: str) -> Optional[str]:
    candidate_l = [c.lower() for c in candidates]
    for child in list(item):
        name = _local(child.tag).lower()
        if name in candidate_l:
            text = (child.text or "").strip()
            if not text:
                text = (child.attrib.get("value") or child.attrib.get("content") or "").strip()
            if not text:
                text = " ".join((child.text or "", "".join(grand.text or "" for grand in child)))
            result = _coerce_dt(text, tz_name)
            if result:
                return result
    for child in list(item):
        name = _local(child.tag).lower()
        for key in candidate_l:
            if key in name:
                text = (child.text or "").strip()
                if not text:
                    text = (child.attrib.get("value") or child.attrib.get("content") or "").strip()
                result = _coerce_dt(text, tz_name)
                if result:
                    return result
    return None


def _extract_location(item: ET.Element, description: Optional[str]) -> Optional[str]:
    parts: List[str] = []
    for key in ("location", "venue", "address", "city", "state", "country"):
        for child in list(item):
            name = _local(child.tag).lower()
            if key == name:
                text = _clean_text(child.text) or _clean_text(child.attrib.get("content"))
                if text:
                    parts.append(text)
    if parts:
        seen: set[str] = set()
        uniq: List[str] = []
        for part in parts:
            lower = part.lower()
            if lower in seen:
                continue
            seen.add(lower)
            uniq.append(part)
        return ", ".join(uniq)

    if description:
        match = re.search(r"Location\s*[:\-]\s*(.+?)(?:\s{2,}|$)", description, flags=re.IGNORECASE)
        if match:
            loc = match.group(1).strip()
            loc = re.sub(r"\s+", " ", loc)
            if loc:
                return loc
    return None


def _to_utc(dt_str: str) -> Optional[datetime]:
    try:
        dt = dtparse.parse(dt_str)
    except Exception:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    return dt


def fetch_tec_rss(source: Dict, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> List[Dict]:
    """Parse a The Events Calendar RSS feed into event dictionaries."""
    if not isinstance(source, dict):
        return []

    url = source.get("url")
    if not url:
        return []

    tz_name = source.get("timezone") or "UTC"
    calendar_name = source.get("name")

    sess = session()
    try:
        resp = sess.get(url, timeout=getattr(sess, "timeout", 30))
        resp.raise_for_status()
    except Exception:
        return []

    try:
        root = ET.fromstring(resp.text)
    except Exception:
        return []

    channel = root.find("channel") or root
    items = list(channel.findall("item"))

    events: List[Dict] = []

    for item in items:
        title = _clean_text(item.findtext("title")) or "(untitled event)"
        link = (item.findtext("link") or source.get("calendar") or url)

        desc_raw = _find_text(item, "encoded") or item.findtext("description")
        description = _clean_text(desc_raw)

        start = _find_datetime(item, tz_name, "startdate", "start_date", "dtstart", "start")
        end = _find_datetime(item, tz_name, "enddate", "end_date", "dtend", "end")

        if not start and description:
            match = re.search(r"(\d{4}-\d{2}-\d{2}(?:[T\s]\d{2}:\d{2}(?::\d{2})?)?)", description)
            if match:
                start = _coerce_dt(match.group(1), tz_name)
        if not start:
            continue

        start_dt = _to_utc(start)
        if start_date and start_dt and start_dt < start_date:
            continue
        if end_date and start_dt and start_dt > end_date:
            continue

        location = _extract_location(item, description)

        events.append(
            {
                "title": title,
                "start_utc": start,
                "end_utc": end,
                "url": link,
                "description": description,
                "location": location,
                "calendar": calendar_name,
            }
        )

    return events
