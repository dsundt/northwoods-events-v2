# User-Curated Feeds Feature - Implementation Summary

## Overview

Successfully implemented a comprehensive user-curated feeds system that allows users to create personalized event calendars based on hand-picked events and automatic filtering preferences.

## What Was Built

### 1. Core Functionality (`src/curated.py`)

A complete curated feed processing module with:

- **Manual Event Selection**: Select specific events by UID
- **Automatic Event Filtering**: Auto-select events based on:
  - Source filters (include/exclude specific sources)
  - Location keywords (substring matching)
  - Title/description keywords (case-insensitive)
  - Exclude keywords (blacklist)
  - Date range limits (days ahead)
  - Event count limits
- **Automatic Maintenance**: 
  - Drops past events automatically
  - Includes new matching events each run
  - Sorts events chronologically

### 2. Configuration System (`config/curated.yaml`)

User-friendly YAML configuration with:
- 4 example curated feed templates
- Detailed inline comments explaining each option
- Examples for different use cases (family events, outdoor activities, music & arts, weekends)
- Easy enable/disable toggle per feed

### 3. Helper Tools (`tools/find_events.py`)

Command-line tool for discovering events:
- Search by keyword
- Filter by source
- Filter by location
- Limit by days ahead
- Show UIDs for manual selection
- Flexible output formatting

### 4. Pipeline Integration

Modified `src/main.py` to:
- Process curated feeds after collecting all events
- Generate ICS files for each enabled curated feed
- Mirror outputs to `public/`, `github-pages/`, and `docs/` directories
- Include curated feed metadata in `report.json`
- Include UIDs in event previews for easy discovery

### 5. Documentation

**README.md Updates**:
- Added curated feeds to outputs list
- Comprehensive "User-Curated Feeds" section with:
  - Feature highlights
  - Quick start guide
  - Configuration examples
  - Use case examples
  - Links to detailed documentation

**Detailed Guide** (`docs/CURATED_FEEDS_GUIDE.md`):
- Complete configuration reference
- Step-by-step tutorials
- Multiple example use cases
- Advanced tips and tricks
- Troubleshooting section
- Calendar app integration instructions
- API access information

## Key Features

### ✅ Hand-Picked Events
- Select specific events by UID from any source
- Events persist until they become past events
- Works across all source types

### ✅ Smart Auto-Selection
Multiple filtering criteria that can be combined:
- **Source filters**: Include/exclude specific event sources
- **Location matching**: Filter by location keywords
- **Keyword inclusion**: Match keywords in title/description
- **Keyword exclusion**: Blacklist unwanted terms
- **Date limits**: Custom date ranges per feed
- **Count limits**: Cap maximum auto-selected events

### ✅ Automatic Updates
- Past events automatically dropped daily
- New matching events automatically added
- No manual maintenance required
- Runs as part of existing pipeline

### ✅ Multiple Feeds
- Create unlimited curated feeds
- Each with independent preferences
- Enable/disable individual feeds
- Separate ICS file per feed

### ✅ Monitoring & Reporting
- Each feed reports in `report.json`:
  - Total event count
  - Manual vs auto-selected counts
  - Processing status
  - File paths

## File Structure

```
/workspace/
├── config/
│   └── curated.yaml              # User configuration for curated feeds
├── src/
│   ├── curated.py                # Core curated feeds module
│   └── main.py                   # Updated to process curated feeds
├── tools/
│   └── find_events.py            # Helper script to discover events
├── docs/
│   └── CURATED_FEEDS_GUIDE.md    # Comprehensive user guide
├── public/
│   └── curated/
│       └── *.ics                 # Generated curated ICS files
├── github-pages/
│   └── curated/
│       └── *.ics                 # Mirror for GitHub Pages
└── docs/
    └── curated/
        └── *.ics                 # Mirror for docs deployment
```

## Usage Example

### 1. Configure a Curated Feed

Edit `config/curated.yaml`:

```yaml
- id: my-events
  name: "My Personal Events"
  enabled: true
  
  selected_events:
    - "10017882"  # Specific event I want
  
  preferences:
    keywords:
      - "music"
      - "festival"
    
    exclude_keywords:
      - "21+"
    
    locations:
      - "Eagle River"
    
    max_auto_events: 30
    days_ahead: 60
```

### 2. Find Events to Add

```bash
python tools/find_events.py --keyword "music" --show-uid --limit 10
```

### 3. Run Pipeline

```bash
python -m src.main
```

### 4. Use Your Feed

Subscribe to: `https://your-site.github.io/curated/my-events.ics`

## Testing Results

✅ Successfully generates curated ICS files  
✅ Manual event selection works correctly  
✅ Auto-selection filters work as expected  
✅ Past events are excluded  
✅ Files mirrored to all deployment directories  
✅ Report.json includes curated feed metadata  
✅ Helper tool finds events correctly  
✅ Multiple curated feeds work independently  

### Test Feed Results

**Family-Friendly Events Feed**:
- Total events: 16
- Manual selections: 2
- Auto-selected: 14
- Preferences: Keywords (family, kids, children, festival, parade), Sources (boulder-junction, eagle-river, vilas-county)

## API & Integration

### Output Files

Each enabled curated feed generates:
- `public/curated/{feed-id}.ics` - Standard ICS calendar file
- Entry in `public/report.json` under `curated_feeds` section

### Report JSON Structure

```json
{
  "curated_feeds": {
    "generated_at": "2025-11-15T17:10:00.000000+00:00",
    "total_feeds": 4,
    "enabled_feeds": 1,
    "feeds": [
      {
        "id": "family-events",
        "name": "Family-Friendly Northwoods Events",
        "enabled": true,
        "count": 16,
        "path": "curated/family-events.ics",
        "manual_count": 2,
        "auto_count": 14
      }
    ]
  }
}
```

## Future Enhancement Ideas

Potential improvements for future development:

1. **Weekday Filters**: Filter by day of week (e.g., weekends only)
2. **Time Filters**: Filter by time of day (morning, afternoon, evening)
3. **Category Support**: If sources provide categories, filter by them
4. **Fuzzy Matching**: More sophisticated keyword matching
5. **Web UI**: Browser-based interface for managing curated feeds
6. **Event Scoring**: Rank events by relevance to preferences
7. **Notification System**: Alert on new matching events
8. **Export/Import**: Share curated feed configurations
9. **Templates**: Pre-built curated feed templates for common use cases
10. **Statistics**: Track which preferences match most events

## Backward Compatibility

✅ Fully backward compatible  
✅ No changes to existing functionality  
✅ Curated feeds are optional  
✅ Pipeline works with or without curated.yaml  
✅ No breaking changes to existing outputs  

## Dependencies

No new dependencies required! Uses existing:
- `pyyaml` - For configuration parsing
- `icalendar` - For ICS generation
- `python-dateutil` - For date handling

All already in `requirements.txt`.

## Performance

- Minimal performance impact
- Curated feed processing happens after main collection
- Fast filtering even with 500+ source events
- Scales to multiple curated feeds without issues

## Summary

This implementation provides a powerful, flexible, and user-friendly system for creating personalized event feeds. Users can now:

✅ Curate their own event calendars  
✅ Combine manual selection with intelligent auto-filtering  
✅ Maintain feeds automatically without manual updates  
✅ Subscribe to personalized feeds in any calendar app  
✅ Create multiple specialized feeds for different interests  

The feature is fully documented, tested, and ready for production use!
