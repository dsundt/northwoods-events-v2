# Music Service Integration Examples

## Overview

This document shows how to integrate different music services into the reel generation backend.

## Table of Contents
1. [Mubert AI (Already Implemented)](#mubert-ai-already-implemented)
2. [Pre-Downloaded Library](#pre-downloaded-library)
3. [Epidemic Sound API (Unofficial)](#epidemic-sound-api-unofficial)
4. [No Music Approach](#no-music-approach)

---

## Mubert AI (Already Implemented)

### Status: ✅ Ready to Use

This is already implemented in `api/generate-reel.js`.

### Setup

```bash
# Add API key to Vercel
vercel env add MUBERT_API_KEY
# Paste: amb_xxxxxxxxxxxxxxxx

# Redeploy
vercel --prod
```

### Code Example

```javascript
// In api/generate-reel.js (already exists)
async function addBackgroundMusic(videoUrl, event, mubertApiKey) {
  const tags = determineMusicTags(event.title);
  
  const response = await fetch('https://api.mubert.com/v2/RecordTrack', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      license: mubertApiKey,
      duration: 20,
      tags: tags,
      mode: 'track',
      bitrate: 320,
    }),
  });
  
  const data = await response.json();
  return data.data.track_url;
}
```

### Usage

Check "Add Background Music" when generating reel. That's it!

---

## Pre-Downloaded Library

### Status: 🔧 Requires Setup

Use this for Epidemic Sound, Artlist, YouTube Audio Library, etc.

### Step 1: Download Tracks

1. Subscribe to service (Epidemic Sound, Artlist, etc.)
2. Download 10-20 tracks
3. Place in `/backend-example/music/` folder
4. Use descriptive filenames

### Step 2: Update music-selector.js

Edit `music-selector.js`:

```javascript
const musicLibrary = {
  upbeat: [
    'upbeat-outdoor-adventure.mp3',  // Your actual filenames
    'upbeat-summer-festival.mp3',
    'upbeat-celebration.mp3',
  ],
  calm: [
    'calm-ambient-peaceful.mp3',
    'calm-piano-reflection.mp3',
  ],
  // ... update with your tracks
};
```

### Step 3: Integrate into generate-reel.js

Replace the Mubert section with:

```javascript
// At top of file
const { selectMusic } = require('../music-selector');
const { promisify } = require('util');
const { exec } = require('child_process');
const fs = require('fs').promises;
const execAsync = promisify(exec);

// In the addMusic section
if (addMusic) {
  console.log('Selecting music from library...');
  
  // Select appropriate track
  const musicPath = selectMusic(event);
  
  // Temporary file paths
  const videoPath = '/tmp/video.mp4';
  const outputPath = '/tmp/output.mp4';
  
  // Download video
  const videoResponse = await fetch(videoUrl);
  const videoBuffer = await videoResponse.buffer();
  await fs.writeFile(videoPath, videoBuffer);
  
  // Merge video and music with FFmpeg
  console.log('Merging video and music...');
  await execAsync(
    `ffmpeg -i ${videoPath} -i ${musicPath} ` +
    `-c:v copy -c:a aac -b:a 192k ` +
    `-map 0:v:0 -map 1:a:0 -shortest ` +
    `${outputPath}`
  );
  
  // Read merged video
  const finalVideoBuffer = await fs.readFile(outputPath);
  const finalVideoBase64 = finalVideoBuffer.toString('base64');
  
  // Clean up temp files
  await fs.unlink(videoPath).catch(() => {});
  await fs.unlink(outputPath).catch(() => {});
  
  return `data:video/mp4;base64,${finalVideoBase64}`;
}
```

### Step 4: Install FFmpeg on Vercel

Add to `package.json`:

```json
{
  "dependencies": {
    "node-fetch": "^2.6.7",
    "form-data": "^4.0.0",
    "@ffmpeg-installer/ffmpeg": "^1.1.0"
  }
}
```

Update code to use FFmpeg:

```javascript
const ffmpegPath = require('@ffmpeg-installer/ffmpeg').path;

// Use in exec:
await execAsync(
  `${ffmpegPath} -i ${videoPath} -i ${musicPath} ...`
);
```

### Pros & Cons

**Pros:**
- ✅ Professional quality (Epidemic/Artlist)
- ✅ Full control over tracks
- ✅ No per-track API cost

**Cons:**
- ❌ Manual music management
- ❌ Subscription cost ($10-15/mo)
- ❌ More complex backend (FFmpeg)
- ❌ Larger deployment size
- ❌ Slower generation (video processing)

---

## Epidemic Sound API (Unofficial)

### Status: ⚠️ No Official API

Epidemic Sound does not provide a public API. However, you can:

### Option 1: Manual Download + Library

Use the pre-downloaded library approach above.

### Option 2: Web Scraping (Not Recommended)

**Don't do this!** It violates terms of service.

### Option 3: Request API Access

Contact Epidemic Sound enterprise team for API access (likely expensive).

---

## No Music Approach

### Status: ✅ Recommended!

Generate videos WITHOUT music, add later in Instagram app.

### Benefits

1. **FREE** - No music service cost
2. **Simpler backend** - No FFmpeg needed
3. **Faster generation** - No video processing
4. **Better music** - Use Instagram's huge library
5. **More flexible** - Change music anytime
6. **Better licensing** - Instagram handles it

### Implementation

In `api/generate-reel.js`, simply return the video without music:

```javascript
// After video generation
return res.status(200).json({
  success: true,
  videoUrl: videoUrl,
  duration: 20,
  message: 'Reel generated successfully! Add music in Instagram app.',
});
```

### User Workflow

1. Generate reel (2-5 minutes)
2. Download video
3. Open Instagram app
4. Upload reel
5. Tap "Add Music"
6. Search and select track
7. Post!

**Time to add music:** 30 seconds

---

## Comparison Table

| Approach | Cost | Quality | Automation | Complexity | Recommended |
|----------|------|---------|------------|------------|-------------|
| **No Music** | $0 | ⭐⭐⭐⭐⭐ | Manual | Very Low | ✅ Best |
| **Mubert AI** | $14/mo | ⭐⭐⭐⭐ | Full | Low | ✅ Good |
| **Pre-Downloaded** | $10-15/mo | ⭐⭐⭐⭐⭐ | Full | High | ⚠️ Complex |
| **Manual Selection** | Varies | ⭐⭐⭐⭐⭐ | None | Low | ⚠️ Slow |

---

## My Recommendation

### For Most Users: No Music

**Reasons:**
1. Generate video without music
2. Add music in Instagram app (30 seconds)
3. Save $10-15/month
4. Access to millions of songs
5. Latest trending tracks
6. Zero licensing issues

### For Full Automation: Mubert AI

**Reasons:**
1. Already implemented
2. Fully automated
3. Reasonable cost ($14/mo)
4. Good quality
5. API-based (reliable)

### Avoid: Pre-Downloaded Library

**Reasons:**
1. Complex FFmpeg setup
2. Large deployment size
3. Slower generation
4. Manual music management
5. Not much better than Mubert AI

---

## Code Snippets

### Test Mubert API

```bash
curl -X POST https://api.mubert.com/v2/RecordTrack \
  -H "Content-Type: application/json" \
  -d '{
    "license": "YOUR_API_KEY",
    "duration": 20,
    "tags": "upbeat,outdoor,adventure",
    "mode": "track",
    "bitrate": 320
  }'
```

### Test Music Selector

```javascript
// Test music-selector.js
const { selectMusic, validateMusicLibrary } = require('./music-selector');

// Validate library
const errors = validateMusicLibrary();
console.log('Library errors:', errors);

// Test selection
const event = {
  title: 'Minocqua Music Festival',
  location: 'Minocqua, WI',
  start_utc: '2025-07-15T18:00:00Z'
};

const musicPath = selectMusic(event);
console.log('Selected:', musicPath);
```

### FFmpeg Test Command

```bash
# Test FFmpeg video/music merge
ffmpeg -i video.mp4 -i music.mp3 \
  -c:v copy -c:a aac -b:a 192k \
  -map 0:v:0 -map 1:a:0 -shortest \
  output.mp4
```

---

## Troubleshooting

### Problem: "FFmpeg not found"

**Solution for Vercel:**
```bash
npm install @ffmpeg-installer/ffmpeg
```

```javascript
const ffmpegPath = require('@ffmpeg-installer/ffmpeg').path;
```

### Problem: "Music file not found"

**Solution:**
1. Check file exists: `ls -la music/`
2. Verify filename matches `musicLibrary` in `music-selector.js`
3. Run: `validateMusicLibrary()` to find errors

### Problem: "Deployment size too large"

**Cause:** Music files make deployment > 50MB

**Solutions:**
1. Use fewer tracks (5-10 instead of 20)
2. Use lower bitrate (128kbps instead of 320kbps)
3. Use shorter clips (10 seconds instead of full songs)
4. Or: Use Mubert AI instead (no file storage)

### Problem: "FFmpeg timeout"

**Cause:** Video processing takes too long

**Solution:**
1. Increase `maxDuration` in `vercel.json` to 900s (Pro plan)
2. Or: Generate video without music (faster)

---

## Summary

**Best approach for most users:**
1. ✅ Generate reels WITHOUT music
2. ✅ Add music in Instagram app
3. ✅ FREE, easy, flexible

**If you must automate:**
1. ✅ Use Mubert AI (already implemented)
2. ✅ $14/month, good quality
3. ✅ Zero setup complexity

**Avoid unless you have specific needs:**
1. ❌ Pre-downloaded library (too complex)
2. ❌ Epidemic Sound API (doesn't exist)

---

**Questions?** See `/docs/MUSIC_SOURCES_GUIDE.md` for detailed service comparisons!
