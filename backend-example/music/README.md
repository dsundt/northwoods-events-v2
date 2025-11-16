# Music Library Directory

## Overview

This directory stores music tracks for Instagram Reels. Use this approach if you have a subscription to a music service or want to use pre-downloaded tracks.

## Supported Services

- **Epidemic Sound** ($15/mo) - Best quality, professional
- **Artlist** ($9.99/mo) - Budget-friendly, high quality
- **YouTube Audio Library** (Free) - Good for testing
- **Free Music Archive** (Free) - Check licenses
- **Incompetech** (Free with attribution) - Basic quality

## Setup Instructions

### Step 1: Choose Music Service

**Recommended:** Epidemic Sound or Artlist for professional quality.

**For testing:** YouTube Audio Library (free).

### Step 2: Download Tracks

Download 10-20 tracks covering these moods:

1. **Upbeat** (3-5 tracks) - Festivals, celebrations, general events
2. **Calm** (2-3 tracks) - Art, galleries, peaceful events
3. **Energetic** (2-3 tracks) - Sports, races, competitions
4. **Acoustic** (2-3 tracks) - Food, wine, dining events
5. **Electronic** (2-3 tracks) - Music festivals, nightlife
6. **Nature** (2-3 tracks) - Outdoor adventures, hiking
7. **Winter** (1-2 tracks) - Winter/holiday events
8. **Family** (1-2 tracks) - Family-friendly events

### Step 3: Name Files Clearly

Use descriptive filenames:

**Good examples:**
- `upbeat-outdoor-adventure.mp3`
- `calm-ambient-peaceful.mp3`
- `energetic-rock-sport.mp3`
- `acoustic-folk-gathering.mp3`

**Bad examples:**
- `track1.mp3` (not descriptive)
- `song.mp3` (not descriptive)

### Step 4: Place in This Directory

```
/backend-example/music/
├── upbeat-outdoor-adventure.mp3
├── upbeat-summer-festival.mp3
├── calm-ambient-peaceful.mp3
├── energetic-rock-sport.mp3
└── ...
```

### Step 5: Update music-selector.js

Edit `/backend-example/music-selector.js` and update the `musicLibrary` object with your actual filenames:

```javascript
const musicLibrary = {
  upbeat: [
    'your-upbeat-track-1.mp3',
    'your-upbeat-track-2.mp3',
  ],
  calm: [
    'your-calm-track-1.mp3',
  ],
  // ... etc
};
```

### Step 6: Enable in generate-reel.js

In `/backend-example/api/generate-reel.js`, uncomment the music selection code (look for comments about music-selector.js).

## File Format Requirements

- **Format:** MP3 or AAC
- **Bitrate:** 128kbps minimum, 320kbps recommended
- **Duration:** 20-30 seconds minimum (backend will trim to match video)
- **Sample Rate:** 44.1 kHz or 48 kHz
- **Channels:** Stereo

## Licensing Notes

### Epidemic Sound
- ✅ Commercial use OK
- ✅ All platforms
- ✅ Keep license even after cancellation

### Artlist
- ✅ Commercial use OK
- ✅ Perpetual license
- ✅ Keep tracks after cancellation

### YouTube Audio Library
- ⚠️ Check each track's license
- ⚠️ Some require attribution
- ⚠️ Some are non-commercial only

### Free Music Archive
- ⚠️ Check Creative Commons license
- ⚠️ Most require attribution
- ⚠️ Some are non-commercial only

### Incompetech
- ⚠️ Attribution required (or pay $30/track)
- ✅ Commercial use OK with attribution

## Testing

Test that your music library is set up correctly:

```bash
# Navigate to backend directory
cd backend-example

# Run validation script
node -e "const {validateMusicLibrary} = require('./music-selector'); console.log(validateMusicLibrary());"
```

**Expected output:** `[]` (empty array = no errors)

**If errors:** Download missing tracks or update music-selector.js

## Example Track List

Here's a suggested starting collection (20 tracks):

### Upbeat (5 tracks)
1. Upbeat outdoor adventure
2. Upbeat summer festival
3. Upbeat celebration party
4. Upbeat indie rock
5. Upbeat pop acoustic

### Calm (3 tracks)
1. Calm ambient peaceful
2. Calm piano reflection
3. Calm acoustic gentle

### Energetic (3 tracks)
1. Energetic rock sport
2. Energetic electronic action
3. Energetic motivational

### Acoustic (3 tracks)
1. Acoustic folk gathering
2. Acoustic guitar pleasant
3. Acoustic indie soft

### Electronic (2 tracks)
1. Electronic dance festival
2. Electronic house party

### Nature (2 tracks)
1. Nature adventure outdoor
2. Nature peaceful forest

### Winter (1 track)
1. Winter acoustic cozy

### Family (1 track)
1. Family happy playful

## Alternative: Use Mubert AI Instead

If managing a music library seems like too much work, consider using **Mubert AI** instead:

- ✅ **Automated** - No manual downloads
- ✅ **API integration** - Already implemented
- ✅ **Unlimited** - $14/mo
- ✅ **AI-matched** - Automatically selects appropriate mood
- ❌ **AI quality** - Not as polished as human-composed

See: `/docs/MUSIC_SOURCES_GUIDE.md` for comparison

## Best Option: No Music + Instagram

The easiest approach is to:
1. Generate reels WITHOUT music
2. Add music in Instagram app when posting
3. **Benefits:** FREE, huge library, latest songs, no licensing issues

---

**Questions?** Check `/docs/MUSIC_SOURCES_GUIDE.md` for detailed comparisons and recommendations.
