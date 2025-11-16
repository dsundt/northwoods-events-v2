# 🎵 Music Sources for Instagram Reels - Complete Guide

## Table of Contents
1. [Overview & Comparison](#overview--comparison)
2. [Mubert AI (AI-Generated)](#mubert-ai-ai-generated)
3. [Epidemic Sound](#epidemic-sound)
4. [Artlist](#artlist)
5. [AudioJungle](#audiojungle)
6. [YouTube Audio Library](#youtube-audio-library)
7. [Free Music Archive](#free-music-archive)
8. [Incompetech](#incompetech)
9. [Instagram's Built-in Music](#instagrams-built-in-music)
10. [Implementation Guide](#implementation-guide)
11. [Recommendations](#recommendations)

---

## Overview & Comparison

### Quick Comparison Table

| Service | Type | Cost | API | Quality | Licensing | Best For |
|---------|------|------|-----|---------|-----------|----------|
| **Beatoven.ai** | AI-Generated | Free-$20/mo | ✅ Yes | ⭐⭐⭐⭐⭐ | Commercial OK | Auto-matching |
| **Instagram Music** | Built-in | Free | N/A | ⭐⭐⭐⭐⭐ | Instagram only | Best option! |
| **Epidemic Sound** | Curated Library | $15/mo | ❌ No | ⭐⭐⭐⭐⭐ | Commercial OK | Professionals |
| **Artlist** | Curated Library | $9.99/mo | ❌ No | ⭐⭐⭐⭐⭐ | Commercial OK | Budget-friendly |
| **AudioJungle** | Marketplace | $1-50/track | ❌ No | ⭐⭐⭐⭐ | Per-track | One-off needs |
| **Mubert AI** | AI-Generated | Free-$14/mo | ✅ Yes | ⭐⭐⭐⭐ | Commercial OK | Alternative AI |
| **YouTube Audio** | Free Library | Free | ❌ No | ⭐⭐⭐ | Attribution | Testing |
| **Free Music Archive** | Community | Free | ❌ No | ⭐⭐⭐ | Varies | Non-commercial |
| **Incompetech** | Free Library | Free | ❌ No | ⭐⭐ | Attribution | Budget projects |

### Selection Criteria

**Choose based on:**
1. **Budget:** Free vs. Subscription vs. Per-track
2. **Automation:** Need API integration?
3. **Licensing:** Commercial use required?
4. **Quality:** Professional vs. adequate
5. **Effort:** Auto-matching vs. manual selection

---

## Beatoven.ai (AI-Generated)

### ⭐ Recommended for Automation

**What it is:** Advanced AI music generation that creates emotion-based, original soundtracks tailored to your content's mood and genre.

**UPDATE:** This is now the primary AI music service integrated into the solution!

### Pros
- ✅ **API available** - Perfect for automation
- ✅ **Emotion-based AI** - Intelligent mood and genre matching
- ✅ **High quality** - Professional, human-like compositions
- ✅ **Custom duration** - Matches video exactly
- ✅ **Full control** - Genre, mood, tempo, instruments
- ✅ **Royalty-free** - Commercial use included
- ✅ **Unique tracks** - Every composition is original
- ✅ **Fast generation** - 30-60 seconds per track

### Cons
- ❌ **Paid only at scale** - Free tier limited to 15 min/month
- ❌ **Requires account** - API key needed

### Pricing

| Plan | Cost | Minutes/Month | API Access | Commercial Use |
|------|------|---------------|------------|----------------|
| **Free** | $0 | 15 min | ✅ Yes | Personal only |
| **Pro** | $20/mo | Unlimited | ✅ Yes | ✅ Yes |
| **Enterprise** | Custom | Unlimited | ✅ Yes | ✅ Yes |

**Best for:** Unlimited reels with Pro plan ($20/month)

### API Documentation

**Endpoint:** `POST https://api.beatoven.ai/api/v1/tracks`

**Request:**
```javascript
POST https://api.beatoven.ai/api/v1/tracks
Authorization: Bearer YOUR_API_KEY
Content-Type: application/json

{
  "title": "Event Name - Background Music",
  "duration": 20,           // seconds
  "genre": "Folk",          // Genre type
  "mood": "Uplifting",      // Emotion/mood
  "tempo": "Medium",        // Slow, Medium, Fast
  "instruments": ["Acoustic Guitar", "Strings", "Percussion"],
  "format": "mp3",          // mp3 or wav
  "sample_rate": 44100,     // Audio quality
  "bit_depth": 16           // Audio quality
}
```

**Response:**
```javascript
{
  "track_id": "trk_abc123xyz",
  "status": "processing",
  "estimated_time": 45      // seconds
}
```

**Check Status:** `GET https://api.beatoven.ai/api/v1/tracks/{track_id}`

**Completed Response:**
```javascript
{
  "track_id": "trk_abc123xyz",
  "status": "completed",
  "download_url": "https://beatoven.ai/downloads/abc123.mp3",
  "duration": 20
}
```

### Parameter Examples

**Event Type → Music Parameters:**
```javascript
const musicParams = {
  "music festival": {
    genre: "Electronic",
    mood: "Energetic",
    tempo: "Fast",
    instruments: ["Synth", "Bass", "Drums"]
  },
  "art gallery": {
    genre: "Ambient",
    mood: "Calm",
    tempo: "Slow",
    instruments: ["Piano", "Strings"]
  },
  "sports event": {
    genre: "Rock",
    mood: "Motivational",
    tempo: "Fast",
    instruments: ["Guitar", "Drums", "Bass"]
  },
  "food festival": {
    genre: "Acoustic",
    mood: "Happy",
    tempo: "Medium",
    instruments: ["Acoustic Guitar", "Piano"]
  },
  "outdoor adventure": {
    genre: "Folk",
    mood: "Inspiring",
    tempo: "Medium",
    instruments: ["Acoustic Guitar", "Strings"]
  }
};
```

### Get API Key

1. Sign up: https://www.beatoven.ai/
2. Go to: Dashboard → Settings → API Keys
3. Click: "Generate New API Key"
4. Copy key (save securely!)

### Implementation (Already in your backend!)

```javascript
// In backend-example/api/generate-reel.js
async function addBackgroundMusic(videoUrl, event, beatovenApiKey) {
  const musicParams = determineMusicParameters(event.title, event.start_utc);
  
  const createResponse = await fetch('https://api.beatoven.ai/api/v1/tracks', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${beatovenApiKey}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      title: `${event.title} - Background Music`,
      duration: 20,
      genre: musicParams.genre,
      mood: musicParams.mood,
      tempo: musicParams.tempo,
      instruments: musicParams.instruments,
      format: 'mp3',
    }),
  });
  
  const createData = await createResponse.json();
  return createData.track_id;
}
```

**See full documentation:** `/docs/BEATOVEN_AI_GUIDE.md`

---

## Epidemic Sound

### ⭐ Best Quality, No API

**What it is:** Professional music library used by major YouTubers and brands.

### Pros
- ✅ **Highest quality** - Professional, polished tracks
- ✅ **Huge library** - 40,000+ tracks
- ✅ **Sound effects** - 90,000+ SFX included
- ✅ **Commercial license** - All platforms
- ✅ **Easy search** - Filter by mood, genre, tempo
- ✅ **Stems available** - Adjust individual instruments

### Cons
- ❌ **No API** - Manual download required
- ❌ **Subscription required** - No free tier
- ❌ **More expensive** - $15-49/month

### Pricing

| Plan | Cost | Use Case |
|------|------|----------|
| **Personal** | $15/mo | YouTube, podcasts |
| **Commercial** | $49/mo | All platforms, unlimited channels |

### How to Use

**Manual Process:**
1. Browse: https://www.epidemicsound.com/music/
2. Search by mood: "Upbeat Outdoor"
3. Preview tracks
4. Download MP3 (320kbps)
5. Store in `/public/music/` folder
6. Reference in backend code

**Workflow for Reels:**
1. Create a small library of ~20 tracks covering different moods
2. Backend picks from pre-downloaded tracks
3. Merge with video using FFmpeg

### Sample Library Structure

```
/public/music/
├── upbeat-outdoor-1.mp3
├── upbeat-outdoor-2.mp3
├── calm-ambient-1.mp3
├── energetic-rock-1.mp3
├── acoustic-folk-1.mp3
└── ...
```

### Implementation

```javascript
// Backend selects from pre-downloaded tracks
function selectMusic(eventTitle) {
  const tracks = {
    'upbeat': ['upbeat-outdoor-1.mp3', 'upbeat-outdoor-2.mp3'],
    'calm': ['calm-ambient-1.mp3', 'calm-ambient-2.mp3'],
    'energetic': ['energetic-rock-1.mp3', 'energetic-rock-2.mp3'],
  };
  
  const mood = determineMood(eventTitle);
  const moodTracks = tracks[mood] || tracks['upbeat'];
  const randomTrack = moodTracks[Math.floor(Math.random() * moodTracks.length)];
  
  return `/public/music/${randomTrack}`;
}
```

---

## Artlist

### 💰 Budget-Friendly, High Quality

**What it is:** Unlimited music and SFX subscription service.

### Pros
- ✅ **Great value** - $9.99/month for unlimited
- ✅ **High quality** - Professional tracks
- ✅ **Unlimited downloads**
- ✅ **Perpetual license** - Keep using after cancellation
- ✅ **Good search** - Mood, instrument, vocal/instrumental

### Cons
- ❌ **No API** - Manual process
- ❌ **Smaller library** - ~20,000 tracks (vs Epidemic's 40,000)

### Pricing

| Plan | Cost | Includes |
|------|------|----------|
| **Music** | $9.99/mo | Unlimited music downloads |
| **Music + SFX** | $14.99/mo | Music + sound effects |
| **Max** | $24.99/mo | Music, SFX, footage |

### How to Use

Same as Epidemic Sound - build a library of pre-downloaded tracks.

---

## AudioJungle

### 🎯 Pay-Per-Track

**What it is:** Marketplace for individual track purchases.

### Pros
- ✅ **No subscription** - Pay only for what you use
- ✅ **Huge selection** - 2 million+ tracks
- ✅ **Affordable** - $1-50 per track
- ✅ **Specific searches** - Find exactly what you need
- ✅ **Commercial licenses** - Extended licenses available

### Cons
- ❌ **No API** - Manual purchase
- ❌ **Adds up** - $5-20 per track (expensive at scale)
- ❌ **License per project** - Need to track usage

### Pricing

| License Type | Cost | Usage |
|--------------|------|-------|
| **Standard** | $1-20 | Single end product |
| **Music License** | $19 | Web, social media |
| **Broadcast License** | $99+ | TV, radio, film |

### When to Use

- One-off special events
- High-profile campaigns
- Need a very specific track

---

## YouTube Audio Library

### 🆓 Free, No API

**What it is:** Google's free music library for creators.

### Pros
- ✅ **Completely free**
- ✅ **No account needed**
- ✅ **Good quality**
- ✅ **Clear licensing** - Most tracks are public domain

### Cons
- ❌ **No API** - Manual download
- ❌ **Attribution required** - For some tracks
- ❌ **Limited selection** - ~2000 tracks
- ❌ **Overused** - Many people use same tracks

### How to Access

1. Go to: https://studio.youtube.com/
2. Click: **Audio Library** (left sidebar)
3. Filter by: Mood, Genre, Instrument, Duration
4. Download MP3

### Implementation

Build a library of downloaded tracks, same as Epidemic Sound.

---

## Free Music Archive

### 🎨 Community-Driven, Free

**What it is:** Curated library of free, legal music.

### Pros
- ✅ **Free**
- ✅ **Creative Commons** - Various licenses
- ✅ **Curated** - Quality control
- ✅ **Unique tracks** - Less common than YouTube

### Cons
- ❌ **No API** - Manual download
- ❌ **Mixed quality** - Not all professional
- ❌ **License varies** - Check each track
- ❌ **Attribution required** - Most tracks

### Website

https://freemusicarchive.org/

### Licensing

Check each track for:
- **CC BY** - Attribution required
- **CC BY-NC** - Non-commercial only
- **CC BY-SA** - Share-alike
- **CC0** - Public domain (best!)

---

## Incompetech

### 🎼 Free with Attribution

**What it is:** Kevin MacLeod's royalty-free music library.

### Pros
- ✅ **Free**
- ✅ **Large library** - 2000+ tracks
- ✅ **Search by feel** - Mood-based
- ✅ **Commercial use OK** - With attribution

### Cons
- ❌ **Attribution required** - Must credit in video/description
- ❌ **Basic quality** - MIDI-generated
- ❌ **Very common** - Overused in amateur content

### Website

https://incompetech.com/music/

### Licensing

**Free with attribution:**
```
Music: "Track Name" by Kevin MacLeod (incompetech.com)
Licensed under Creative Commons: By Attribution 4.0 License
```

**Or:** Pay $30 for attribution-free license

---

## Instagram's Built-in Music

### 🏆 BEST OPTION (After Upload)

**What it is:** Add music directly in Instagram app when posting.

### Pros
- ✅ **FREE** - Completely free
- ✅ **Huge library** - Millions of tracks
- ✅ **Licensed** - Instagram handles licensing
- ✅ **Trending songs** - Latest popular music
- ✅ **No attribution needed**
- ✅ **Perfect sync** - Built into the app

### Cons
- ❌ **Manual process** - Must add in app
- ❌ **After generation** - Can't be automated
- ❌ **Instagram only** - Not for other platforms

### How to Use

1. Generate reel without music (saves cost!)
2. Download video
3. Upload to Instagram
4. Tap: **Add Music** when posting
5. Search and select track
6. Adjust timing and volume
7. Post!

### Why This Is Best

- **No cost** - Save $14/month on Mubert
- **Better selection** - Current popular songs
- **Easier licensing** - Instagram handles it
- **More control** - Adjust in real-time
- **Better matching** - You pick the perfect song

---

## Implementation Guide

### Option 1: Mubert AI (Automated)

**Already implemented in your backend!**

**Setup:**
```bash
# Add API key to Vercel
vercel env add MUBERT_API_KEY
# Paste your key: amb_xxxxxxxxxxxxxxxx
```

**Enable in UI:**
- Check "Add Background Music" when generating reel
- Backend automatically generates matching track
- Music merged with video

**Cost:** $0 (free tier) or $14/mo (unlimited)

---

### Option 2: Pre-Downloaded Library

**Best for:** Epidemic Sound, Artlist, YouTube Audio Library

#### Step 1: Build Music Library

Create folder structure:
```
/backend-example/music/
├── upbeat-1.mp3
├── upbeat-2.mp3
├── calm-1.mp3
├── energetic-1.mp3
└── ...
```

Download 10-20 tracks covering different moods.

#### Step 2: Update Backend

Create `/backend-example/music-selector.js`:

```javascript
const fs = require('fs');
const path = require('path');

const musicLibrary = {
  upbeat: ['upbeat-1.mp3', 'upbeat-2.mp3', 'upbeat-3.mp3'],
  calm: ['calm-1.mp3', 'calm-2.mp3'],
  energetic: ['energetic-1.mp3', 'energetic-2.mp3'],
  acoustic: ['acoustic-1.mp3', 'acoustic-2.mp3'],
  electronic: ['electronic-1.mp3', 'electronic-2.mp3'],
};

function selectMusic(eventTitle) {
  const title = eventTitle.toLowerCase();
  
  // Determine mood from event title
  let mood = 'upbeat'; // default
  
  if (title.includes('art') || title.includes('gallery')) {
    mood = 'calm';
  } else if (title.includes('sport') || title.includes('race')) {
    mood = 'energetic';
  } else if (title.includes('music') || title.includes('festival')) {
    mood = 'electronic';
  } else if (title.includes('food') || title.includes('wine')) {
    mood = 'acoustic';
  }
  
  // Pick random track from mood category
  const tracks = musicLibrary[mood];
  const randomTrack = tracks[Math.floor(Math.random() * tracks.length)];
  
  return path.join(__dirname, 'music', randomTrack);
}

module.exports = { selectMusic };
```

#### Step 3: Update API Handler

In `/backend-example/api/generate-reel.js`:

```javascript
const { selectMusic } = require('../music-selector');

// Replace Mubert code with:
if (addMusic) {
  console.log('Selecting music from library...');
  const musicPath = selectMusic(event.title);
  
  // Merge with FFmpeg (same as before)
  await execAsync(
    `ffmpeg -i ${videoPath} -i ${musicPath} -c:v copy -c:a aac -map 0:v:0 -map 1:a:0 -shortest ${outputPath}`
  );
}
```

**Pros:**
- ✅ Professional quality (Epidemic/Artlist)
- ✅ No per-track cost
- ✅ Consistent results

**Cons:**
- ❌ Manual music management
- ❌ Subscription cost ($10-15/mo)
- ❌ Need FFmpeg in serverless (complex)

---

### Option 3: No Music (Recommended)

**Generate videos WITHOUT music:**

**Advantages:**
1. **Lower cost** - Save $14/mo on Mubert
2. **Faster generation** - No music processing
3. **Simpler backend** - No FFmpeg needed
4. **More flexible** - Add music in Instagram app
5. **Better licensing** - Use Instagram's library

**Workflow:**
1. Generate reel (no music)
2. Download video
3. Upload to Instagram
4. Add music in Instagram app
5. Post!

**This is the RECOMMENDED approach!**

---

## Recommendations

### For Most Users: No Music + Instagram

**Best workflow:**
1. Generate reel without music
2. Add music in Instagram app when posting
3. **Benefits:**
   - FREE
   - Huge song library
   - Latest trending music
   - No licensing issues
   - Saves backend complexity

### For Automation: Beatoven.ai (NEW!)

**If you must automate music:**
- Use Beatoven.ai (now integrated!)
- Free tier: 15 minutes/month (~45 reels)
- Pro: $20/month unlimited
- Higher quality than Mubert AI
- Emotion-based matching
- Better customization

### Alternative AI: Mubert AI

**Previous solution (still works):**
- Use Mubert AI for simpler needs
- Free tier: 25 tracks/month
- Pro: $14/month unlimited
- Good quality, tag-based matching
- See documentation for implementation

### For High Quality: Epidemic Sound + Manual

**If you want best quality:**
1. Subscribe to Epidemic Sound ($15/mo)
2. Download 10-20 tracks
3. Store in backend
4. Use music selector (code above)
5. **Trade-off:** More complex but professional

### For Budget Projects: YouTube Audio Library

**If budget is tight:**
1. Download tracks from YouTube Audio Library (free)
2. Store in backend
3. Use music selector
4. **Watch out:** Attribution may be required

---

## Cost Comparison (Per Month)

**Scenario: 50 reels/month**

| Option | Setup | Monthly Cost | Quality | Effort |
|--------|-------|--------------|---------|--------|
| **No music + Instagram** | Easy | $0 | ⭐⭐⭐⭐⭐ | Low |
| **Beatoven.ai** | Easy | $20 | ⭐⭐⭐⭐⭐ | Very Low |
| **Mubert AI** | Easy | $14 | ⭐⭐⭐⭐ | Very Low |
| **Epidemic Sound** | Medium | $15 | ⭐⭐⭐⭐⭐ | Medium |
| **Artlist** | Medium | $10 | ⭐⭐⭐⭐ | Medium |
| **YouTube Library** | Medium | $0 | ⭐⭐⭐ | Medium |
| **Instagram only** | Easy | $0 | ⭐⭐⭐⭐⭐ | Low |

---

## My Recommendation

### 🏆 Best Approach: Instagram's Built-in Music

**Why:**
1. **FREE** - No additional cost
2. **Easy** - Add music when posting (30 seconds)
3. **Legal** - Instagram handles licensing
4. **Quality** - Professional tracks, latest songs
5. **Flexible** - Change your mind anytime

**Implementation:**
1. Keep backend simple (no music processing)
2. Generate video-only reels
3. User adds music in Instagram app
4. **Saves:** $14-20/month + backend complexity

### Alternative: Beatoven.ai for Full Automation

**If you want 100% hands-off:**
- Use Beatoven.ai (now integrated!)
- Cost: Free (15 min/mo) or $20/month (unlimited)
- Quality: Excellent (emotion-based AI)
- Effort: Zero (fully automated)
- Better than Mubert AI

---

## Implementation Summary

### Current Status
✅ **Beatoven.ai** - Now implemented in backend (recommended!)  
✅ **Mubert AI** - Previously implemented, still available  
❌ **Other services** - Require manual process

### To Enable Beatoven.ai
```bash
vercel env add BEATOVEN_API_KEY
# Paste: bv_xxxxxxxxxxxxxxxx (or your key format)
vercel --prod
```

Configure in web interface:
- Click "🎵 Beatoven.ai Key"
- Paste your API key
- Check "Add Background Music" when generating

### To Use Instagram Music (Recommended)
1. Generate reels without music
2. Download video
3. Upload to Instagram
4. Add music in app
5. Done!

---

**Questions? Need help implementing a specific music source?** Let me know! 🎵
