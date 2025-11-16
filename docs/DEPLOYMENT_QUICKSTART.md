# 🚀 Instagram Reel Generation - Deployment Quickstart

## ✅ What You Have

A complete Instagram Reel generation system with:
- AI video generation (Runway ML)
- Optional AI music (Mubert or manual library)
- Web interface on GitHub Pages
- Gallery for viewing all reels
- Comprehensive documentation

## 📚 Documentation Overview

### 1. **VERCEL_DEPLOYMENT_GUIDE.md** (Complete Setup)
**Read this first!** Step-by-step Vercel deployment:
- 10 detailed sections
- Every command explained
- Screenshots descriptions
- Troubleshooting for every error
- **Time required:** 15 minutes

### 2. **MUSIC_SOURCES_GUIDE.md** (Choose Music)
Compare 9 music services:
- Mubert AI (recommended for automation)
- Epidemic Sound (best quality, no API)
- Instagram Music (recommended - add after upload!)
- And 6 more options
- **Recommendation:** No music + Instagram app

### 3. **INTEGRATION_EXAMPLES.md** (Code Examples)
Implementation examples:
- Mubert AI integration (done!)
- Pre-downloaded library setup
- FFmpeg video merging
- Testing procedures

### 4. **INSTAGRAM_REEL_GENERATION.md** (User Guide)
Complete user documentation:
- Features overview
- Backend setup guide
- Prompt writing tips
- Cost breakdown
- FAQ

### 5. **REEL_IMPLEMENTATION_SUMMARY.md** (Technical)
Technical overview for developers

### 6. **REEL_QUICKSTART.txt** (Visual Guide)
ASCII art quick reference guide

---

## ⚡ Super Quick Start (15 Minutes)

### Prerequisites
- Node.js 14+ installed
- Runway ML account with credits ($10 min)
- 15 minutes of your time

### Step 1: Get Runway ML API Key (3 minutes)
1. Go to: https://app.runwayml.com/
2. Sign up and verify email
3. Go to: Settings → API Keys
4. Click: "Create New Key"
5. Copy key (starts with `sk_`)
6. Purchase credits: $10 minimum

### Step 2: Deploy to Vercel (5 minutes)
```bash
# Install Vercel CLI
npm install -g vercel

# Navigate to backend
cd backend-example

# Install dependencies
npm install

# Login to Vercel (opens browser)
vercel login

# Deploy to preview
vercel

# Add API key
vercel env add RUNWAY_API_KEY
# Paste your Runway ML API key when prompted

# Deploy to production
vercel --prod
```

**Save your production URL!** Example: `https://your-project.vercel.app`

### Step 3: Configure Web Interface (2 minutes)
1. Go to: https://dsundt.github.io/northwoods-events-v2/manage.html
2. Click: "🎥 Runway ML Key"
   - Paste your Runway ML API key
3. Click: "⚙️ Backend URL"
   - Paste: `https://your-project.vercel.app/api/generate-reel`

### Step 4: Generate First Reel (5 minutes)
1. Click: "My Feeds" → Preview any feed
2. Find an event
3. Click: "🎥 Generate Reel"
4. Click: "✨ Generate Reel" (use default prompt)
5. Wait: 2-5 minutes ⏰
6. Preview and download!

✅ **Done!** You just generated your first AI reel!

---

## 💰 Cost Breakdown

### Required Costs
| Service | Cost | Purpose |
|---------|------|---------|
| **Runway ML** | $10 min purchase | AI video generation |
| | ~$1-2 per reel | 20-second reels |

### Optional Costs
| Service | Cost | Purpose |
|---------|------|---------|
| **Vercel Hosting** | FREE | Hobby plan (100 GB, 100 hrs) |
| **Mubert AI Music** | FREE | 25 tracks/month |
| | $14/mo | Unlimited tracks |
| **Epidemic Sound** | $15/mo | Professional music library |

### Monthly Estimates

**Light usage (5 reels/month):**
- Runway ML: $5-10
- Vercel: FREE
- Music: FREE (use Instagram)
- **Total: $5-10/month**

**Medium usage (20 reels/month):**
- Runway ML: $20-40
- Vercel: FREE
- Music: $0-14
- **Total: $20-54/month**

**Heavy usage (50 reels/month):**
- Runway ML: $50-100
- Vercel: FREE or $20 (Pro)
- Music: $0-15
- **Total: $50-135/month**

---

## 🎵 Music Recommendations

### Option 1: No Music (Recommended ⭐)

**Generate reels WITHOUT music, add in Instagram app:**

**Pros:**
- ✅ **FREE** - No additional cost
- ✅ **Easy** - 30 seconds to add music
- ✅ **Huge library** - Millions of licensed songs
- ✅ **Latest tracks** - Trending music
- ✅ **Zero licensing issues**

**How:**
1. Generate reel without music
2. Download video
3. Upload to Instagram app
4. Tap "Add Music"
5. Search and select
6. Post!

**This is THE BEST option for most users!**

### Option 2: Mubert AI (For Automation)

**Fully automated AI-generated music:**

**Pros:**
- ✅ Already implemented
- ✅ Fully automated
- ✅ API-based (reliable)
- ✅ Good quality

**Cons:**
- ❌ $14/month after 25 free tracks
- ❌ AI-generated (less polished)

**Setup:**
```bash
vercel env add MUBERT_API_KEY
# Paste: amb_xxxxxxxxxxxxxxxx
vercel --prod
```

### Option 3: Epidemic Sound (Professional)

**Highest quality, no API:**

**Pros:**
- ✅ Best quality
- ✅ 40,000+ tracks
- ✅ Commercial license

**Cons:**
- ❌ $15/month
- ❌ No API (manual process)
- ❌ Complex setup (FFmpeg)

**Only use if:** You need professional music for non-Instagram platforms

---

## 📐 Video Specifications

Generated reels meet Instagram requirements:

| Specification | Value |
|---------------|-------|
| Format | MP4 (H.264) |
| Resolution | 1080x1920 (9:16 vertical) |
| Duration | 15-30 seconds |
| Frame Rate | 30 fps |
| File Size | < 50 MB |
| Audio | AAC, 44.1 kHz, stereo |

---

## 🎨 Prompt Tips

### Good Prompt Structure

```
Create a [duration]-second vertical video (9:16) for [event].

SETTING: Northern Wisconsin / Northwoods
- Dense pine forests and pristine lakes
- Rolling hills (NO mountains)
- Rustic cabins and charming towns

VIDEO STYLE:
- Camera movements: [pans, zooms, tracking]
- Lighting: [golden hour, bright daylight]
- Mood: [energetic, peaceful, exciting]

SCENES:
- Opening: [description] (X seconds)
- Middle: [description] (Y seconds)
- Closing: [description] (Z seconds)

Duration: 20 seconds, vertical (9:16)
NO text, NO mountains - Wisconsin only!
```

### Example: Summer Festival

```
Create a 22-second vertical video (9:16) for Minocqua Music Festival.

SETTING: Outdoor concert venue, late afternoon summer,
surrounded by tall pine trees, lakeside atmosphere

VIDEO STYLE:
- Smooth cinematic camera movements
- Golden hour lighting (warm, glowing)
- Energetic and festive mood

SCENES:
- Opening: Aerial view of venue with forest (5s)
- Middle: Stage with crowd, festival energy (8s)
- Transition: Slow pan across blue lake (5s)
- Closing: Wide sunset shot with attendees (4s)

Duration: 22 seconds, 9:16 vertical
NO text, NO mountains - Wisconsin Northwoods only!
```

---

## 🐛 Common Issues & Solutions

### "Command not found: vercel"
```bash
# Reinstall CLI
npm install -g vercel

# Or use without installing
npx vercel
```

### "Error: No existing credentials"
```bash
vercel login
```

### "Missing RUNWAY_API_KEY"
```bash
vercel env add RUNWAY_API_KEY
vercel --prod
```

### "Backend URL not configured" (in web interface)
1. Click "⚙️ Backend URL"
2. Paste: `https://your-project.vercel.app/api/generate-reel`
3. Save

### "Runway API error (401)"
- Check API key is correct
- Verify you have credits: https://app.runwayml.com/
- Check key has proper permissions

### "Video generation timeout"
- Wait longer (can take up to 5 minutes)
- Simplify prompt
- Check Runway ML status page

### CORS errors
- Verify backend URL is correct
- Check backend deployed successfully
- Try redeploying: `vercel --prod`

---

## 📊 File Structure

```
northwoods-events-v2/
├── docs/
│   ├── VERCEL_DEPLOYMENT_GUIDE.md     ⭐ Start here!
│   ├── MUSIC_SOURCES_GUIDE.md         🎵 Music options
│   ├── INTEGRATION_EXAMPLES.md        💻 Code examples
│   ├── INSTAGRAM_REEL_GENERATION.md   📖 User guide
│   ├── REEL_IMPLEMENTATION_SUMMARY.md 📝 Tech overview
│   └── DEPLOYMENT_QUICKSTART.md       ⚡ This file
│
├── backend-example/
│   ├── api/
│   │   └── generate-reel.js           Main API handler
│   ├── music/
│   │   └── README.md                  Music library setup
│   ├── music-selector.js              Smart music selection
│   ├── INTEGRATION_EXAMPLES.md        Integration guides
│   ├── package.json                   Dependencies
│   ├── vercel.json                    Deployment config
│   └── README.md                      Deployment guide
│
├── public/
│   ├── manage.html                    Main interface
│   ├── manage.js                      Reel generation logic
│   ├── reel-gallery.html              Gallery page
│   └── instagram-reels/               Generated videos
│
└── REEL_QUICKSTART.txt                Visual ASCII guide
```

---

## 🎯 Recommended Workflow

### For Maximum Efficiency

1. **Generate videos WITHOUT music**
   - Saves: $14/month
   - Simpler: No music processing
   - Faster: No video merging

2. **Add music in Instagram app**
   - FREE: Instagram's huge library
   - Easy: 30 seconds
   - Better: Latest trending songs
   - Flexible: Change anytime

3. **Generate in batches**
   - Create 5-10 reels at once
   - Less switching between tools
   - More efficient workflow

4. **Test prompts first**
   - Use Runway ML web interface
   - Test 1-2 prompts before automating
   - Refine for best results

5. **Monitor costs**
   - Check Runway ML dashboard weekly
   - Set budget alerts
   - Track API usage

---

## ✨ What You Can Do Now

1. ✅ Generate professional Instagram Reels (9:16, 1080x1920)
2. ✅ AI video generation with Runway ML
3. ✅ Optional AI music or manual selection
4. ✅ Northern Wisconsin-themed prompts
5. ✅ Web interface for easy generation
6. ✅ Gallery to view all reels
7. ✅ Save to GitHub repository
8. ✅ Download for local use
9. ✅ Customize every prompt
10. ✅ Professional quality results

---

## 📞 Need Help?

### Documentation
- **Setup:** Read `VERCEL_DEPLOYMENT_GUIDE.md`
- **Music:** Read `MUSIC_SOURCES_GUIDE.md`
- **Code:** Read `INTEGRATION_EXAMPLES.md`
- **Usage:** Read `INSTAGRAM_REEL_GENERATION.md`

### Troubleshooting
- Check Vercel logs: `vercel logs --prod`
- Test API: `curl -X POST https://your-url/api/generate-reel ...`
- Validate setup: Review error messages
- Check status: https://status.runwayml.com/

### Community
- GitHub Issues: https://github.com/dsundt/northwoods-events-v2
- Runway ML Docs: https://docs.runwayml.com/
- Vercel Docs: https://vercel.com/docs

---

## 🚀 Ready to Deploy?

### Checklist

- [ ] Node.js 14+ installed
- [ ] Runway ML account created
- [ ] Runway ML API key obtained
- [ ] $10+ credits purchased
- [ ] 15 minutes available

### Commands

```bash
# Install CLI
npm install -g vercel

# Deploy
cd backend-example
npm install
vercel login
vercel
vercel env add RUNWAY_API_KEY
vercel --prod

# Copy your URL
echo "https://your-project.vercel.app/api/generate-reel"
```

### Configure

1. Go to: https://dsundt.github.io/northwoods-events-v2/manage.html
2. Add: Runway ML API Key
3. Add: Backend URL
4. Test: Generate a reel!

---

**That's it!** You're ready to create stunning Instagram Reels! 🎥✨

**Recommended:** Start with NO music, add in Instagram app. It's free, easy, and gives you access to millions of licensed songs! 🎵
