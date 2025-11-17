# Video Dimension Debugging Guide

## 🔍 How to Check Video Dimensions

### Method 1: File Properties (Windows)
1. Download the video
2. Right-click the file
3. Select "Properties"
4. Go to "Details" tab
5. Look for "Frame width" and "Frame height"

### Method 2: File Properties (Mac)
1. Download the video
2. Right-click (or Control+click) the file
3. Select "Get Info"
4. Look at dimensions in the preview or details

### Method 3: VLC Player
1. Open video in VLC
2. Tools → Media Information (or Cmd+I / Ctrl+I)
3. "Codec Details" tab
4. Look for "Resolution" or "Video resolution"

### Method 4: Browser Console
1. Download video
2. Drag into browser
3. Right-click video → "Inspect" (F12)
4. In console, type:
   ```javascript
   document.querySelector('video').videoWidth
   document.querySelector('video').videoHeight
   ```

---

## ✅ **Expected Dimensions**

### Correct (Vertical 9:16):
```
Width: 1080 pixels
Height: 1920 pixels
Orientation: Portrait (vertical)
Aspect Ratio: 9:16 (0.5625)
```

### Incorrect (Horizontal 16:9):
```
Width: 1920 pixels
Height: 1080 pixels
Orientation: Landscape (horizontal)
Aspect Ratio: 16:9 (1.777)
```

---

## 📐 Valid Runway ML Ratios

From API validation errors:

| Ratio String | Width | Height | Orientation | Aspect Ratio |
|--------------|-------|--------|-------------|--------------|
| `"1280:720"` | 1280 | 720 | Horizontal | 16:9 |
| `"720:1280"` | 720 | 1280 | **Vertical** | **9:16** |
| `"1080:1920"` | 1080 | 1920 | **Vertical** | **9:16** (HD) |
| `"1920:1080"` | 1920 | 1080 | Horizontal | 16:9 (HD) |

### Current Setting:
```javascript
ratio: '1080:1920'  // Should produce 1080×1920 vertical video
```

---

## 🐛 Troubleshooting Wrong Dimensions

### If Video is 1920×1080 (Horizontal):

**Possible Causes:**

#### 1. Backend Not Redeployed
**Check**: When was last `vercel --prod` run?
**Fix**: Redeploy backend

#### 2. Old Cached Video
**Check**: Is this a newly generated video?
**Fix**: Generate a brand new video, delete old ones

#### 3. Runway ML Bug
**Check**: Does Runway ML have open issues?
**Fix**: Report to Runway ML support

#### 4. Model-Specific Behavior
**Check**: Does `veo3.1_fast` honor aspect ratio?
**Fix**: Try different model (`veo3.1`, `veo3`)

---

## 🔧 **Potential Fixes**

### Fix 1: Try 720:1280 (Lower Quality Vertical)
```javascript
ratio: '720:1280'  // 720×1280 vertical (lower quality but might be more stable)
```

### Fix 2: Try Different Model
```javascript
model: 'veo3.1'  // Instead of veo3.1_fast
```

### Fix 3: Add Explicit Orientation in Prompt
Update prompt to emphasize:
```
"...vertical portrait orientation, mobile phone format, 9:16 aspect ratio..."
```

---

## 📊 What Dimensions Did You Get?

Please check and report:

**Your Video**:
- Width: _____ pixels
- Height: _____ pixels
- Expected: 1080×1920

**If you got**:
- 1920×1080 → Backend sending wrong ratio
- 1080×1920 → ✅ Correct!
- 720×1280 → Lower quality vertical
- Other → Something else wrong

---

## 🎯 Next Steps

1. **Tell me exact dimensions** (Width × Height)
2. **I'll adjust the fix** based on what you're seeing
3. **Redeploy** with correct settings
4. **Verify** it works

---

**What are the actual dimensions (Width × Height) of the generated video?** 📐
