from __future__ import annotations
import json
from pathlib import Path
from typing import Dict, Any, List

def write_report(path: Path, run_meta: Dict[str, Any], per_source: List[Dict[str, Any]], events_preview: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": "2.0",
        "run_started_utc": run_meta["run_started_utc"],
        "success": True,
        "total_events": sum(s["count"] for s in per_source),
        "sources_processed": len(per_source),
        "source_logs": per_source,
        "events_preview": events_preview[:100],
        "events_preview_count": min(100, sum(s["count"] for s in per_source)),
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
