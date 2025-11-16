# 🎵 Beatoven.ai Music Generation Guide

## Overview

Beatoven.ai is an advanced AI music generation platform that creates original, emotion-based soundtracks perfectly tailored to your content. Unlike generic music libraries, Beatoven.ai generates unique compositions based on mood, genre, and instrumentation.

## Why Beatoven.ai?

### Advantages Over Other Services

✅ **Emotion-Based AI** - Music matched to your content's mood and feel  
✅ **Fully Customizable** - Control genre, mood, tempo, and instruments  
✅ **Unique Compositions** - Every track is original and copyright-free  
✅ **Commercial License** - Included in all plans  
✅ **High Quality** - Professional, human-like compositions  
✅ **API Available** - Full automation support  
✅ **Fast Generation** - 30-60 seconds per track  
✅ **Event-Aware** - Automatically matches event type  

### vs. Other AI Music Services

| Feature | Beatoven.ai | Mubert AI | AIVA | Soundraw |
|---------|-------------|-----------|------|----------|
| **Quality** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ |
| **Customization** | Excellent | Good | Limited | Good |
| **API** | ✅ Yes | ✅ Yes | ❌ No | ❌ No |
| **Unique Tracks** | Yes | Yes | Yes | Limited |
| **Event Matching** | Intelligent | Basic | Manual | Manual |
| **Pricing** | $20/mo | $14/mo | $15/mo | $20/mo |
| **Free Tier** | ✅ Yes | ✅ Yes | ❌ No | ❌ No |

---

## Pricing & Plans

### Free Tier
- **Cost:** $0
- **Tracks:** 15 minutes/month
- **Downloads:** MP3, WAV
- **License:** Personal use
- **API Access:** ✅ Yes
- **Best for:** Testing and personal projects

### Pro Plan (Recommended)
- **Cost:** $20/month
- **Tracks:** Unlimited
- **Downloads:** MP3, WAV, stems
- **License:** Commercial use
- **API Access:** ✅ Yes
- **Best for:** Content creators, businesses

### Enterprise Plan
- **Cost:** Custom
- **Everything in Pro, plus:**
  - Priority support
  - Custom licensing
  - Dedicated account manager
  - Volume discounts

**Cost per reel:** ~$0 (unlimited on Pro plan)

---

## Getting Started

### Step 1: Create Account

1. Go to: https://www.beatoven.ai/
2. Click: "Sign Up" or "Start Free Trial"
3. Enter email and create password
4. Verify email address
5. Complete onboarding (optional)

### Step 2: Get API Key

1. Log into Beatoven.ai dashboard
2. Go to: Settings → API Keys
3. Click: "Generate New API Key"
4. Copy key (starts with `bv_` or similar)
5. Save securely

**Important:** Keep your API key secret!

### Step 3: Add to Backend

```bash
# In your backend-example directory
vercel env add BEATOVEN_API_KEY
# Paste your API key when prompted

# Redeploy
vercel --prod
```

### Step 4: Configure Web Interface

1. Go to: https://dsundt.github.io/northwoods-events-v2/manage.html
2. Click: "🎵 Beatoven.ai Key" button
3. Paste your API key
4. Click: "Save Key"

✅ **Setup complete!**

---

## API Documentation

### Authentication

```http
Authorization: Bearer YOUR_API_KEY
```

### Create Track

**Endpoint:** `POST https://api.beatoven.ai/api/v1/tracks`

**Request:**
```json
{
  "title": "My Event - Background Music",
  "duration": 20,
  "genre": "Folk",
  "mood": "Uplifting",
  "tempo": "Medium",
  "instruments": ["Acoustic Guitar", "Strings", "Percussion"],
  "format": "mp3",
  "sample_rate": 44100,
  "bit_depth": 16
}
```

**Response:**
```json
{
  "track_id": "trk_abc123xyz",
  "status": "processing",
  "estimated_time": 45
}
```

### Check Status

**Endpoint:** `GET https://api.beatoven.ai/api/v1/tracks/{track_id}`

**Response (Processing):**
```json
{
  "track_id": "trk_abc123xyz",
  "status": "processing",
  "progress": 75
}
```

**Response (Completed):**
```json
{
  "track_id": "trk_abc123xyz",
  "status": "completed",
  "download_url": "https://beatoven.ai/downloads/abc123.mp3",
  "duration": 20,
  "file_size": 1048576
}
```

**Response (Failed):**
```json
{
  "track_id": "trk_abc123xyz",
  "status": "failed",
  "error": "Error message here"
}
```

---

## Music Parameters

### Genres

Beatoven.ai supports these genres:

| Genre | Best For | Example Events |
|-------|----------|----------------|
| **Folk** | Outdoor, nature events | Hiking, camping, farmers markets |
| **Acoustic** | Intimate, casual events | Food festivals, wine tastings |
| **Electronic** | Modern, energetic events | Music festivals, nightlife |
| **Rock** | Active, sports events | Races, competitions, games |
| **Ambient** | Calm, artistic events | Art galleries, exhibits |
| **Cinematic** | Dramatic, special events | Winter celebrations, premieres |
| **Pop** | General, upbeat events | Family events, celebrations |
| **Classical** | Formal, elegant events | Galas, formal dinners |

### Moods

| Mood | Emotion | When to Use |
|------|---------|-------------|
| **Uplifting** | Positive, hopeful | General events |
| **Energetic** | High-energy, exciting | Sports, festivals |
| **Calm** | Peaceful, relaxed | Art, meditation |
| **Happy** | Joyful, cheerful | Family, celebrations |
| **Motivational** | Inspiring, driving | Races, competitions |
| **Peaceful** | Serene, gentle | Nature, wellness |
| **Inspiring** | Moving, emotional | Fundraisers, ceremonies |
| **Relaxed** | Easy-going, chill | Evening events |

### Tempo

| Tempo | BPM Range | Best For |
|-------|-----------|----------|
| **Slow** | 60-80 BPM | Calm, reflective events |
| **Medium** | 80-120 BPM | Most events (default) |
| **Fast** | 120-160 BPM | High-energy, sports events |

### Instruments

**Available instruments:**
- Acoustic Guitar
- Electric Guitar
- Piano
- Synth
- Strings (Violin, Cello)
- Drums
- Bass
- Percussion
- Bells
- Flute
- Saxophone

**Combinations:**
- **Outdoor:** Acoustic Guitar, Strings, Percussion
- **Electronic:** Synth, Bass, Drums
- **Classical:** Piano, Strings
- **Rock:** Guitar, Drums, Bass
- **Winter:** Piano, Strings, Bells

---

## Event-Based Matching

Our backend automatically selects appropriate music parameters based on event details:

### Music Festival/Concert
```javascript
{
  genre: 'Electronic',
  mood: 'Energetic',
  tempo: 'Fast',
  instruments: ['Synth', 'Bass', 'Drums']
}
```

### Art Gallery/Museum
```javascript
{
  genre: 'Ambient',
  mood: 'Calm',
  tempo: 'Slow',
  instruments: ['Piano', 'Strings']
}
```

### Sports Event/Race
```javascript
{
  genre: 'Rock',
  mood: 'Motivational',
  tempo: 'Fast',
  instruments: ['Guitar', 'Drums', 'Bass']
}
```

### Food/Wine Event
```javascript
{
  genre: 'Acoustic',
  mood: 'Happy',
  tempo: 'Medium',
  instruments: ['Acoustic Guitar', 'Piano']
}
```

### Outdoor/Nature Event
```javascript
{
  genre: 'Folk',
  mood: 'Inspiring',
  tempo: 'Medium',
  instruments: ['Acoustic Guitar', 'Strings']
}
```

### Family Event
```javascript
{
  genre: 'Pop',
  mood: 'Happy',
  tempo: 'Medium',
  instruments: ['Piano', 'Strings', 'Percussion']
}
```

### Winter/Holiday Event
```javascript
{
  genre: 'Cinematic',
  mood: 'Peaceful',
  tempo: 'Slow',
  instruments: ['Piano', 'Strings', 'Bells']
}
```

---

## Usage in Your Project

### Automatic Mode (Recommended)

When generating a reel, simply check "Add Background Music":

1. System analyzes event title and date
2. Determines appropriate genre, mood, tempo
3. Generates custom music (30-60 seconds)
4. Returns video URL

**Example:**
- Event: "Minocqua Music Festival"
- Auto-selected: Electronic, Energetic, Fast tempo
- Result: Perfect festival music!

### Manual Override

For advanced users, you can modify `/backend-example/api/generate-reel.js`:

```javascript
// Custom parameters
const createResponse = await fetch('https://api.beatoven.ai/api/v1/tracks', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${beatovenApiKey}`,
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    title: event.title,
    duration: 20,
    genre: 'Custom Genre',      // Override
    mood: 'Custom Mood',         // Override
    tempo: 'Custom Tempo',       // Override
    instruments: ['Custom'],     // Override
    format: 'mp3',
  }),
});
```

---

## Best Practices

### 1. Generate Without Music First

**Recommended workflow:**
1. Generate reel without music (faster, cheaper)
2. Preview video
3. If satisfied, regenerate with music
4. Or: Add music in Instagram app (FREE!)

### 2. Match Music to Event Type

Let the system auto-select music parameters based on event:
- ✅ Event title: "Winter Festival" → Auto: Cinematic, Peaceful
- ✅ Event title: "Marathon Race" → Auto: Rock, Motivational
- ✅ Works great for 90% of events!

### 3. Test Different Moods

Same event, different moods:
- "Community Picnic" + Happy mood = Cheerful, family-friendly
- "Community Picnic" + Relaxed mood = Easy-going, casual

### 4. Consider Season

System auto-detects season from event date:
- Summer events: Bright, upbeat music
- Winter events: Cozy, peaceful music
- Fall events: Warm, reflective music
- Spring events: Fresh, inspiring music

### 5. Monitor API Usage

**Free tier:** 15 minutes/month
- ~45 reels (20 seconds each)
- Perfect for testing

**Pro plan:** Unlimited
- Generate as many as needed
- $20/month flat rate

---

## Troubleshooting

### Problem: "Beatoven.ai API error (401)"

**Cause:** Invalid API key

**Solution:**
1. Check API key is correct in web interface
2. Verify key hasn't expired
3. Check account has active subscription
4. Regenerate key if needed

### Problem: "Music generation timeout"

**Cause:** Generation took > 2.5 minutes

**Solution:**
1. Try simpler parameters (default instruments)
2. Check Beatoven.ai status page
3. Increase timeout in backend if needed

### Problem: "Insufficient credits" (Free tier)

**Cause:** Exceeded 15 minutes/month

**Solution:**
1. Upgrade to Pro plan ($20/month unlimited)
2. Wait for next month (resets)
3. Or: Generate videos without music

### Problem: Music doesn't match event

**Cause:** Auto-detection incorrect

**Solution:**
1. Modify event title to be more specific
   - Bad: "Festival"
   - Good: "Music Festival" or "Art Festival"
2. Or: Override parameters in backend code

### Problem: Music quality low

**Cause:** Compressed download or settings

**Solution:**
1. Check `bit_depth: 16` in API call
2. Use `sample_rate: 44100` (CD quality)
3. Download WAV instead of MP3 (Pro plan)

---

## Alternative: Instagram Music (Still Recommended!)

### Why Instagram Music is Better

Even with Beatoven.ai, we still recommend:

1. **Generate reels WITHOUT music**
2. **Add music in Instagram app when posting**

**Reasons:**
- ✅ FREE (no API costs)
- ✅ Huge library (millions of songs)
- ✅ Latest trending music
- ✅ Easier licensing
- ✅ More flexible (change anytime)
- ✅ Instagram handles copyright

**Beatoven.ai is best for:**
- Video content for other platforms (YouTube, Facebook, website)
- Need original music (not stock songs)
- Want AI-matched mood
- Full automation required

---

## Cost Comparison

### Per 50 Reels/Month

| Approach | Setup | Monthly | Total |
|----------|-------|---------|-------|
| **No music + Instagram** | Easy | $0 | $0 |
| **Beatoven.ai Free** | Easy | $0 | $0 (limited) |
| **Beatoven.ai Pro** | Easy | $20 | $20 |
| **Epidemic Sound** | Medium | $15 | $15 |
| **Stock library** | Hard | $10-15 | $10-15 |

**Best value:** Instagram Music (FREE)  
**Best AI option:** Beatoven.ai ($20 for unlimited)

---

## API Rate Limits

### Free Tier
- 15 minutes of music/month
- ~45 tracks (20 seconds each)
- Max 10 requests/minute

### Pro Plan
- Unlimited minutes
- Max 60 requests/minute
- Priority processing

### Tips
- Cache music for repeated events
- Generate in batches
- Monitor usage in dashboard

---

## Examples

### Test API Call

```bash
curl -X POST https://api.beatoven.ai/api/v1/tracks \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Test Track",
    "duration": 20,
    "genre": "Folk",
    "mood": "Uplifting",
    "tempo": "Medium",
    "instruments": ["Acoustic Guitar", "Strings"],
    "format": "mp3"
  }'
```

### Check Track Status

```bash
curl https://api.beatoven.ai/api/v1/tracks/trk_abc123xyz \
  -H "Authorization: Bearer YOUR_API_KEY"
```

---

## Resources

- **Website:** https://www.beatoven.ai/
- **Dashboard:** https://app.beatoven.ai/
- **API Docs:** https://docs.beatoven.ai/
- **Support:** support@beatoven.ai
- **Status Page:** https://status.beatoven.ai/

---

## Summary

✅ **Beatoven.ai provides:**
- High-quality AI-generated music
- Emotion-based composition
- Full API automation
- Event-aware matching
- Commercial licensing
- Free tier for testing

✅ **Best for:**
- Automated video generation
- Original, unique soundtracks
- Multi-platform content
- Professional quality

✅ **Cost:** Free (15 min/mo) or $20/month (unlimited)

✅ **Alternative:** Use Instagram Music (FREE, easier)

---

**Ready to generate amazing music for your reels?** Get your API key at https://www.beatoven.ai/! 🎵
