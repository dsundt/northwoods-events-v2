# src/curated.py
"""
User-curated feeds module.

Processes curated feed configurations and generates personalized ICS files
based on manually selected events and auto-selection preferences.
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Set

import yaml

from src.ics_writer import write_combined_ics
from src.util import slugify, json_default


def _load_curated_config(config_path: str) -> List[Dict[str, Any]]:
    """
    Load curated feeds configuration from YAML file.
    
    Args:
        config_path: Path to curated.yaml configuration file
        
    Returns:
        List of curated feed configurations
    """
    if not os.path.exists(config_path):
        print(f"[curated] No curated config found at {config_path}")
        return []
    
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            configs = yaml.safe_load(f)
        
        if not isinstance(configs, list):
            print("[curated] ERROR: curated.yaml must be a list")
            return []
        
        return configs
    except Exception as e:
        print(f"[curated] ERROR loading curated config: {e}")
        return []


def _is_future_event(event: Dict[str, Any], now: Optional[datetime] = None) -> bool:
    """
    Check if an event is in the future.
    
    Args:
        event: Event dictionary with start_utc field
        now: Current time (defaults to now)
        
    Returns:
        True if event is in the future, False otherwise
    """
    if now is None:
        now = datetime.now(timezone.utc)
    
    start_str = event.get("start_utc")
    if not start_str:
        return False
    
    try:
        if isinstance(start_str, datetime):
            start_dt = start_str
        else:
            from dateutil import parser as dtparse
            start_dt = dtparse.parse(str(start_str))
        
        if start_dt.tzinfo is None:
            start_dt = start_dt.replace(tzinfo=timezone.utc)
        else:
            start_dt = start_dt.astimezone(timezone.utc)
        
        return start_dt >= now
    except Exception:
        return False


def _matches_keywords(text: str, keywords: List[str]) -> bool:
    """
    Check if text contains any of the keywords (case-insensitive).
    
    Args:
        text: Text to search
        keywords: List of keywords to match
        
    Returns:
        True if any keyword matches, False otherwise
    """
    if not keywords or not text:
        return False
    
    text_lower = text.lower()
    return any(keyword.lower() in text_lower for keyword in keywords)


def _event_matches_preferences(
    event: Dict[str, Any],
    preferences: Dict[str, Any],
    now: Optional[datetime] = None
) -> bool:
    """
    Check if an event matches the auto-selection preferences.
    
    Args:
        event: Event dictionary
        preferences: Preferences dictionary from curated config
        now: Current time (defaults to now)
        
    Returns:
        True if event matches preferences, False otherwise
    """
    if now is None:
        now = datetime.now(timezone.utc)
    
    # Check if event is in the future
    if not _is_future_event(event, now):
        return False
    
    # Check days_ahead limit
    days_ahead = preferences.get("days_ahead")
    if days_ahead and days_ahead > 0:
        try:
            start_str = event.get("start_utc")
            if start_str:
                from dateutil import parser as dtparse
                start_dt = dtparse.parse(str(start_str)) if isinstance(start_str, str) else start_str
                if start_dt.tzinfo is None:
                    start_dt = start_dt.replace(tzinfo=timezone.utc)
                else:
                    start_dt = start_dt.astimezone(timezone.utc)
                
                max_date = now + timedelta(days=days_ahead)
                if start_dt > max_date:
                    return False
        except Exception:
            pass
    
    # Check source filters
    event_source = event.get("calendar_slug") or event.get("source") or ""
    
    include_sources = preferences.get("include_sources", [])
    if include_sources:
        # If include list is specified, event must be from one of these sources
        if not any(src.lower() in event_source.lower() or event_source.lower() in src.lower() 
                   for src in include_sources):
            return False
    
    exclude_sources = preferences.get("exclude_sources", [])
    if exclude_sources:
        # If event is from excluded source, reject it
        if any(src.lower() in event_source.lower() or event_source.lower() in src.lower() 
               for src in exclude_sources):
            return False
    
    # Check location filters
    locations = preferences.get("locations", [])
    if locations:
        event_location = event.get("location") or ""
        if not _matches_keywords(event_location, locations):
            return False
    
    # Check exclude keywords (takes precedence)
    exclude_keywords = preferences.get("exclude_keywords", [])
    if exclude_keywords:
        title = event.get("title") or ""
        description = event.get("description") or ""
        combined_text = f"{title} {description}"
        
        if _matches_keywords(combined_text, exclude_keywords):
            return False
    
    # Check include keywords
    keywords = preferences.get("keywords", [])
    if keywords:
        title = event.get("title") or ""
        description = event.get("description") or ""
        location = event.get("location") or ""
        combined_text = f"{title} {description} {location}"
        
        if not _matches_keywords(combined_text, keywords):
            return False
    
    return True


def _select_curated_events(
    all_events: List[Dict[str, Any]],
    config: Dict[str, Any],
    now: Optional[datetime] = None
) -> List[Dict[str, Any]]:
    """
    Select events for a curated feed based on configuration.
    
    Args:
        all_events: List of all available events
        config: Curated feed configuration
        now: Current time (defaults to now)
        
    Returns:
        List of selected events for the curated feed
    """
    if now is None:
        now = datetime.now(timezone.utc)
    
    selected_events: List[Dict[str, Any]] = []
    selected_uids: Set[str] = set()
    
    # First, add manually selected events (by UID)
    manual_uids = config.get("selected_events", [])
    if manual_uids:
        for event in all_events:
            uid = event.get("uid")
            if uid in manual_uids and _is_future_event(event, now):
                selected_events.append(event)
                selected_uids.add(uid)
    
    # Then, add auto-selected events based on preferences
    preferences = config.get("preferences", {})
    if preferences:
        max_auto = preferences.get("max_auto_events", 0)
        auto_count = 0
        
        for event in all_events:
            uid = event.get("uid")
            
            # Skip if already manually selected
            if uid in selected_uids:
                continue
            
            # Check if event matches preferences
            if _event_matches_preferences(event, preferences, now):
                selected_events.append(event)
                selected_uids.add(uid)
                auto_count += 1
                
                # Check max limit
                if max_auto > 0 and auto_count >= max_auto:
                    break
    
    # Sort by start date
    selected_events.sort(key=lambda e: e.get("start_utc") or "")
    
    return selected_events


def process_curated_feeds(
    all_events: List[Dict[str, Any]],
    config_path: str = "config/curated.yaml",
    output_dir: str = "public/curated",
    mirror_dirs: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Process all curated feeds and generate ICS files.
    
    Args:
        all_events: List of all available events from all sources
        config_path: Path to curated.yaml configuration
        output_dir: Directory to write curated ICS files
        mirror_dirs: Additional directories to mirror outputs to
        
    Returns:
        Dictionary with processing summary and results
    """
    if mirror_dirs is None:
        mirror_dirs = ["github-pages/curated", "docs/curated"]
    
    now = datetime.now(timezone.utc)
    configs = _load_curated_config(config_path)
    
    results = {
        "generated_at": now.isoformat(),
        "total_feeds": 0,
        "enabled_feeds": 0,
        "feeds": []
    }
    
    if not configs:
        print("[curated] No curated feeds configured")
        return results
    
    # Ensure output directories exist
    os.makedirs(output_dir, exist_ok=True)
    for mirror_dir in mirror_dirs:
        os.makedirs(mirror_dir, exist_ok=True)
    
    for config in configs:
        feed_id = config.get("id")
        feed_name = config.get("name", feed_id)
        enabled = config.get("enabled", True)
        
        results["total_feeds"] += 1
        
        if not enabled:
            print(f"[curated] Skipping disabled feed: {feed_name} ({feed_id})")
            results["feeds"].append({
                "id": feed_id,
                "name": feed_name,
                "enabled": False,
                "count": 0,
                "path": None
            })
            continue
        
        results["enabled_feeds"] += 1
        
        print(f"[curated] Processing feed: {feed_name} ({feed_id})")
        
        try:
            # Select events for this curated feed
            selected_events = _select_curated_events(all_events, config, now)
            
            # Generate ICS file
            slug = slugify(feed_id or feed_name, fallback="curated")
            ics_filename = f"{slug}.ics"
            ics_path = os.path.join(output_dir, ics_filename)
            
            count, written_path = write_combined_ics(selected_events, ics_path)
            
            # Mirror to other directories
            for mirror_dir in mirror_dirs:
                mirror_path = os.path.join(mirror_dir, ics_filename)
                try:
                    import shutil
                    shutil.copy2(written_path, mirror_path)
                except Exception as e:
                    print(f"[curated] WARN: Failed to mirror {written_path} to {mirror_path}: {e}")
            
            rel_path = f"curated/{ics_filename}"
            
            print(f"[curated] Generated {count} events for {feed_name}: {ics_path}")
            
            # Calculate manual vs auto event counts
            manual_uids = config.get("selected_events") or []
            manual_count = len(manual_uids)
            manual_selected = len([uid for uid in manual_uids 
                                  if any(e.get("uid") == uid for e in selected_events)])
            auto_count = count - manual_selected
            
            results["feeds"].append({
                "id": feed_id,
                "name": feed_name,
                "enabled": True,
                "count": count,
                "path": rel_path,
                "manual_count": manual_selected,
                "auto_count": auto_count
            })
            
        except Exception as e:
            print(f"[curated] ERROR processing feed {feed_name}: {e}")
            results["feeds"].append({
                "id": feed_id,
                "name": feed_name,
                "enabled": True,
                "count": 0,
                "path": None,
                "error": str(e)
            })
    
    return results
