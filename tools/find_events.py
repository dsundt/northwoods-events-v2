#!/usr/bin/env python3
"""
Helper script to search and find events for curated feeds.

Usage:
    python tools/find_events.py --keyword "music"
    python tools/find_events.py --source "boulder-junction"
    python tools/find_events.py --location "Eagle River"
    python tools/find_events.py --keyword "festival" --days 30
"""

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path


def load_events(report_path="public/report.json"):
    """Load events from report.json"""
    if not Path(report_path).exists():
        print(f"Error: {report_path} not found. Run the pipeline first.")
        sys.exit(1)
    
    with open(report_path, "r") as f:
        data = json.load(f)
    
    return data.get("normalized_events", [])


def search_events(events, keyword=None, source=None, location=None, days=None):
    """Filter events based on search criteria"""
    results = []
    now = datetime.now(timezone.utc)
    
    for event in events:
        # Filter by days ahead
        if days:
            try:
                from dateutil import parser as dtparse
                start_str = event.get("start_utc")
                if start_str:
                    start_dt = dtparse.parse(start_str)
                    if start_dt.tzinfo is None:
                        start_dt = start_dt.replace(tzinfo=timezone.utc)
                    else:
                        start_dt = start_dt.astimezone(timezone.utc)
                    
                    if start_dt > now + timedelta(days=days):
                        continue
            except Exception:
                pass
        
        # Filter by keyword
        if keyword:
            title = (event.get("title") or "").lower()
            source_data = event.get("_source") or {}
            desc = (source_data.get("description") if isinstance(source_data, dict) else "") or ""
            desc = desc.lower()
            if keyword.lower() not in title and keyword.lower() not in desc:
                continue
        
        # Filter by source
        if source:
            event_source = (event.get("source") or "").lower()
            if source.lower() not in event_source:
                continue
        
        # Filter by location
        if location:
            event_location = (event.get("location") or "").lower()
            if location.lower() not in event_location:
                continue
        
        results.append(event)
    
    return results


def format_event(event, show_uid=False):
    """Format event for display"""
    title = event.get("title", "Untitled")
    start = event.get("start_utc", "Unknown date")
    location = event.get("location", "No location")
    source = event.get("source", "Unknown source")
    url = event.get("url", "")
    
    # Get UID from _source if available
    source_data = event.get("_source") or {}
    uid = (source_data.get("uid") if isinstance(source_data, dict) else None) or event.get("uid", "N/A")
    
    output = f"""
Title:    {title}
Date:     {start}
Location: {location}
Source:   {source}
URL:      {url}"""
    
    if show_uid:
        output += f"\nUID:      {uid}"
    
    return output


def main():
    parser = argparse.ArgumentParser(
        description="Search events for curated feeds",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python tools/find_events.py --keyword "music"
    python tools/find_events.py --source "boulder-junction"
    python tools/find_events.py --location "Eagle River"
    python tools/find_events.py --keyword "festival" --days 30 --show-uid
        """
    )
    
    parser.add_argument("--keyword", "-k", help="Search in title and description")
    parser.add_argument("--source", "-s", help="Filter by source name")
    parser.add_argument("--location", "-l", help="Filter by location")
    parser.add_argument("--days", "-d", type=int, help="Only show events within N days")
    parser.add_argument("--show-uid", action="store_true", help="Show event UIDs")
    parser.add_argument("--report", default="public/report.json", help="Path to report.json")
    parser.add_argument("--limit", type=int, default=20, help="Maximum events to show")
    
    args = parser.parse_args()
    
    if not any([args.keyword, args.source, args.location]):
        parser.print_help()
        print("\nError: Please specify at least one search criteria (--keyword, --source, or --location)")
        sys.exit(1)
    
    # Load events
    events = load_events(args.report)
    
    # Search
    results = search_events(
        events,
        keyword=args.keyword,
        source=args.source,
        location=args.location,
        days=args.days
    )
    
    # Display results
    print(f"\nFound {len(results)} matching events")
    if len(results) > args.limit:
        print(f"Showing first {args.limit} events (use --limit to show more)")
        results = results[:args.limit]
    
    print("=" * 80)
    
    for i, event in enumerate(results, 1):
        print(f"\nEvent {i}:")
        print(format_event(event, show_uid=args.show_uid))
        print("-" * 80)
    
    if args.show_uid:
        print("\nTo add events to a curated feed:")
        print("1. Copy the UID(s) above")
        print("2. Edit config/curated.yaml")
        print("3. Add the UID to the 'selected_events' list")
        print("4. Run the pipeline to regenerate curated feeds")


if __name__ == "__main__":
    main()
