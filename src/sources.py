from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
from src.util import slugify

SUPPORTED_TYPES = {
    "tec_rest",
    "tec_html",
    "growthzone_html",
    "simpleview_html",
    "ics",
}


@dataclass
class SourceCfg:
    name: str
    type: str
    url: str
    calendar: Optional[str] = None
    slug: Optional[str] = None
    min_expected: Optional[int] = None  # optional guardrail

    def ensure_slug(self):
        if not self.slug:
            self.slug = f"{slugify(self.name)}-{self.type.replace('_','-')}"
