# 🎨 Instagram Reel Overlay Guide

## ✅ **What's Been Implemented**

### **Updated Runway ML Prompt** ✅
The system now automatically tells Runway ML to **not generate text** in videos.

**Change made**:
```javascript
// Old prompt: Just descriptive text
// New prompt: + "IMPORTANT: No text, no words, no captions, no titles in the video - visual content only."
```

**Benefit**: You get clean, text-free videos ready for your custom overlays!

---

## 🎯 **Recommended Workflow: Instagram Native Overlays**

### **Why Use Instagram's Built-In Tools?**

✅ **Professional Quality**
- Multiple font options
- Animations and effects
- Precise positioning
- Color customization
- Drop shadows, outlines

✅ **Easy to Use**
- Drag and drop text
- Live preview
- Undo/redo
- Templates available

✅ **Zero Technical Complexity**
- No code changes
- No server processing
- No additional costs
- No new failure points

✅ **Fast Workflow**
- 2-3 minutes per reel
- Easier than learning new tools
- What pros use

---

## 📱 **Step-by-Step: Adding Overlays in Instagram**

### **Step 1: Generate Clean Video**

1. Go to: https://dsundt.github.io/northwoods-events-v2/manage.html
2. Select event
3. Click "🎬 Create Instagram Reel"
4. Generate video (with updated prompt - no text from AI!)
5. Download to your device

---

### **Step 2: Add Text Overlay**

**On Mobile (iPhone/Android)**:

1. **Open Instagram app**
2. **Tap** ➕ (Create) → **Reel**
3. **Upload** your video
4. **Tap** Aa (Text tool)
5. **Type event info**:
   ```
   Holiday Felted Garland Workshop
   📅 December 5, 2025
   📍 North Lakeland Discovery Center
   ```
6. **Customize**:
   - Choose font (Classic, Modern, Neon, etc.)
   - Change color (white with black outline works well)
   - Adjust size and position
   - Add animation (typewriter, fade, etc.)

7. **Tap** Done

**Text Positioning Tips**:
- Top third: Event name
- Bottom third: Date and location
- Leave center clear for video content
- Use drop shadows for readability

---

### **Step 3: Add Red Canoe Lodging Logo**

#### **First Time: Upload Logo as Sticker**

1. **In Instagram Reel editor**
2. **Tap** 😊 (Sticker icon)
3. **Tap** "Upload" or "Gallery"
4. **Select** your Red Canoe logo PNG file
5. **Position** in bottom right corner
6. **Resize** to small (about 15-20% of screen width)
7. **Tap and hold** logo → **Opacity slider** → Set to ~30%
8. **Pin** logo to specific position
9. **Save as custom sticker** (if available)

#### **Subsequent Reels: Reuse Logo**

1. **Tap** 😊 (Sticker icon)
2. **Tap** "Your stickers"
3. **Select** Red Canoe logo
4. Already sized and positioned!

---

### **Step 4: Final Touches**

**Optional enhancements**:
- Add music (Instagram library or upload)
- Add transitions
- Adjust timing
- Add effects (vintage, vibrant, etc.)

---

### **Step 5: Save or Post**

1. **Tap** "Next"
2. **Write caption** with event details, website, booking link
3. **Add hashtags**:
   ```
   #NorthwoodsWisconsin #VisitWisconsin #ExploreMi nocqua
   #RedCanoeLodging #WisconsinEvents #NorthernWisconsin
   ```
4. **Share** as Reel or **Save Draft**

---

## 🎨 **Design Templates**

### **Template 1: Minimal**
```
┌─────────────────────────┐
│   Holiday Workshop       │ ← Top: Event name (white, bold)
│                          │
│    [Video Content]       │
│                          │
│   📅 Dec 5, 2025        │ ← Bottom: Date/Location (white)
│   📍 Discovery Center   │
│              [LOGO] 30% │ ← Bottom right: Logo
└─────────────────────────┘
```

### **Template 2: Card Style**
```
┌─────────────────────────┐
│ ╔═════════════════════╗ │ ← Top: Card with event info
│ ║ Holiday Workshop    ║ │
│ ║ Dec 5 • 2PM         ║ │
│ ╚═════════════════════╝ │
│                          │
│    [Video Content]       │
│                          │
│              [LOGO] 30% │ ← Bottom right: Logo
└─────────────────────────┘
```

### **Template 3: Bottom Bar**
```
┌─────────────────────────┐
│                          │
│    [Video Content]       │
│                          │
│ ┌──────────────────────┐│
│ │Holiday Workshop  Dec 5││ ← Bottom bar: All info
│ │Discovery Center [LOGO]││
│ └──────────────────────┘│
└─────────────────────────┘
```

---

## 🖼️ **Logo File Preparation**

### **Create Optimized Logo**

**Requirements**:
- Format: PNG with transparency
- Size: 500×500px to 1000×1000px
- Background: Transparent
- File size: <1MB

**How to create**:

1. **If you have logo**:
   - Open in Photoshop/GIMP/Canva
   - Export as PNG with transparency
   - Resize to 800×800px

2. **If you need logo created**:
   - Use Canva (free): canva.com
   - Create 800×800px design
   - Add "Red Canoe Lodging" text
   - Add canoe graphic
   - Download as PNG

3. **Optimize**:
   - Use tinypng.com to compress
   - Should be <500KB

---

## ⚡ **Alternative Tools** (If Not Using Instagram)

### **CapCut** (Free, Easy)
**Best for**: Batch processing multiple reels

1. Import video
2. Add text layers (drag & drop)
3. Add logo as overlay
4. Export in 9:16 format

**Pros**: Desktop app, powerful, free  
**Cons**: Need to install software

### **Canva** (Free tier available)
**Best for**: Quick edits, templates

1. Upload video
2. Choose Reel template
3. Add text and logo
4. Download

**Pros**: Web-based, easy templates  
**Cons**: Limited free exports

### **DaVinci Resolve** (Free, Professional)
**Best for**: Professional quality

1. Import video
2. Add text layers
3. Add logo overlay with opacity control
4. Export 1080×1920

**Pros**: Professional grade, free  
**Cons**: Learning curve

---

## 🔧 **If You Need Automated Overlays**

### **Option A: Simple Browser Tool** (Medium Complexity)

I can create a **browser-based overlay editor**:

**What it does**:
- Upload video
- Add text (event name, date, location)
- Upload logo
- Position and preview
- Download composite video

**Pros**:
- No server-side processing
- Works in browser
- Preview before download

**Cons**:
- Browser compatibility issues
- Limited to smaller videos
- Quality may vary

**Implementation time**: 4-6 hours  
**Risk**: Medium

---

### **Option B: FFmpeg Server Processing** (High Complexity)

Add video processing to Vercel backend:

**What it does**:
- Automatically overlays text and logo
- Professional quality
- Consistent results

**Cons**:
- ❌ Requires FFmpeg layer (complex setup)
- ❌ Adds 30-60 seconds processing time
- ❌ Multiple failure points
- ❌ 100MB file size limits
- ❌ Debugging complexity
- ❌ Higher costs

**Implementation time**: 1-2 days  
**Risk**: High  
**Recommendation**: ❌ Not worth it for current use case

---

## 🎯 **My Recommendation**

### **For You (Processing <20 reels/month)**

1. ✅ **Use updated prompt** (no text from Runway) - IMPLEMENTED
2. ✅ **Use Instagram native overlays** - Fastest, easiest, best quality
3. ❌ **Skip automated processing** - Not worth the complexity

**Why**: 
- Instagram overlays take 2-3 minutes
- Automated processing takes 1-2 days to implement
- Instagram quality is better
- No technical debt
- No maintenance burden

### **Workflow**:
```
Generate Video (2-5 min)
    ↓
Download to Phone (30 sec)
    ↓
Add Overlays in Instagram (2-3 min)
    ↓
Save Draft or Post
    ↓
Total time: ~5-10 minutes per reel
```

**This is what professional content creators do!**

---

## 📋 **What's Been Changed**

### **File**: `public/manage.js`

**Change**: Added to default prompt:
```
IMPORTANT: No text, no words, no captions, no titles in the video - visual content only.
```

**Result**: Runway ML will generate clean videos without text overlays, perfect for adding your custom text and logo!

---

## 🧪 **Test the Update**

After GitHub Pages deploys (2-3 minutes):

1. **Clear cache**: Cmd+Shift+Delete
2. **Go to**: https://dsundt.github.io/northwoods-events-v2/manage.html
3. **Select event** → Create Reel
4. **Notice** the updated prompt includes "No text, no words..."
5. **Generate video**
6. **Result**: Clean video without AI-generated text!

---

## 📱 **Instagram Overlay Tutorial**

### **Text Overlay**

1. Open Instagram → Create Reel → Upload video
2. Tap **Aa** (Text)
3. Type:
   ```
   Holiday Felted Garland Workshop
   ```
4. Choose font: **Classic** or **Modern**
5. Change color: **White**
6. Add **Drop Shadow** (make text readable over video)
7. Position at **top center**

8. Tap **Aa** again for second text
9. Type:
   ```
   📅 December 5, 2025
   📍 North Lakeland Discovery Center
   ```
10. Same font, smaller size
11. Position at **bottom center**

### **Logo Watermark**

1. Tap **😊** (Stickers)
2. Upload Red Canoe logo (first time only)
3. Position in **bottom right**
4. Resize to **small** (~15% of screen)
5. Tap and hold → Adjust **opacity** to ~30%
6. Done!

**Next reels**: Logo saved as custom sticker, just select and place!

---

## 🔄 **Comparison: Manual vs Automated**

| Aspect | Instagram Overlays | Automated Processing |
|--------|-------------------|---------------------|
| **Time per reel** | 2-3 minutes | 30-60 seconds |
| **Setup time** | 0 minutes | 1-2 days coding |
| **Quality** | ⭐⭐⭐⭐⭐ Professional | ⭐⭐⭐ Good |
| **Customization** | ⭐⭐⭐⭐⭐ Unlimited | ⭐⭐ Limited |
| **Risk** | ✅ Zero | ⚠️ High |
| **Maintenance** | ✅ None | ⚠️ Ongoing |
| **Cost** | $0 | +$10-20/month |
| **Animations** | ✅ Many options | ❌ Static |
| **Preview** | ✅ Live | ⚠️ After processing |

**For 10-20 reels/month**: Instagram overlays are clearly better!

---

## 💡 **When to Consider Automation**

Only if:
- ✅ Processing 100+ reels/month
- ✅ Need identical formatting every time
- ✅ Have technical resources for maintenance
- ✅ Cost of development < cost of manual work

For your current use case: **Manual is better!**

---

## 🎓 **Quick Reference Card**

**Save this for each reel**:

```
┌─────────────────────────────────┐
│   INSTAGRAM OVERLAY CHECKLIST   │
├─────────────────────────────────┤
│ 1. Upload video to Instagram    │
│ 2. Add event title (top)         │
│ 3. Add date & location (bottom)  │
│ 4. Add Red Canoe logo (BR, 30%)  │
│ 5. Add music (optional)          │
│ 6. Preview full screen           │
│ 7. Save draft or post            │
└─────────────────────────────────┘
```

---

## ✅ **Summary**

**Implemented**:
- ✅ Runway prompt updated to request no text
- ✅ Clean videos ready for custom overlays

**Recommended**:
- ✅ Use Instagram native overlay tools (best quality, fastest, easiest)
- ✅ Follow the step-by-step guide above
- ✅ Save logo as custom sticker for reuse

**Not Recommended**:
- ❌ Automated video processing (too complex for current needs)
- ❌ FFmpeg server-side processing (high risk, high maintenance)
- ❌ Browser-based compositing (compatibility issues)

**Result**: Professional-quality reels with event info and branding in 5-10 minutes total!

---

**Last Updated**: 2025-11-17  
**Status**: Production Ready  
**Next**: Test with next reel generation
