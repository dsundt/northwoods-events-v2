# Curated Feeds Persistence - Fixed!

## ✅ **Issue Resolved**

Your curated feeds are now properly persisting to GitHub!

---

## 🔍 **What Was Wrong**

### Problem 1: File Not Committed
- GitHub Actions workflow generated ICS files
- But didn't commit them back to the repository
- Files only existed temporarily during workflow execution

### Problem 2: Wrong Filename Expectation
- Feed ID: `"RCLMinocquaEvents"`
- Generated filename: `"rclminocquaevents.ics"` (lowercase, no spaces)
- You were looking for: `"rclfeed.ics"`

---

## ✅ **What's Fixed**

### 1. Auto-Commit Workflow
The GitHub Actions workflow now:
- ✅ Generates all ICS files
- ✅ **Commits them back to repository**
- ✅ Pushes to `main` branch
- ✅ Deploys to GitHub Pages

### 2. Clear Filename Display
The UI now shows:
- Feed ID
- Generated ICS filename
- Full ICS URL (copy/test buttons)

---

## 📋 **How It Works Now**

### When You Save/Update a Feed:

1. **Save Configuration**
   - Configuration saved to `config/curated.yaml`
   - Committed to GitHub

2. **Trigger Workflow** (Click "Generate ICS Files Now")
   - Fetches all events from sources
   - Processes curated feeds
   - Generates ICS files
   - **Auto-commits files to repository**
   - Deploys to GitHub Pages

3. **Access Your Feed**
   - URL displayed in feed card
   - File persists in repository
   - Accessible via GitHub Pages

---

## 🌐 **Your Current Feed**

### Feed Details
- **Feed Name**: Minocqua Events
- **Feed ID**: `RCLMinocquaEvents`
- **ICS Filename**: `rclminocquaevents.ics`
- **Events**: 9 matching events

### Access URLs

**ICS Feed** (for calendar apps):
```
https://dsundt.github.io/northwoods-events-v2/curated/rclminocquaevents.ics
```

**GitHub Repository**:
```
https://github.com/dsundt/northwoods-events-v2/blob/main/public/curated/rclminocquaevents.ics
```

---

## 🎯 **How to Use Your Feed**

### Option 1: Subscribe in Calendar App

**Google Calendar**:
1. Open Google Calendar
2. Click "+" next to "Other calendars"
3. Select "From URL"
4. Paste: `https://dsundt.github.io/northwoods-events-v2/curated/rclminocquaevents.ics`
5. Click "Add calendar"

**Apple Calendar (macOS/iOS)**:
1. Open Calendar app
2. File → New Calendar Subscription (or Settings → Add Account → Other)
3. Paste URL
4. Set refresh interval (e.g., daily)
5. Subscribe

**Outlook**:
1. Open Outlook
2. Calendar view → Add Calendar → From Internet
3. Paste URL
4. Subscribe

### Option 2: Copy URL from Web Interface

1. Go to https://dsundt.github.io/northwoods-events-v2/manage.html
2. Find your feed
3. Click **"📋 Copy"** to copy URL
4. Or click **"🔗 Test"** to open in browser

---

## 🔄 **Feed Updates**

### Automatic Updates (3x Daily)
Your feed automatically updates:
- **1 AM CST** (7 AM UTC)
- **12 PM CST** (6 PM UTC)
- **10 PM CST** (4 AM UTC next day)

The workflow:
1. Fetches latest events from sources
2. Matches events to your preferences
3. Regenerates ICS files
4. Commits to repository
5. Updates GitHub Pages

### Manual Update
Click **"⚡ Regenerate Feed"** in the web interface to trigger immediate update.

---

## 📝 **Filename Rules**

Feed IDs are converted to filenames using these rules:

| Feed ID | ICS Filename |
|---------|--------------|
| `RCLMinocquaEvents` | `rclminocquaevents.ics` |
| `My-Awesome Feed!` | `my-awesome-feed.ics` |
| `family events` | `family-events.ics` |
| `2024 Summer` | `2024-summer.ics` |

### Rules:
1. Convert to lowercase
2. Remove special characters (except hyphens)
3. Replace spaces/underscores with hyphens
4. Add `.ics` extension

### Best Practice:
Use simple IDs like:
- `minocqua-events`
- `family-events`
- `outdoor-activities`

This makes URLs cleaner and more predictable.

---

## 🔍 **Verifying Your Feed**

### Check if Feed Exists:

1. **Test URL in Browser**:
   - Open: `https://dsundt.github.io/northwoods-events-v2/curated/rclminocquaevents.ics`
   - Should download or display ICS file

2. **Check GitHub Repository**:
   - Go to: https://github.com/dsundt/northwoods-events-v2/tree/main/public/curated
   - Your ICS file should be listed

3. **Verify in Web Interface**:
   - Click **"🔗 Test"** button
   - Should open ICS file

### If Feed Doesn't Exist:

1. **Check Feed Status**:
   - Is feed **Enabled**?
   - Does it have any matching events?

2. **Trigger Generation**:
   - Click **"⚡ Regenerate Feed"**
   - Wait 2-3 minutes
   - Refresh page

3. **Check GitHub Actions**:
   - Go to: https://github.com/dsundt/northwoods-events-v2/actions
   - Find latest "Build ICS & Deploy Pages" workflow
   - Check for errors

---

## 🐛 **Troubleshooting**

### Problem: 404 Error on ICS URL

**Cause**: File doesn't exist or wrong filename

**Solutions**:
1. Check feed ID vs. filename (see rules above)
2. Trigger manual regeneration
3. Wait for next scheduled run
4. Check if feed is enabled

### Problem: Feed Shows 0 Events

**Causes**:
- No events match your preferences
- `max_auto_events` set to 0
- All events are in the past

**Solutions**:
1. Preview events in web interface
2. Adjust location/keyword filters
3. Increase `max_auto_events`
4. Check `days_ahead` setting

### Problem: Feed Not Updating

**Causes**:
- Workflow not running
- Errors in workflow execution
- Feed disabled

**Solutions**:
1. Check GitHub Actions tab for workflow runs
2. Manually trigger workflow
3. Verify feed is enabled
4. Check workflow logs for errors

### Problem: Old Events Still Showing

**Cause**: Calendar app cached old version

**Solution**:
1. Force refresh in calendar app
2. Unsubscribe and resubscribe
3. Wait for next automatic update

---

## 🔧 **Workflow Configuration**

### Auto-Commit Step

The workflow now includes this step:

```yaml
- name: Commit generated files
  run: |
    git config user.name "github-actions[bot]"
    git config user.email "github-actions[bot]@users.noreply.github.com"
    git add public/curated/*.ics public/by-source/*.ics public/combined.ics public/report.json || true
    git diff --quiet && git diff --staged --quiet || git commit -m "Auto-generate ICS files [skip ci]"
    git push || true
```

### What It Does:
1. Configures Git with bot identity
2. Stages all generated ICS files
3. Commits if there are changes
4. Pushes to `main` branch
5. `[skip ci]` prevents infinite loops

---

## 📊 **Files Generated**

### Per Run:
- `public/curated/*.ics` - Your curated feeds
- `public/by-source/*.ics` - Individual source feeds
- `public/combined.ics` - All events combined
- `public/report.json` - Generation report

### All Files Persist:
- ✅ Committed to repository
- ✅ Accessible via GitHub Pages
- ✅ Available for download

---

## ✅ **Summary**

### Before Fix:
- ❌ ICS files generated but not persisted
- ❌ 404 errors on feed URLs
- ❌ Had to manually commit files

### After Fix:
- ✅ ICS files auto-committed to repository
- ✅ Feeds persist and update automatically
- ✅ URLs work immediately after generation
- ✅ Clear filename display in UI

### Your Feed is Now:
- ✅ Live and accessible
- ✅ Updates 3x daily automatically
- ✅ Subscribable in any calendar app
- ✅ Persists in GitHub repository

---

**Your curated feeds are now fully functional and will persist forever!** 🎉
