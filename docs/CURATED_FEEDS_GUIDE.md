# User-Curated Feeds Guide

This guide explains how to create and manage personalized event feeds using the curated feeds feature.

## Overview

Curated feeds allow you to create custom calendar feeds by:
1. **Manually selecting specific events** you want to include
2. **Auto-selecting events** based on preferences (keywords, sources, locations, etc.)

Curated feeds automatically:
- Drop past events
- Include new matching events
- Update daily with the main pipeline

## Quick Start

### 1. Create Your First Curated Feed

Edit `config/curated.yaml`:

```yaml
- id: my-events
  name: "My Personal Events"
  enabled: true
  
  selected_events:
    # Add event UIDs here (see step 2)
  
  preferences:
    keywords:
      - "festival"
      - "music"
```

### 2. Find Events to Add Manually

Use the helper script to search for events:

```bash
# Search by keyword
python tools/find_events.py --keyword "music" --show-uid

# Search by location
python tools/find_events.py --location "Eagle River" --show-uid

# Search by source
python tools/find_events.py --source "boulder-junction" --show-uid

# Combine filters
python tools/find_events.py --keyword "family" --days 30 --show-uid
```

Copy the UID(s) of events you want and add them to `selected_events` in your curated feed.

### 3. Run the Pipeline

```bash
python -m src.main
```

Your curated feed will be generated at:
- `public/curated/my-events.ics`

### 4. Subscribe to Your Feed

If you're using GitHub Pages:
```
https://your-username.github.io/your-repo/curated/my-events.ics
```

Add this URL to your calendar app (Google Calendar, Apple Calendar, Outlook, etc.)

## Configuration Reference

### Feed Settings

```yaml
- id: unique-feed-id           # Required: Used in filename
  name: "Display Name"          # Required: Calendar name
  enabled: true                 # Optional: Set to false to disable
  
  selected_events:              # Optional: List of event UIDs
    - "uid1"
    - "uid2"
  
  preferences:                  # Optional: Auto-selection rules
    # ... see below
```

### Preference Options

#### Source Filters

```yaml
preferences:
  # Include only events from these sources (leave empty for all)
  include_sources:
    - boulder-junction-tec
    - eagle-river-chamber-tec
  
  # Exclude events from these sources
  exclude_sources:
    - some-source-to-skip
```

Source IDs can be found in `config/sources.yaml` or `public/report.json`.

#### Location Filters

```yaml
preferences:
  # Include only events matching these location keywords
  locations:
    - "Eagle River"
    - "Boulder Junction"
    - "Minocqua"
```

Location matching is case-insensitive and uses substring matching.

#### Keyword Filters

```yaml
preferences:
  # Include events with these keywords in title/description
  keywords:
    - "music"
    - "festival"
    - "art"
  
  # Exclude events with these keywords (takes precedence)
  exclude_keywords:
    - "21+"
    - "adults only"
```

Keywords are case-insensitive and matched anywhere in the title, description, or location.

#### Event Limits

```yaml
preferences:
  # Maximum auto-selected events (0 = unlimited)
  max_auto_events: 50
  
  # Days ahead to look (overrides global setting)
  days_ahead: 90
```

## Example Use Cases

### Family-Friendly Events

Filter for kid-friendly activities, exclude adult-only events:

```yaml
- id: family-events
  name: "Family-Friendly Events"
  enabled: true
  
  selected_events: []
  
  preferences:
    keywords:
      - "family"
      - "kids"
      - "children"
      - "festival"
    
    exclude_keywords:
      - "21+"
      - "adults only"
      - "bar crawl"
    
    max_auto_events: 50
    days_ahead: 90
```

### Outdoor Activities

Focus on outdoor and sports events:

```yaml
- id: outdoor
  name: "Outdoor Adventures"
  enabled: true
  
  selected_events: []
  
  preferences:
    keywords:
      - "hiking"
      - "biking"
      - "fishing"
      - "kayak"
      - "trail"
      - "race"
      - "outdoor"
    
    max_auto_events: 0  # Unlimited
    days_ahead: 180
```

### Location-Specific

Only events in your favorite towns:

```yaml
- id: eagle-river-only
  name: "Eagle River Events"
  enabled: true
  
  selected_events: []
  
  preferences:
    locations:
      - "Eagle River"
    
    # Or use source filter
    include_sources:
      - eagle-river-chamber-tec
```

### Mixed: Manual + Auto

Hand-pick must-attend events + auto-fill with similar ones:

```yaml
- id: my-favorites
  name: "My Favorite Events"
  enabled: true
  
  # Manually selected events I don't want to miss
  selected_events:
    - "10017882"
    - "25302"
  
  # Also auto-include similar events
  preferences:
    keywords:
      - "music"
      - "art"
    
    locations:
      - "Eagle River"
      - "Boulder Junction"
    
    max_auto_events: 20
```

## Advanced Tips

### Finding Source IDs

Source IDs are listed in `config/sources.yaml`. You can also find them by running:

```bash
python -c "import json; data=json.load(open('public/report.json')); print('\n'.join([s['id'] for s in data['source_logs']]))"
```

### Testing Preferences

Before enabling a curated feed, you can test how many events match your preferences:

```bash
# Enable the feed temporarily
# Run the pipeline
python -m src.main

# Check the results
python -c "import json; data=json.load(open('public/report.json')); feeds=data['curated_feeds']['feeds']; print('\n'.join([f\"{f['name']}: {f['count']} events\" for f in feeds if f['enabled']]))"
```

### Multiple Feeds

You can create as many curated feeds as you need:

```yaml
# config/curated.yaml
- id: family-events
  name: "Family Events"
  enabled: true
  # ...

- id: music-events
  name: "Music & Concerts"
  enabled: true
  # ...

- id: outdoor-events
  name: "Outdoor Activities"
  enabled: true
  # ...
```

Each will generate a separate ICS file.

### Monitoring

Check the processing report at `public/report.json` for:
- Number of events in each curated feed
- Manual vs auto-selected event counts
- Any errors or warnings

Example:

```bash
python -c "import json; data=json.load(open('public/report.json')); print(json.dumps(data['curated_feeds'], indent=2))"
```

## Troubleshooting

### No events in my curated feed

1. Check that the feed is `enabled: true`
2. Verify your preferences aren't too restrictive
3. Check that source IDs are correct
4. Ensure events exist in the date range (check `days_ahead`)

### Manual events not appearing

1. Verify the UID is correct (check `public/report.json`)
2. Make sure the event is still in the future
3. Check that the event exists in one of your sources

### Too many/few events

Adjust these settings:
- `max_auto_events`: Limit total auto-selected events
- `days_ahead`: Reduce or increase time window
- Add more specific keywords or exclude keywords
- Use source filters to narrow down

## Integration with Calendar Apps

### Google Calendar

1. Open Google Calendar
2. Click the "+" next to "Other calendars"
3. Select "From URL"
4. Paste your curated feed URL
5. The calendar will update automatically (usually within 24 hours)

### Apple Calendar

1. Open Calendar app
2. File → New Calendar Subscription
3. Paste your curated feed URL
4. Set refresh frequency to "Every day"

### Outlook

1. Open Outlook Calendar
2. Add Calendar → From Internet
3. Paste your curated feed URL
4. Name your calendar and save

## API Access

Your curated feeds are also available as JSON:

```
https://your-username.github.io/your-repo/report.json
```

The `curated_feeds` section contains metadata about all curated feeds.

## Need Help?

- Check `public/report.json` for processing details
- Use `tools/find_events.py` to explore available events
- Review example configurations in `config/curated.yaml`
- Enable debug mode in `src/curated.py` if needed
