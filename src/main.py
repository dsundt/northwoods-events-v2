from __future__ import annotations

import datetime as dt
from typing import List, Tuple

from src.util import ensure_dirs
from src.yaml_cfg import load_sources
from src.report import Report
from src.models import Event
from src.sources import SourceCfg

from src.parsers.tec_rest import fetch_tec_rest
from src.parsers.tec_html import fetch_tec_html
from src.parsers.growthzone_html import fetch_growthzone_html
from src.parsers.simpleview_html import fetch_simpleview_html
from src.parsers.ics_feed import fetch_ics

from src.ics_writer import write_per_source_ics, write_combined_ics

DATE_RANGE_DAYS = 120

FETCHERS = {
    "tec_rest": fetch_tec_rest,
    "tec_html": fetch_tec_html,
    "growthzone_html": fetch_growthzone_html,
    "simpleview_html": fetch_simpleview_html,
    "ics": fetch_ics,
}


def main():
    ensure_dirs()
    start = dt.date.today()
    end = start + dt.timedelta(days=DATE_RANGE_DAYS)

    report = Report.start()
    sources = load_sources()

    all_events: List[Event] = []
    per_source: List[Tuple[SourceCfg, List[Event]]] = []

    for s in sources:
        fetcher = FETCHERS.get(s.type)
        ok = True
        err = ""
        diag = {}
        items: List[Event] = []
        try:
            items, diag = fetcher(s.url, start, end)
            # annotate source fields for traceability
            for e in items:
                e.source_name = s.name
                if not e.calendar:
                    e.calendar = s.name
        except Exception as ex:
            ok = False
            err = f"{ex.__class__.__name__}: {ex}"

        report.add_log(s.name, s.type, s.url, len(items), ok, err, diag)
        # Always write per-source ICS, even if zero, so gaps are visible
        write_per_source_ics(s, items)

        all_events.extend(items)
        per_source.append((s, items))

    # sort combined by start date
    all_events.sort(key=lambda e: (e.start_utc or dt.datetime.max.replace(tzinfo=dt.timezone.utc)))

    write_combined_ics(all_events)
    report.finish(all_events, per_source)
    report.write_files()

    print({"ok": True, "events": len(all_events)})


if __name__ == "__main__":
    main()
