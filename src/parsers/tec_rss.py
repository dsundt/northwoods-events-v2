from __future__ import annotations

"""RSS parser for The Events Calendar feeds."""

import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from bs4 import BeautifulSoup
from dateutil import parser as dtparse

from src.fetch import session


def _local(tag: str) -> str:
    """Return the local part of an XML tag, dropping namespace prefixes."""

    if "}" in tag:
        tag = tag.split("}", 1)[1]
    if ":" in tag:
        tag = tag.split(":", 1)[1]
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


def _harvest_fields(item: ET.Element) -> Dict[str, str]:
    fields: Dict[str, str] = {}

    def _aliases(name: str) -> List[str]:
        lowered = name.lower()
        alts = {lowered}
        cleaned = lowered.replace("-", " ").replace("_", " ")
        if cleaned != lowered:
            alts.add(cleaned.replace(" ", ""))
            alts.add(cleaned.replace(" ", "_"))
        alts.add(lowered.replace("-", ""))
        alts.add(lowered.replace("_", ""))
        return [alias for alias in alts if alias]

    for child in list(item):
        name = _local(child.tag)
        if not name:
            continue
        text = (child.text or "").strip()
        if not text:
            text = (child.attrib.get("value") or child.attrib.get("content") or "").strip()
        if not text:
            text = " ".join((child.text or "", "".join(grand.text or "" for grand in child)))
        text = text.strip()
        if not text:
            continue

        for alias in _aliases(name):
            fields.setdefault(alias, text)
    return fields


def _date_time_from_fields(fields: Dict[str, str], tz_name: Optional[str], *candidates: str) -> Tuple[Optional[str], Optional[str]]:
    """Return combined datetime string + raw source used (for diagnostics)."""

    def _try_keys(keys: Tuple[str, ...]) -> Optional[str]:
        for key in keys:
            if key in fields:
                result = _coerce_dt(fields[key], tz_name)
                if result:
                    return result
        return None

    lowered = [c.lower() for c in candidates]

    # Direct matches that already contain full datetimes (dtstart, start_utc, etc.).
    direct_first = tuple(
        key for key in lowered if not key.endswith("date") and not key.endswith("time")
    )
    direct = _try_keys(direct_first)
    if direct:
        return direct, None

    # TEC feeds often split date/time into separate elements (startdate/starttime).
    for candidate in lowered:
        base = candidate
        for suffix in ("date", "_date", "-date"):
            if base.endswith(suffix):
                base = base[: -len(suffix)]
                break

        date_keys = (
            f"{base}date",
            f"{base}_date",
            f"{base}-date",
            candidate if candidate.endswith("date") else "",
        )
        time_keys = (
            f"{base}time",
            f"{base}_time",
            f"{base}-time",
            candidate if candidate.endswith("time") else "",
        )

        date_text = None
        for key in date_keys:
            if key and key in fields:
                date_text = fields[key]
                break

        time_text = None
        for key in time_keys:
            if key and key in fields:
                time_text = fields[key]
                break

        if date_text:
            combined = date_text
            if time_text:
                combined = f"{combined} {time_text}"
            dt = _coerce_dt(combined, tz_name)
            if dt:
                return dt, combined

    # Last-ditch fallback to publication timestamps and raw date-only fields.
    remaining_direct = tuple(key for key in lowered if key.endswith("date"))
    direct = _try_keys(remaining_direct)
    if direct:
        return direct, None

    pub = _try_keys(("pubdate", "published", "updated", "dc:date"))
    if pub:
        return pub, None

    return None, None


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
    except Exception as exc:
        source.setdefault("_fetch_meta", {}).setdefault("warnings", []).append(
            f"tec_rss request failed: {exc}"
        )
        return []

    try:
        root = ET.fromstring(resp.text)
    except Exception as exc:
        source.setdefault("_fetch_meta", {}).setdefault("warnings", []).append(
            f"tec_rss feed parse failed: {exc}"
        )
        return []

    channel = root.find("channel") or root
    items = list(channel.findall("item"))

    events: List[Dict] = []

    for item in items:
        title = _clean_text(item.findtext("title")) or "(untitled event)"
        link = (item.findtext("link") or source.get("calendar") or url)

        desc_raw = _find_text(item, "encoded") or item.findtext("description")
        description = _clean_text(desc_raw)

        fields = _harvest_fields(item)

        feed_tz = fields.get("timezone") or fields.get("tz") or fields.get("eventtimezone")
        item_tz = feed_tz or tz_name

        start, start_source = _date_time_from_fields(
            fields,
            item_tz,
            "start_utc",
            "dtstart",
            "startdate",
            "start_date",
            "start",
        )
        end, _ = _date_time_from_fields(
            fields,
            item_tz,
            "end_utc",
            "dtend",
            "enddate",
            "end_date",
            "end",
        )

        if not start and description:
            # Attempt to discover an ISO-like timestamp in the body as a fallback
            match = re.search(r"(\d{4}-\d{2}-\d{2}(?:[T\s]\d{2}:\d{2}(?::\d{2})?)?)", description)
            if match:
                start = _coerce_dt(match.group(1), item_tz)
                start_source = match.group(1)
        if not start:
            source.setdefault("_fetch_meta", {}).setdefault("warnings", []).append(
                f"tec_rss skipped '{title}' due to missing start time"
            )
            continue

        start_dt = _to_utc(start)
        if start_date and start_dt and start_dt < start_date:
            continue
        if end_date and start_dt and start_dt > end_date:
            continue

        location = fields.get("location") or _extract_location(item, description)

        event = {
            "title": title,
            "start_utc": start,
            "end_utc": end,
            "url": link,
            "description": description,
            "location": location,
            "calendar": calendar_name,
        }

        if start_source and start_source != start:
            event.setdefault("_meta", {})["start_source"] = start_source

        events.append(event)

    return events
