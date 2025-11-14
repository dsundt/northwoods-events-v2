# src/report.py
from __future__ import annotations
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from src.util import json_default

EVENTS_PREVIEW_LIMIT = int(os.getenv("NW_EVENTS_PREVIEW_LIMIT", "0"))

def write_report(path: str, source_logs: List[Dict], events_preview: List[Dict]) -> None:
    preview = (
        events_preview[:EVENTS_PREVIEW_LIMIT]
        if EVENTS_PREVIEW_LIMIT > 0
        else events_preview
    )

    data = {
        "version": "2.0",
        "run_started_utc": datetime.utcnow().isoformat() + "Z",
        "success": True,
        "total_events": sum(s.get("count", 0) for s in source_logs),
        "sources_processed": len(source_logs),
        "source_logs": source_logs,
        "events_preview": preview,
        "events_preview_count": len(preview),
    }
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=json_default)
