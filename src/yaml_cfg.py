from __future__ import annotations

import os
import yaml
from typing import List
from src.sources import SourceCfg, SUPPORTED_TYPES


CFG_PATH = os.path.join("config", "sources.yaml")


def load_sources() -> List[SourceCfg]:
    if not os.path.exists(CFG_PATH):
        return []
    with open(CFG_PATH, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    items = []
    for s in data.get("sources", []):
        t = (s or {}).get("type")
        if t not in SUPPORTED_TYPES:
            continue
        sc = SourceCfg(
            name=s.get("name", s.get("url", "source")),
            type=t,
            url=s.get("url"),
            calendar=s.get("calendar"),
            slug=s.get("slug"),
            min_expected=s.get("min_expected"),
        )
        sc.ensure_slug()
        items.append(sc)
    return items
