# Instagram Reel Generation (AI Video)

## 🎥 Overview

Generate stunning Instagram Reels (15-30 second vertical videos) for events using AI video generation. The reels are automatically optimized for Instagram's format (9:16 aspect ratio, 1080x1920px) and can include AI-selected background music.

## ⚠️ Important: Backend Service Required

Unlike image generation (which runs entirely in the browser), **video generation requires a backend service** because:

1. **Long processing time**: Video generation takes 2-5 minutes
2. **Large file sizes**: Videos are 10-50 MB
3. **Complex workflows**: Generation → Polling → Music → Delivery
4. **API limitations**: Runway ML API doesn't support browser CORS

## 🛠️ Implementation Options

### Option 1: Serverless Function (Recommended)

Deploy a serverless function to handle video generation:

**Platforms:**
- Vercel Functions (recommended - free tier available)
- Netlify Functions
- AWS Lambda
- Google Cloud Functions

**Implementation Steps:**

1. Create a serverless function endpoint
2. Accept event data from frontend
3. Call Runway ML API
4. Poll for completion
5. Optionally add music with FFmpeg
6. Return video URL

See [Backend Implementation Guide](#backend-implementation-guide) below.

### Option 2: GitHub Actions Workflow

Use GitHub Actions to generate videos on schedule:

**Pros:**
- No separate backend needed
- Automatic scheduling
- Free for public repos

**Cons:**
- Can't generate on-demand from UI
- Slower (GitHub Actions startup time)

### Option 3: Use Runway ML Directly

**Simplest option for testing:**

1. Go to [app.runwayml.com](https://app.runwayml.com/)
2. Use Gen-2 or Gen-3 video generation
3. Input your prompt
4. Download the video
5. Manually upload to `/public/instagram-reels/`

## 🎬 AI Video Generation Services

### Runway ML (Recommended)

**Why Runway ML:**
- Industry-leading quality (used in Hollywood productions)
- Reliable API with good documentation
- Gen-2 (stable) and Gen-3 (newest) models
- Reasonable pricing

**Pricing:**
- **Gen-2**: ~$0.05 per second (~$0.75-1.50 per reel)
- **Gen-3**: ~$0.10 per second (~$1.50-3.00 per reel)
- **Credits**: Buy in packs or subscribe

**API Endpoint:**
```
POST https://api.runwayml.com/v1/gen2/generate
```

**Get API Key:**
1. Sign up at [app.runwayml.com](https://app.runwayml.com/)
2. Go to Settings → API Keys
3. Create new API key
4. Save securely

### Alternative: Luma AI Dream Machine

**If Runway is unavailable:**
- High quality, cinematic results
- Good for landscapes and nature scenes
- Limited API access (waitlist)
- Similar pricing

**API:** Contact Luma AI for access

### Not Recommended

- **OpenAI Sora**: Not publicly available (no API yet)
- **Stability AI Video**: Lower quality, inconsistent results
- **Pika Labs**: Limited API access

## 🎵 Background Music Options

### Option 1: Mubert AI (Recommended)

**AI-generated royalty-free music:**
- Generated on-demand
- Match mood and duration
- Fully licensed for commercial use

**Pricing:**
- Free tier: 25 tracks/month
- Pro: $14/month unlimited

**Get API Key:**
1. Sign up at [mubert.com](https://mubert.com/)
2. Go to API section
3. Generate API key

**API Usage:**
```javascript
POST https://api.mubert.com/v2/RecordTrack
{
  "duration": 20, // seconds
  "tags": "upbeat,energetic,outdoor",
  "mode": "track"
}
```

### Option 2: Stock Music Libraries

**Free options:**
- **YouTube Audio Library**: Free, attribution required
- **Free Music Archive**: Royalty-free
- **Incompetech**: Free with attribution

**Premium options:**
- **Epidemic Sound**: $15/month
- **Artlist**: $9.99/month
- **AudioJungle**: Pay per track

### Option 3: No Music

Generate video without music (user can add in Instagram app).

## 📐 Reel Specifications

### Video Format

```
Aspect Ratio: 9:16 (vertical)
Resolution: 1080x1920 pixels
Duration: 15-30 seconds (optimal: 20-25 seconds)
Frame Rate: 30 fps (24 fps acceptable)
Format: MP4 (H.264 codec)
File Size: Under 50 MB
Audio: AAC codec, 44.1 kHz, stereo
```

### Text Overlay (Added on Video)

Unlike images where text is composited in the browser, video text overlay requires:

1. **Server-side processing** (FFmpeg)
2. **Or**: Skip text, let Instagram add it
3. **Or**: Burn text into video during generation (via prompt)

**Recommended:** Add text in Instagram app (more flexible).

## 🎨 Prompt Writing for Reels

### Structure

```
Create a [duration]-second vertical video (9:16) for [event].

SETTING: Northern Wisconsin / Northwoods
[Describe location, landscape, season]

VIDEO STYLE:
- Camera movements (pans, zooms, tracking shots)
- Lighting (golden hour, bright daylight, etc.)
- Mood (energetic, peaceful, exciting)

SCENES:
- Scene 1: [opening shot description]
- Scene 2: [mid shot description]
- Scene 3: [closing shot description]

Duration: [15-30] seconds
NO text, NO mountains, Wisconsin landscapes only
```

### Example Prompts

**Music Festival:**
```
Create a 22-second vertical video (9:16) for Minocqua Music Festival in Northern Wisconsin.

SETTING: Outdoor concert venue surrounded by tall pine trees, late afternoon summer setting, lakeside atmosphere

VIDEO STYLE:
- Smooth cinematic camera movements
- Golden hour lighting (warm, glowing)
- Energetic and festive mood
- Professional tourism videography

SCENES:
- Opening: Sweeping aerial view of venue with pine forest backdrop (5 seconds)
- Middle: Close-up of instruments/stage with crowd energy, festival banners (8 seconds)
- Transition: Slow pan across pristine blue lake adjacent to venue (5 seconds)
- Closing: Wide shot of venue at sunset with attendees enjoying music (4 seconds)

CAMERA MOVEMENTS: Slow zoom out, smooth pans, gentle tracking shots
Duration: 22 seconds, vertical format (9:16)
NO text, NO mountains - Wisconsin Northwoods only
```

**Winter Sports Event:**
```
Create a 20-second vertical video (9:16) for Snowshoe Adventure Race in Northern Wisconsin.

SETTING: Snowy winter forest, frozen lake, bright winter day

VIDEO STYLE:
- Dynamic, energetic camera work
- Bright winter lighting, blue skies
- Adventurous, exhilarating mood
- Action-focused cinematography

SCENES:
- Opening: Tracking shot through snow-covered pine forest (6 seconds)
- Middle: Snowshoers on frozen lake with forest background (8 seconds)
- Closing: Wide shot of winter landscape, participants in distance (6 seconds)

CAMERA: Drone-style aerials, tracking shots, smooth movements
Duration: 20 seconds, 9:16 vertical
NO mountains, focus on flat frozen lakes and forest
```

### Tips

1. **Be specific about camera movements**: "slow pan left", "zoom out", "tracking shot"
2. **Describe transitions**: How scenes flow together
3. **Specify duration per scene**: Helps AI pace the video
4. **Mention lighting**: Golden hour, bright daylight, overcast
5. **Include mood keywords**: Energetic, peaceful, exciting, inviting
6. **Wisconsin-specific**: Pine forests, lakes, cabins, no mountains

## 🔧 Backend Implementation Guide

### Serverless Function (Vercel Example)

**File: `/api/generate-reel.js`**

```javascript
// Vercel Serverless Function
import fetch from 'node-fetch';
import { exec } from 'child_process';
import { promisify } from 'util';
import fs from 'fs/promises';
import path from 'path';

const execAsync = promisify(exec);

export default async function handler(req, res) {
  // Enable CORS
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
  
  if (req.method === 'OPTIONS') {
    return res.status(200).end();
  }
  
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }
  
  const { prompt, event, addMusic } = req.body;
  const RUNWAY_API_KEY = process.env.RUNWAY_API_KEY;
  
  if (!RUNWAY_API_KEY) {
    return res.status(500).json({ error: 'Runway API key not configured' });
  }
  
  try {
    // Step 1: Generate video with Runway ML
    console.log('Starting video generation...');
    
    const genResponse = await fetch('https://api.runwayml.com/v1/gen2/generate', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${RUNWAY_API_KEY}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        prompt: prompt,
        duration: 20, // seconds
        aspect_ratio: '9:16',
        model: 'gen2', // or 'gen3' for higher quality
      }),
    });
    
    if (!genResponse.ok) {
      throw new Error(`Runway API error: ${await genResponse.text()}`);
    }
    
    const genData = await genResponse.json();
    const taskId = genData.id;
    
    // Step 2: Poll for completion
    console.log(`Video generation started: ${taskId}`);
    let videoUrl = null;
    let attempts = 0;
    const maxAttempts = 60; // 5 minutes max
    
    while (!videoUrl && attempts < maxAttempts) {
      await new Promise(resolve => setTimeout(resolve, 5000)); // Wait 5 seconds
      
      const statusResponse = await fetch(
        `https://api.runwayml.com/v1/tasks/${taskId}`,
        {
          headers: {
            'Authorization': `Bearer ${RUNWAY_API_KEY}`,
          },
        }
      );
      
      const statusData = await statusResponse.json();
      
      if (statusData.status === 'SUCCEEDED') {
        videoUrl = statusData.output;
        break;
      } else if (statusData.status === 'FAILED') {
        throw new Error('Video generation failed');
      }
      
      attempts++;
      console.log(`Polling attempt ${attempts}/${maxAttempts}...`);
    }
    
    if (!videoUrl) {
      throw new Error('Video generation timeout');
    }
    
    console.log('Video generated successfully');
    
    // Step 3: Add music (optional)
    if (addMusic) {
      console.log('Generating background music...');
      
      const musicResponse = await fetch('https://api.mubert.com/v2/RecordTrack', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          license: process.env.MUBERT_API_KEY,
          duration: 20,
          tags: determineMusicTags(event.title),
          mode: 'track',
        }),
      });
      
      const musicData = await musicResponse.json();
      const musicUrl = musicData.data.track_url;
      
      // Download video and music
      const videoPath = `/tmp/video.mp4`;
      const musicPath = `/tmp/music.mp3`;
      const outputPath = `/tmp/output.mp4`;
      
      await downloadFile(videoUrl, videoPath);
      await downloadFile(musicUrl, musicPath);
      
      // Merge with FFmpeg
      console.log('Merging video and music...');
      await execAsync(
        `ffmpeg -i ${videoPath} -i ${musicPath} -c:v copy -c:a aac -map 0:v:0 -map 1:a:0 -shortest ${outputPath}`
      );
      
      // Read and return as base64
      const videoBuffer = await fs.readFile(outputPath);
      const videoBase64 = videoBuffer.toString('base64');
      
      return res.status(200).json({
        success: true,
        video: `data:video/mp4;base64,${videoBase64}`,
        taskId: taskId,
      });
    }
    
    // Return video URL (no music)
    return res.status(200).json({
      success: true,
      videoUrl: videoUrl,
      taskId: taskId,
    });
    
  } catch (error) {
    console.error('Error generating reel:', error);
    return res.status(500).json({
      error: error.message,
      stack: error.stack,
    });
  }
}

function determineMusicTags(eventTitle) {
  const title = eventTitle.toLowerCase();
  
  if (title.includes('music') || title.includes('concert') || title.includes('festival')) {
    return 'upbeat,energetic,festival,party';
  } else if (title.includes('art') || title.includes('gallery')) {
    return 'calm,ambient,sophisticated,artful';
  } else if (title.includes('sport') || title.includes('race') || title.includes('adventure')) {
    return 'energetic,dynamic,motivational,action';
  } else if (title.includes('food') || title.includes('wine') || title.includes('dining')) {
    return 'upbeat,cheerful,casual,pleasant';
  } else {
    return 'upbeat,outdoor,nature,adventure';
  }
}

async function downloadFile(url, dest) {
  const response = await fetch(url);
  const buffer = await response.buffer();
  await fs.writeFile(dest, buffer);
}
```

**File: `vercel.json`**

```json
{
  "functions": {
    "api/generate-reel.js": {
      "maxDuration": 300,
      "memory": 3008
    }
  },
  "env": {
    "RUNWAY_API_KEY": "@runway-api-key",
    "MUBERT_API_KEY": "@mubert-api-key"
  }
}
```

**Deployment:**

```bash
# Install Vercel CLI
npm install -g vercel

# Deploy
vercel

# Set environment variables
vercel env add RUNWAY_API_KEY
vercel env add MUBERT_API_KEY

# Deploy to production
vercel --prod
```

### Update Frontend to Use Backend

**File: `/workspace/public/manage.js`**

Replace the placeholder `startReelGeneration` function with:

```javascript
async function startReelGeneration(event) {
    const promptInput = document.getElementById('reel-prompt');
    const statusDiv = document.getElementById('reel-generation-status');
    const generateBtn = document.getElementById('generate-reel-btn');
    const addMusic = document.getElementById('add-music').checked;
    const prompt = promptInput.value.trim();
    
    if (!prompt) {
        showToast('Please enter a prompt', 'warning');
        return;
    }
    
    generateBtn.disabled = true;
    generateBtn.textContent = '⏳ Generating...';
    
    // Update to your deployed backend URL
    const BACKEND_URL = 'https://your-vercel-app.vercel.app/api/generate-reel';
    
    statusDiv.innerHTML = `
        <div style="background: #e7f3ff; border: 1px solid #b3d9ff; padding: 1rem; border-radius: 4px;">
            <div style="display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.5rem;">
                <div style="width: 20px; height: 20px; border: 3px solid #0066cc; border-top-color: transparent; border-radius: 50%; animation: spin 1s linear infinite;"></div>
                <span><strong>Generating Video...</strong> This takes 2-5 minutes</span>
            </div>
            <div style="font-size: 0.85rem; color: var(--text-muted);">
                Step 1/3: Submitting to Runway ML...<br>
                Please keep this window open.
            </div>
        </div>
    `;
    
    try {
        const response = await fetch(BACKEND_URL, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                prompt: prompt,
                event: {
                    title: event.title,
                    start_utc: event.start_utc,
                    location: event.location,
                },
                addMusic: addMusic,
            }),
        });
        
        if (!response.ok) {
            throw new Error(`Backend error: ${response.status}`);
        }
        
        const data = await response.json();
        
        if (!data.success) {
            throw new Error(data.error || 'Unknown error');
        }
        
        // Show preview and save options
        const previewDiv = document.getElementById('reel-preview');
        previewDiv.innerHTML = `
            <div style="background: #d4edda; border: 1px solid #c3e6cb; padding: 1rem; border-radius: 4px; margin-bottom: 1rem;">
                ✅ Video generated successfully!
            </div>
            <video controls style="width: 100%; max-width: 400px; border-radius: 8px; margin-bottom: 1rem;">
                <source src="${data.videoUrl || data.video}" type="video/mp4">
                Your browser does not support video playback.
            </video>
            <div style="display: flex; gap: 0.5rem; flex-wrap: wrap;">
                <button onclick="downloadReel('${data.videoUrl || data.video}')" class="btn btn-success">
                    💾 Download Reel
                </button>
                <button onclick="saveReelToGitHub('${data.videoUrl || data.video}', ${JSON.stringify(event).replace(/"/g, '&quot;')})" class="btn btn-primary">
                    ☁️ Save to Repository
                </button>
            </div>
        `;
        
        statusDiv.innerHTML = '';
        
    } catch (error) {
        console.error('Reel generation error:', error);
        statusDiv.innerHTML = `
            <div style="background: #ffe7e7; border: 1px solid #ffb3b3; padding: 1rem; border-radius: 4px; color: #cc0000;">
                <strong>Error:</strong> ${escapeHtml(error.message)}<br>
                <small>Check console for details</small>
            </div>
        `;
    } finally {
        generateBtn.disabled = false;
        generateBtn.textContent = '✨ Generate Reel ($2-4, 2-5 min)';
    }
}

function downloadReel(videoUrl) {
    const a = document.createElement('a');
    a.href = videoUrl;
    a.download = `reel-${Date.now()}.mp4`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
}

async function saveReelToGitHub(videoUrl, event) {
    // Implementation similar to saveImageToGitHub
    // Convert video to base64 and commit to repo
}
```

## 📊 Cost Breakdown

### Runway ML
- **Gen-2**: $0.05/second = $0.75-1.50 per reel (15-30 sec)
- **Gen-3**: $0.10/second = $1.50-3.00 per reel
- **Minimum**: $10 credit purchase

### Mubert AI Music
- **Free**: 25 tracks/month (sufficient for testing)
- **Pro**: $14/month unlimited

### Total Cost Per Reel
- **Without music**: $0.75-3.00
- **With music**: $0.75-3.00 (free tier) or +$0.50 (pro tier)
- **Estimated**: $2-4 per reel (average)

### Monthly Estimates
- **5 reels/month**: $10-20
- **20 reels/month**: $40-80
- **50 reels/month**: $100-200

## 🎯 Best Practices

1. **Test prompts first**: Use Runway ML web interface to test prompts before automating
2. **Keep prompts specific**: Detailed prompts = better results
3. **Generate in batches**: Save costs by generating multiple reels at once
4. **Preview before posting**: Always review generated videos
5. **Wisconsin-specific**: Emphasize local landscapes, no mountains
6. **Music licensing**: Ensure commercial rights if using stock music
7. **Monitor costs**: Track API usage, set up alerts
8. **Cache results**: Don't regenerate the same video multiple times

## 🐛 Troubleshooting

### "Backend service required"
- You're seeing the placeholder implementation
- Deploy a serverless function (see Backend Implementation Guide)
- Or use Runway ML web interface directly

### "Video generation timeout"
- Runway ML can take 2-5 minutes
- Increase timeout in your backend function
- Check Runway ML status page

### "Invalid API key"
- Verify Runway ML API key in backend environment variables
- Regenerate key if necessary
- Check account has sufficient credits

### Music not working
- Verify Mubert API key
- Check free tier limits (25/month)
- Try without music first

### Large file sizes
- Videos are 10-50 MB (normal)
- GitHub has 100 MB file limit
- Consider external storage (S3, Cloudinary) for videos

## 📚 Additional Resources

- **Runway ML Docs**: [docs.runwayml.com](https://docs.runwayml.com/)
- **Mubert API Docs**: [mubert.com/api](https://mubert.com/api)
- **Instagram Reel Specs**: [help.instagram.com](https://help.instagram.com/270447560766967)
- **FFmpeg Documentation**: [ffmpeg.org/documentation.html](https://ffmpeg.org/documentation.html)
- **Vercel Functions**: [vercel.com/docs/functions](https://vercel.com/docs/functions)

## ❓ FAQ

**Q: Why doesn't this work in the browser like images?**  
A: Video generation takes 2-5 minutes and requires polling APIs, which browsers can't handle reliably. A backend service is needed.

**Q: Can I use OpenAI for video?**  
A: Sora (OpenAI's video model) is not publicly available yet. Use Runway ML instead.

**Q: How long does generation take?**  
A: 2-5 minutes typically, sometimes up to 10 minutes for complex prompts.

**Q: What if I don't want to set up a backend?**  
A: Use Runway ML's web interface directly and manually upload videos.

**Q: Can I generate without music?**  
A: Yes, uncheck "Add Background Music" option. Add music in Instagram app later.

**Q: Is there a free option?**  
A: No free AI video generation services exist with sufficient quality. Minimum cost is ~$0.75 per reel.

**Q: Can I edit the video after generation?**  
A: Yes, download and edit in video editing software, or add text/effects in Instagram app.

---

**Ready to generate reels?** Deploy the backend service and start creating stunning Instagram videos! 🎥✨
