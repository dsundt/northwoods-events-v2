from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Event:
    uid: str
    title: str
    description: Optional[str]
    url: Optional[str]
    location: Optional[str]
    start_utc: datetime
    end_utc: Optional[datetime]
    source_name: str
    calendar: str
