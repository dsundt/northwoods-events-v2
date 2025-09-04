from __future__ import annotations
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
import os

from src.models import Event
from src.sources import SourceCfg
from src.util import PUBLIC_DIR


@dataclass
class Report:
    run_started_utc: str
    logs: List[Dict[str, Any]] = field(default_factory=list)

    @classmethod
    def start(cls) -> "Report":
        return cls(run_started_utc=datetime.now(timezone.utc).isoformat())

    def add_log(self, name: str, typ: str, url: str, count: int, ok: bool, error: str = "", diag: Dict[str, Any] | None = None):
        self.logs.append({
            "name": name,
            "type": typ,
            "url": url,
            "count": count,
            "ok": ok,
            "error": error,
            "diag": diag or {},
        })

    def finish(self, all_events: List[Event], per_source: List[Tuple[SourceCfg, List[Event]]]):
        self.total_events = len(all_events)
        self.sources_processed = len(per_source)
        # Embed preview for quick UI checks
        preview = []
        for e in all_events[:100]:
            preview.append({
                "uid": e.uid,
                "title": e.title,
                "start_utc": e.start_utc.isoformat() if e.start_utc else None,
                "end_utc": e.end_utc.isoformat() if e.end_utc else None,
                "url": e.url,
                "location": e.location,
                "source": e.source_name,
                "calendar": e.calendar,
            })
        self.events_preview = preview
        self.events_preview_count = len(preview)

    def write_files(self):
        os.makedirs(PUBLIC_DIR, exist_ok=True)
        path = os.path.join(PUBLIC_DIR, "report.json")
        doc = {
            "version": "2.0",
            "run_started_utc": self.run_started_utc,
            "success": True,
            "total_events": getattr(self, "total_events", 0),
            "sources_processed": getattr(self, "sources_processed", 0),
            "source_logs": self.logs,
            "events_preview": getattr(self, "events_preview", []),
            "events_preview_count": getattr(self, "events_preview_count", 0),
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(doc, f, ensure_ascii=False, indent=2)
