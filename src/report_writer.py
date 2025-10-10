from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Dict, List

from src.util import json_default

def write_report(ok: bool, events: List[Dict], source_logs: List[Dict[str, Any]]):
    Path("public").mkdir(parents=True, exist_ok=True)
    payload = {
        "version": "2.0",
        "ok": ok,
        "total_events": len(events),
        "sources": source_logs,
        "sample": events[:100],
    }
    with open("public/report.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2, default=json_default)
