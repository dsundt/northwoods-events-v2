# Runway ML Aspect Ratio - Correct Configuration

## ✅ CORRECT Configuration for Vertical Instagram Reels

### Valid Runway ML Aspect Ratios

According to the Runway ML API error message, these are the **ONLY** valid options:

| Ratio Value | Dimensions | Orientation | Aspect Ratio | Use Case |
|-------------|------------|-------------|--------------|----------|
| `"1280:720"` | 1280w × 720h | Horizontal | 16:9 | YouTube landscape |
| `"720:1280"` | 720w × 1280h | **Vertical** | **9:16** | Instagram Reels (lower quality) |
| **`"1080:1920"`** | **1080w × 1920h** | **Vertical** | **9:16** | **Instagram Reels (HD)** ✅ |
| `"1920:1080"` | 1920w × 1080h | Horizontal | 16:9 | YouTube landscape |

---

## 🎯 Why `"1080:1920"` IS Vertical (9:16)

### Understanding the Format
The ratio format is: `"WIDTH:HEIGHT"`

```
"1080:1920" means:
- Width: 1080 pixels (narrow)
- Height: 1920 pixels (tall)
- Result: VERTICAL (portrait)

┌─────────────┐
│             │  ← 1080px wide
│             │
│   VERTICAL  │  ← 1920px tall
│    9:16     │
│             │
└─────────────┘
```

### Math Verification
```
1080 (width) ÷ 1920 (height) = 0.5625
9 ÷ 16 = 0.5625
✅ Perfect 9:16 aspect ratio!
```

---

## ❌ Common Confusion

### What IS Horizontal (16:9):
```
"1920:1080" means:
- Width: 1920 pixels (WIDE)
- Height: 1080 pixels (short)
- Result: HORIZONTAL (landscape)

┌────────────────────────────────┐
│         HORIZONTAL 16:9        │
└────────────────────────────────┘
```

---

## 🔧 Correct Backend Configuration

### File: `backend-example/api/generate-reel.js`

```javascript
body: JSON.stringify({
  promptText: prompt,
  duration: 8,
  ratio: '1080:1920', // ✅ CORRECT - This IS vertical (9:16)
  model: 'veo3.1_fast',
})
```

### What Happens:
- Runway ML generates video: **1080 pixels wide × 1920 pixels tall**
- Result: **Vertical portrait video**
- Perfect for: **Instagram Reels, TikTok, YouTube Shorts**

---

## 🐛 If Videos Still Appear Horizontal

### Possible Causes:

1. **Looking at old videos** generated before fix
   - Solution: Generate a NEW reel after deploying the fix

2. **Backend not redeployed**
   - Solution: Run `vercel --prod` in `backend-example/` directory

3. **Viewing in wrong orientation**
   - Some video players auto-rotate
   - Test on actual mobile device in Instagram app

4. **Cache issue**
   - Clear browser cache
   - Hard refresh (Ctrl+Shift+R / Cmd+Shift+R)

---

## ✅ Verification Steps

### 1. Check Backend Code
```bash
cd ~/Documents/northwoods-events-v2/backend-example
grep "ratio:" api/generate-reel.js
```

Should show: `ratio: '1080:1920'`

### 2. Check Video File Properties
After downloading a generated video:
- Right-click → Properties → Details
- **Width should be 1080**
- **Height should be 1920**
- If width > height = horizontal ❌
- If height > width = vertical ✅

### 3. Test on Mobile
- Upload to Instagram Reels
- Should fill entire phone screen vertically
- No black bars on sides

---

## 📊 Quick Reference

| Format | Ratio String | Width | Height | Orientation |
|--------|--------------|-------|--------|-------------|
| Instagram Reels | `"1080:1920"` | 1080 | 1920 | Vertical ✅ |
| TikTok | `"1080:1920"` | 1080 | 1920 | Vertical ✅ |
| YouTube Shorts | `"1080:1920"` | 1080 | 1920 | Vertical ✅ |
| YouTube Standard | `"1920:1080"` | 1920 | 1080 | Horizontal |
| Instagram Story | `"1080:1920"` | 1080 | 1920 | Vertical ✅ |

---

## 🎬 What to Do Now

1. **Pull latest changes**: `git pull origin main`
2. **Redeploy backend**: `cd backend-example && vercel --prod`
3. **Generate NEW reel** (old ones might be horizontal)
4. **Check dimensions** of the new video file
5. **Test on mobile** device

---

## ✨ Summary

- ✅ **`"1080:1920"` = VERTICAL (9:16)** - This is CORRECT
- ❌ **`"9:16"` is INVALID** - Runway ML doesn't accept this format
- ✅ **Width before height** - Format is "WIDTH:HEIGHT"
- ✅ **1080 < 1920** - Height > Width = Vertical portrait

**The configuration was correct all along!** If videos appear horizontal, they're likely from before the backend was properly deployed, or there's a viewing/cache issue.
