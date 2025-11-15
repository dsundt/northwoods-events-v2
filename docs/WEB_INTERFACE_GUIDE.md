# Web Interface Guide

The Northwoods Events web interface provides a graphical user interface for managing curated event feeds without editing configuration files.

## Features

- **Browse Events**: View all available events from all sources
- **Create Curated Feeds**: Build personalized event calendars
- **Manage Preferences**: Configure auto-selection rules
- **On-Demand Generation**: Generate feeds instantly
- **Visual Feedback**: See event counts and feed status in real-time

## Getting Started

### Installation

1. Install Flask dependency:
```bash
pip install -r requirements.txt
```

### Starting the Web Server

```bash
python src/web_app.py
```

Or with custom port:
```bash
PORT=8000 python src/web_app.py
```

The server will start at `http://localhost:5000` (or your custom port).

### Environment Variables

- `PORT`: Server port (default: 5000)
- `FLASK_DEBUG`: Enable debug mode (default: False)
- `CURATED_CONFIG_PATH`: Path to curated.yaml (default: config/curated.yaml)
- `NW_REPORT_JSON`: Path to report.json (default: public/report.json)
- `PUBLIC_DIR`: Public output directory (default: public)

## User Interface

### 1. My Feeds Page (`/`)

**Main dashboard for managing your curated feeds.**

Features:
- View all curated feeds with statistics
- Enable/disable feeds
- Edit or delete feeds
- Generate feeds on-demand
- Refresh all events from sources

Each feed card shows:
- Feed name and ID
- Enabled/disabled status
- Total events count
- Manual vs auto-selected breakdown
- Download link (if generated)

Actions:
- **Edit**: Modify feed settings and preferences
- **Enable/Disable**: Toggle feed active status
- **Delete**: Remove feed permanently
- **Generate**: Create/update the ICS file

### 2. Browse Events Page (`/browse`)

**Explore all available events from all sources.**

Features:
- Search events by keyword
- Filter by source
- Filter by location
- Select multiple events
- Add selected events to any feed

How to use:
1. Use filters to find events you're interested in
2. Click events to select them (they'll turn blue)
3. Click "Add to Curated Feed" button
4. Choose which feed to add them to
5. Confirm to save

### 3. Create/Edit Feed Pages (`/new-feed`, `/feed/<id>`)

**Configure curated feeds with detailed preferences.**

#### Basic Settings

- **Feed ID**: Unique identifier (lowercase, numbers, hyphens only)
  - Used in URL: `/curated/<id>.ics`
  - Cannot be changed after creation
- **Feed Name**: Display name for the calendar
- **Enabled**: Whether this feed is active

#### Manually Selected Events

Add specific event UIDs that should always be included:
- Enter UIDs manually
- Or select events from Browse page
- Events must be in the future to appear in feed

#### Auto-Selection Preferences

**Include Sources**
- Select specific sources to include
- Leave empty to include all sources
- Example: "Boulder Junction (TEC)", "Eagle River Chamber"

**Exclude Sources**
- Prevent events from certain sources
- Takes precedence over include list

**Location Keywords**
- Filter by location substring matching
- Case-insensitive
- Example: "Eagle River", "Boulder Junction"

**Include Keywords**
- Events must match at least one keyword
- Searches title, description, and location
- Case-insensitive
- Example: "music", "festival", "family"

**Exclude Keywords**
- Events matching these are filtered out
- Takes precedence over include keywords
- Example: "21+", "adults only", "bar crawl"

**Maximum Auto Events**
- Limit number of auto-selected events
- 0 = unlimited
- Example: 50

**Days Ahead**
- How far into the future to include events
- Overrides global setting
- Example: 90 days

## API Endpoints

The web interface uses a REST API that can also be accessed programmatically.

### Events

**GET /api/events**
- Get all events
- Query params: `keyword`, `source`, `location`
- Returns: `{success, total, filtered, events[]}`

**GET /api/sources**
- Get all event sources
- Returns: `{success, sources[]}`

### Curated Feeds

**GET /api/feeds**
- Get all curated feeds with statistics
- Returns: `{success, feeds[]}`

**GET /api/feeds/<id>**
- Get specific feed configuration
- Returns: `{success, feed}`

**POST /api/feeds**
- Create new curated feed
- Body: `{id, name, enabled, selected_events[], preferences{}}`
- Returns: `{success, feed}`

**PUT /api/feeds/<id>**
- Update existing feed
- Body: `{name, enabled, selected_events[], preferences{}}`
- Returns: `{success, feed}`

**DELETE /api/feeds/<id>**
- Delete curated feed
- Returns: `{success}`

### Generation

**POST /api/generate**
- Generate curated feeds
- Body: `{feed_id}` (optional, generates all if omitted)
- Returns: `{success, message, results}`

**POST /api/pipeline/run**
- Run full pipeline (fetch events + generate feeds)
- Background process
- Returns: `{success, message}`

**GET /api/report**
- Get latest pipeline report
- Returns: `{success, report}`

## Common Workflows

### Workflow 1: Create a Family-Friendly Feed

1. Go to "Create Feed" page
2. Set ID: `family-events`
3. Set Name: "Family-Friendly Events"
4. Add keywords: `family`, `kids`, `children`
5. Add exclude keywords: `21+`, `adults only`
6. Set max events: `30`
7. Click "Save & Generate"
8. Download from home page

### Workflow 2: Select Specific Events

1. Go to "Browse Events"
2. Search for events (e.g., "music")
3. Click events you want to add
4. Click "Add to Curated Feed"
5. Select existing feed or create new one
6. Generate feed
7. Download ICS file

### Workflow 3: Location-Specific Feed

1. Create new feed
2. Set ID: `eagle-river-only`
3. Set Name: "Eagle River Events"
4. Add location: `Eagle River`
5. Or use include sources: `eagle-river-chamber-tec`
6. Save and generate

### Workflow 4: Regular Updates

1. Set feeds to "Enabled"
2. Run pipeline daily (or use cron/GitHub Actions)
3. Feeds auto-update with new events
4. Past events automatically dropped
5. Subscribe to feed URL in calendar app

## Integration

### Calendar Apps

After generating a feed, download the ICS file or copy the URL:

```
http://localhost:5000/curated/my-events.ics
```

**Google Calendar:**
1. Settings → Add calendar → From URL
2. Paste URL
3. Calendar updates automatically

**Apple Calendar:**
1. File → New Calendar Subscription
2. Paste URL
3. Set refresh frequency

**Outlook:**
1. Add calendar → From internet
2. Paste URL
3. Name and save

### Automation

Run the web server alongside your automated pipeline:

```bash
# Start web server
python src/web_app.py &

# Run pipeline (cron/GitHub Actions)
python -m src.main
```

Or use the API to trigger generation:

```bash
curl -X POST http://localhost:5000/api/pipeline/run
```

## Production Deployment

### Docker

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 5000
CMD ["python", "src/web_app.py"]
```

### Environment Setup

```bash
export FLASK_DEBUG=False
export PORT=8080
python src/web_app.py
```

### Reverse Proxy (nginx)

```nginx
location / {
    proxy_pass http://localhost:5000;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
}
```

### Security Considerations

1. **Authentication**: Add auth middleware for production
2. **HTTPS**: Use SSL/TLS for production
3. **Rate Limiting**: Implement rate limits on API
4. **File Permissions**: Ensure proper file permissions
5. **Input Validation**: Already implemented in API

## Troubleshooting

### Server Won't Start

**Error: Port already in use**
```bash
# Use different port
PORT=8080 python src/web_app.py
```

**Error: Module not found**
```bash
# Install dependencies
pip install -r requirements.txt
```

### No Events Showing

**Problem**: Browser shows "No events found"

**Solutions:**
1. Run pipeline first: `python -m src.main`
2. Check report.json exists
3. Verify sources are configured
4. Check report.json for errors

### Feed Not Generating

**Problem**: "Generate Feed" doesn't create ICS file

**Solutions:**
1. Check feed is enabled
2. Verify events exist matching preferences
3. Check file permissions in public/curated/
4. Look at browser console for errors
5. Check server logs

### Changes Not Saving

**Problem**: Feed changes don't persist

**Solutions:**
1. Check file permissions on config/curated.yaml
2. Verify no YAML syntax errors
3. Check server logs for error messages
4. Try clearing browser cache

## Advanced Usage

### Custom Filters

Edit feed preferences to create complex filters:

```yaml
preferences:
  include_sources:
    - boulder-junction-tec
    - eagle-river-chamber-tec
  keywords:
    - music
    - concert
  exclude_keywords:
    - "21+"
  locations:
    - "Eagle River"
  max_auto_events: 30
  days_ahead: 60
```

### Bulk Operations

Use API for bulk operations:

```python
import requests

# Get all feeds
feeds = requests.get('http://localhost:5000/api/feeds').json()['feeds']

# Update multiple feeds
for feed in feeds:
    feed['preferences']['days_ahead'] = 90
    requests.put(f'http://localhost:5000/api/feeds/{feed["id"]}', json=feed)

# Generate all
requests.post('http://localhost:5000/api/generate')
```

### Custom Styling

Edit `web/static/css/style.css` to customize appearance:

```css
:root {
    --primary-color: #your-color;
    --secondary-color: #your-color;
}
```

## Support

- Check logs in terminal running web server
- Review `public/report.json` for pipeline issues
- Verify config/curated.yaml syntax
- Check browser developer console for frontend errors

## Next Steps

1. **Create your first feed** using the web interface
2. **Browse and select events** you're interested in
3. **Set up automation** to run pipeline regularly
4. **Subscribe to feeds** in your calendar app
5. **Customize preferences** as your needs change
