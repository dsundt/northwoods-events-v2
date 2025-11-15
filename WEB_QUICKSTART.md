# Web Interface Quick Start

Get started with the Northwoods Events web interface in 5 minutes!

## Step 1: Install Dependencies

```bash
pip install -r requirements.txt
```

This installs Flask and other required packages.

## Step 2: Run the Main Pipeline (First Time)

```bash
python -m src.main
```

This fetches all events from your configured sources. Takes 1-2 minutes.

## Step 3: Start the Web Server

```bash
python src/web_app.py
```

You'll see:
```
Starting Northwoods Events Web Interface on http://localhost:5000
 * Running on http://0.0.0.0:5000
```

## Step 4: Open in Browser

Visit: **http://localhost:5000**

## Quick Tutorial

### Create Your First Curated Feed

1. **Click "Create Feed"** button (top right)

2. **Fill in Basic Info:**
   - Feed ID: `my-events` (used in filename)
   - Feed Name: `My Personal Events`
   - Keep "Enabled" checked

3. **Add Some Keywords:**
   - Type `music` → Click "Add"
   - Type `festival` → Click "Add"
   - Type `family` → Click "Add"

4. **Set Preferences:**
   - Max Auto Events: `30`
   - Days Ahead: `60`

5. **Click "Save & Generate"**

6. **Download Your Feed:**
   - You'll be redirected to the homepage
   - Find your new feed card
   - Click "📥 Download ICS"
   - Add to your calendar app!

### Browse and Select Specific Events

1. **Click "Browse Events"** (top nav)

2. **Search for Events:**
   - Type in search box: `concert`
   - Filter by source (dropdown)
   - Filter by location

3. **Select Events You Want:**
   - Click any event card (turns blue when selected)
   - Select multiple events

4. **Add to Feed:**
   - Click "Add to Curated Feed" button (bottom right)
   - Choose your feed
   - Click "Add to Feed"
   - Click "Generate Feed" on homepage

### Edit an Existing Feed

1. **Go to Homepage** (click "My Feeds")

2. **Click "✏️ Edit"** on any feed card

3. **Make Changes:**
   - Add/remove keywords
   - Change preferences
   - Add specific event UIDs

4. **Click "Save & Generate"**

## Common Commands

### Start Web Server
```bash
python src/web_app.py
```

### Start on Different Port
```bash
PORT=8080 python src/web_app.py
```

### Refresh All Events
```bash
python -m src.main
```

Or click "🔄 Refresh All Events" in the web UI.

### Generate All Curated Feeds
Click "⚡ Generate All Feeds" button on homepage.

## What Each Page Does

### 📱 My Feeds (`/`)
- See all your curated feeds
- View statistics (total events, manual vs auto)
- Enable/disable feeds
- Edit, delete, or generate feeds
- Download ICS files

### 📅 Browse Events (`/browse`)
- View all available events (600+)
- Search by keyword
- Filter by source or location
- Select events to add to feeds

### ✏️ Feed Editor (`/feed/<id>` or `/new-feed`)
- Create new feed
- Edit existing feed
- Configure preferences:
  - Keywords (include/exclude)
  - Sources (include/exclude)
  - Locations
  - Max events
  - Date range

## Tips & Tricks

### Finding Event UIDs
- Browse Events page shows UID below each event
- Copy the UID to add specific events to feeds

### Using Keywords Effectively
**Include Keywords** - Events must match at least one:
- `music`, `concert`, `band`
- `art`, `gallery`, `exhibit`
- `family`, `kids`, `children`

**Exclude Keywords** - Filter out unwanted events:
- `21+`, `adults only`
- `bar crawl`
- Any terms you don't want

### Location Filtering
- Case-insensitive matching
- Matches anywhere in location text
- Examples: `Eagle River`, `Boulder Junction`, `Minocqua`

### Source Filtering
**Include Sources** - Only these sources:
- `boulder-junction-tec`
- `eagle-river-chamber-tec`

**Exclude Sources** - Skip these sources:
- `some-source-to-avoid`

### Multiple Feeds for Different Purposes
Create separate feeds for:
- Family events
- Music & concerts
- Outdoor activities
- Weekend events
- Location-specific events

## Troubleshooting

### "No events found"
**Solution:** Run the pipeline first
```bash
python -m src.main
```

### Port Already in Use
**Solution:** Use different port
```bash
PORT=8080 python src/web_app.py
```

### Changes Not Saving
**Solution:** Check file permissions
```bash
chmod 644 config/curated.yaml
```

### Feed Not Generating
**Solution:** 
1. Make sure feed is enabled
2. Check that preferences aren't too restrictive
3. Verify events exist in date range

## Next Steps

1. ✅ **Create your first feed** (see tutorial above)
2. 📚 **Read the full guide**: [docs/WEB_INTERFACE_GUIDE.md](docs/WEB_INTERFACE_GUIDE.md)
3. 🎯 **Customize feeds** with your preferences
4. 📱 **Subscribe in calendar app** (Google, Apple, Outlook)
5. 🔄 **Set up automation** to run pipeline daily

## URL Reference

- Homepage: `http://localhost:5000/`
- Browse Events: `http://localhost:5000/browse`
- Create Feed: `http://localhost:5000/new-feed`
- Edit Feed: `http://localhost:5000/feed/<feed-id>`
- Download ICS: `http://localhost:5000/curated/<feed-id>.ics`

## API Examples (Advanced)

### Get All Feeds
```bash
curl http://localhost:5000/api/feeds
```

### Create Feed via API
```bash
curl -X POST http://localhost:5000/api/feeds \
  -H "Content-Type: application/json" \
  -d '{
    "id": "my-events",
    "name": "My Events",
    "enabled": true,
    "selected_events": [],
    "preferences": {
      "keywords": ["music"],
      "max_auto_events": 20
    }
  }'
```

### Generate Feed
```bash
curl -X POST http://localhost:5000/api/generate \
  -H "Content-Type: application/json" \
  -d '{"feed_id": "my-events"}'
```

## Getting Help

- **Full Documentation**: [docs/WEB_INTERFACE_GUIDE.md](docs/WEB_INTERFACE_GUIDE.md)
- **Curated Feeds Guide**: [docs/CURATED_FEEDS_GUIDE.md](docs/CURATED_FEEDS_GUIDE.md)
- **Check report.json** for pipeline details
- **Look at browser console** for client-side errors
- **Check terminal** where web server is running for server errors

## Example Feed Configurations

### Music Events
```
Keywords: music, concert, band, jazz, rock, performance
Exclude: karaoke
Max Events: 30
Days Ahead: 90
```

### Family Activities
```
Keywords: family, kids, children, festival
Exclude: 21+, adults only
Include Sources: eagle-river-chamber-tec, boulder-junction-tec
Max Events: 50
Days Ahead: 60
```

### Outdoor Adventures
```
Keywords: hiking, biking, fishing, kayak, trail, outdoor
Locations: Eagle River, Boulder Junction
Max Events: unlimited (0)
Days Ahead: 120
```

### Weekend Events
```
(Currently requires manual selection, automatic day-of-week filtering coming soon)
```

Happy event curating! 🎉
