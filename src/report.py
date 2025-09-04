# src/report.py
from __future__ import annotations
import json
from datetime import datetime
from typing import Dict, List
from pathlib import Path

def write_report(path: str, source_logs: List[Dict], events_preview: List[Dict]) -> None:
    data = {
        "version": "2.0",
        "run_started_utc": datetime.utcnow().isoformat() + "Z",
        "success": True,
        "total_events": sum(s.get("count", 0) for s in source_logs),
        "sources_processed": len(source_logs),
        "source_logs": source_logs,
        "events_preview": events_preview[:100],
        "events_preview_count": len(events_preview[:100]),
    }
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
