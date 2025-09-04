from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from dateutil import parser as dtp
import hashlib
from typing import Optional, Dict, Any


def _to_dt_utc(x) -> Optional[datetime]:
    if x is None:
        return None
    if isinstance(x, datetime):
        if x.tzinfo is None:
            return x.replace(tzinfo=timezone.utc)
        return x.astimezone(timezone.utc)
    # assume string
    try:
        dt = dtp.parse(str(x))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


@dataclass
class Event:
    title: str
    start_utc: datetime | str
    end_utc: Optional[datetime | str] = None
    description: Optional[str] = None
    url: Optional[str] = None
    location: Optional[str] = None
    source_name: Optional[str] = None
    calendar: Optional[str] = None
    source_url: Optional[str] = None
    meta: Dict[str, Any] = field(default_factory=dict)

    uid: str = field(init=False)

    def __post_init__(self):
        su = _to_dt_utc(self.start_utc)
        eu = _to_dt_utc(self.end_utc) if self.end_utc else None
        self.start_utc = su
        self.end_utc = eu

        base = f"{self.source_name or ''}|{self.title or ''}|{self.start_utc.isoformat() if self.start_utc else ''}|{self.url or ''}"
        self.uid = hashlib.sha1(base.encode("utf-8")).hexdigest() + "@northwoods-v2"
