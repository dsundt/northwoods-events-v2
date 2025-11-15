# Northwoods Events – Version 2.0

A clean, resilient calendar aggregation pipeline that collects events from:
- Public **ICS** feeds
- **The Events Calendar (TEC)** HTML
- **GrowthZone** HTML
- **AI1EC** HTML

Outputs:
- `public/combined.ics` - All events from all sources
- `public/by-source/<slug>.ics` - Individual source feeds
- `public/curated/<slug>.ics` - User-curated personalized feeds ✨ NEW
- `public/report.json` - Processing report
- `public/index.html` - Web interface

## 🌐 Web Interface ✨ NEW

Manage your curated feeds through an intuitive web interface - no config files needed!

```bash
# Install dependencies
pip install -r requirements.txt

# Start web server
python src/web_app.py
```

Visit `http://localhost:5000` to:
- 📅 **Browse all events** from all sources
- ✨ **Create curated feeds** with visual editor
- 🎯 **Select specific events** by clicking
- ⚙️ **Configure preferences** (keywords, sources, locations)
- ⚡ **Generate feeds on-demand**
- 📊 **View statistics** (event counts, manual vs auto)

See [docs/WEB_INTERFACE_GUIDE.md](docs/WEB_INTERFACE_GUIDE.md) for complete documentation.

## How it works

1. GitHub Actions workflow runs daily (09:15 UTC) and on demand.
2. `src/main.py` loads `config/sources.yaml`.
3. Each enabled source is fetched (with retries/timeouts), parsed, normalized to UTC.
4. Outputs written to `public/` and deployed to GitHub Pages.

## Quick Start

### Option 1: Web Interface (Recommended)

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run pipeline to fetch events
python -m src.main

# 3. Start web server
python src/web_app.py

# 4. Open browser
# Visit http://localhost:5000
```

See [WEB_QUICKSTART.md](WEB_QUICKSTART.md) for detailed tutorial.

### Option 2: GitHub Pages Deployment

1. Upload the provided files to your repository.
2. Edit `config/sources.yaml` and add real sources (`enabled: true` to activate).
3. Enable Actions and Pages (Settings → Pages → Source: GitHub Actions).
4. Run the workflow manually from **Actions** to test the pipeline.
5. Visit the Pages URL to access `index.html`, `combined.ics`, and `report.json`.

## Notes

- Times are normalized to **UTC** to avoid VTIMEZONE/DST issues.
- Stable `uid` per event enables deduplication across sources.
- `report.json` is always written to aid troubleshooting.
- Workflow calls `python -m src.main` for import reliability.

## User-Curated Feeds ✨ NEW

Create personalized event feeds that combine hand-picked events with automatic filtering based on your preferences!

### Features

- **Hand-pick specific events** by UID from any source
- **Auto-select events** using flexible filters:
  - Source filters (include/exclude specific sources)
  - Location keywords (e.g., "Boulder Junction", "Eagle River")
  - Title/description keywords (e.g., "family", "music", "outdoor")
  - Exclude keywords (e.g., "21+", "adults only")
  - Date range limits
- **Automatic updates**: Past events are dropped, new matching events are added daily
- **Multiple curated feeds**: Create as many personalized feeds as you need

### Quick Start

1. **Edit `config/curated.yaml`** to define your curated feeds:

```yaml
- id: family-events
  name: "Family-Friendly Northwoods Events"
  enabled: true
  
  # Manually selected event UIDs (from report.json)
  selected_events:
    - "abc123def456..."
  
  # Auto-selection preferences
  preferences:
    include_sources:
      - boulder-junction-tec
      - eagle-river-chamber-tec
    
    keywords:
      - "family"
      - "kids"
      - "festival"
    
    exclude_keywords:
      - "21+"
      - "adults only"
    
    max_auto_events: 50
    days_ahead: 90
```

2. **Run the pipeline** (manual or automatic via GitHub Actions)

3. **Access your curated feed**:
   - `https://your-github-pages-url/curated/family-events.ics`
   - Subscribe to it in your calendar app!

### Finding Event UIDs

To manually select specific events:

1. Visit `https://your-github-pages-url/report.json`
2. Browse the `events_preview` or `normalized_events` array
3. Copy the `uid` field of events you want to include
4. Add them to the `selected_events` list in `config/curated.yaml`

### Configuration Options

Each curated feed supports:

- `id`: Unique identifier (used in filename)
- `name`: Display name for the calendar
- `enabled`: Set to `false` to temporarily disable
- `selected_events`: List of event UIDs to always include
- `preferences`:
  - `include_sources`: Only include events from these source IDs (empty = all)
  - `exclude_sources`: Never include events from these source IDs
  - `locations`: Only include events matching these location keywords
  - `keywords`: Only include events matching these keywords in title/description
  - `exclude_keywords`: Exclude events matching these keywords
  - `max_auto_events`: Limit auto-selected events (0 = unlimited)
  - `days_ahead`: Override global date range for this feed

### Example Use Cases

**Family-Friendly Events**: Filter for kid-friendly activities, exclude adult-only events

**Weekend Events**: Create a feed with only Friday-Sunday events

**Outdoor & Sports**: Auto-select hiking, biking, fishing, and sports events

**Music & Arts**: Focus on concerts, galleries, and performances

**Location-Specific**: Only events in your favorite towns

**Custom Mix**: Hand-pick your must-attend events + auto-fill with matching activities

### Full Documentation

See [docs/CURATED_FEEDS_GUIDE.md](docs/CURATED_FEEDS_GUIDE.md) for:
- Detailed configuration reference
- Step-by-step tutorials
- Advanced tips and tricks
- Troubleshooting guide
- Calendar app integration instructions

### Helper Tools

**Find Events Script**: Search and discover events to add to your curated feeds:

```bash
# Search by keyword
python tools/find_events.py --keyword "music" --show-uid

# Filter by location
python tools/find_events.py --location "Eagle River" --show-uid --limit 10

# Combine multiple filters
python tools/find_events.py --keyword "festival" --days 30 --show-uid
```
