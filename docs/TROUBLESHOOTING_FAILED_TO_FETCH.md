# Troubleshooting "Failed to Fetch" Error

## 🔍 Diagnostic Steps

Follow these steps **IN ORDER** to identify the problem:

---

## Step 1: Test Backend Health (CRITICAL)

Open this URL in your browser:
```
https://northwoods-reel-api.vercel.app/api/generate-reel
```

### Expected Result: ✅ Good
```json
{
  "status": "ok",
  "service": "Instagram Reel Generation API",
  "version": "1.0.0",
  "timestamp": "2025-11-16T...",
  "runwayConfigured": true,
  "beatovenConfigured": false
}
```

### If You See This Instead: ❌ Problem

#### Error 1: "Method not allowed"
```json
{"error":"Method not allowed","message":"This endpoint only accepts POST requests"}
```
**Cause**: Backend has old code without health check  
**Fix**: Redeploy backend (see Step 2 below)

#### Error 2: 404 Not Found
**Cause**: Backend not deployed or wrong URL  
**Fix**: Deploy backend (see Step 2 below)

#### Error 3: Page doesn't load at all
**Cause**: Backend URL is wrong or Vercel deployment failed  
**Fix**: Check Vercel deployment status

---

## Step 2: Redeploy Backend with Latest Code

```bash
# Pull latest code
cd ~/Documents/northwoods-events-v2
git pull origin main

# Navigate to backend
cd backend-example

# Deploy to production
vercel --prod
```

**Wait for confirmation**:
```
✅ Production: https://northwoods-reel-api.vercel.app [copied to clipboard]
```

**Then immediately test** the health check URL again (Step 1).

---

## Step 3: Check Frontend Configuration

### A. Open Browser Console
1. Go to: https://dsundt.github.io/northwoods-events-v2/manage.html
2. Press **F12** to open Developer Tools
3. Click **Console** tab

### B. Check Backend URL Setting
In the console, type:
```javascript
localStorage.getItem('reel_backend_url')
```

**Expected Result**:
```
"https://northwoods-reel-api.vercel.app/api/generate-reel"
```

**If null or wrong URL**: Reconfigure it:
1. Click **"⚙️ Backend URL"** button in the web interface
2. Paste: `https://northwoods-reel-api.vercel.app/api/generate-reel`
3. Click **"Save URL"**

### C. Check for Console Errors
Try generating a reel again and watch the console. Look for:
- Red error messages
- "CORS" errors
- "Failed to fetch" with additional details
- Any URLs being called

**Copy all error messages** and share them.

---

## Step 4: Test Backend Connection Manually

### Option A: Browser Test
Open this URL (replace YOUR_URL with your backend):
```
https://northwoods-reel-api.vercel.app/api/generate-reel
```

### Option B: Command Line Test (Mac/Linux)
```bash
curl https://northwoods-reel-api.vercel.app/api/generate-reel
```

**Should return JSON with `"status": "ok"`**

---

## Step 5: Check API Keys

### Verify Runway ML API Key in Vercel

```bash
cd ~/Documents/northwoods-events-v2/backend-example

# List environment variables
vercel env ls

# Should show:
# RUNWAY_API_KEY (Production)
```

**If missing**:
```bash
vercel env add RUNWAY_API_KEY
# Paste your Runway ML API key when prompted
# Select: Production
```

**Then redeploy**:
```bash
vercel --prod
```

---

## Step 6: Clear All Caches

### Browser Cache
1. Press **Ctrl+Shift+Delete** (or **Cmd+Shift+Delete** on Mac)
2. Select **"Cached images and files"**
3. Click **"Clear data"**

### Hard Refresh
1. Go to: https://dsundt.github.io/northwoods-events-v2/manage.html
2. Press **Ctrl+Shift+R** (or **Cmd+Shift+R** on Mac)

---

## 🐛 Common Causes & Solutions

| Problem | Symptom | Solution |
|---------|---------|----------|
| Backend not deployed | Health check fails | Run `vercel --prod` |
| Old backend code | "Method not allowed" | `git pull` + `vercel --prod` |
| Wrong URL configured | Fetch fails immediately | Reconfigure Backend URL in UI |
| Missing API key | Health check shows `runwayConfigured: false` | Add `RUNWAY_API_KEY` to Vercel |
| CORS issue | Console shows "CORS policy" | Backend headers should auto-fix this |
| GitHub Pages not updated | Old UI | Wait 2-3 minutes or clear cache |

---

## 📋 Quick Checklist

Run through this checklist:

- [ ] Health check URL returns JSON with `"status": "ok"`
- [ ] Backend shows `"runwayConfigured": true`
- [ ] Frontend shows backend URL when you click "⚙️ Backend URL"
- [ ] URL is exactly: `https://northwoods-reel-api.vercel.app/api/generate-reel`
- [ ] No extra spaces or characters in URL
- [ ] Runway ML API key is set in Vercel (`vercel env ls` shows it)
- [ ] Backend deployed to production (`vercel --prod`)
- [ ] Browser cache cleared
- [ ] No console errors when loading manage.html

---

## 🆘 If Still Failing

### Collect This Information:

1. **Health check result** (what you see at the health check URL)
2. **Console errors** (F12 → Console tab, copy all red errors)
3. **Backend URL** (from localStorage or UI)
4. **Vercel deployment status** (run `vercel ls` in backend-example/)
5. **Environment variables** (run `vercel env ls`)

### Then Share:
- All error messages
- Screenshots if helpful
- Which step failed

---

## ✅ Expected Working State

When everything is working:

1. **Health Check**: Returns JSON with `status: "ok"`
2. **Frontend**: Shows "Backend connected!" when saving URL
3. **Generation**: Shows progress steps without errors
4. **Result**: Video generates and plays in preview

---

## 🔄 Nuclear Option (Complete Reset)

If nothing else works:

```bash
# Start fresh
cd ~/Documents/northwoods-events-v2
git pull origin main
cd backend-example

# Remove Vercel config
rm -rf .vercel

# Redeploy from scratch
vercel --prod

# Reconfigure all API keys
vercel env add RUNWAY_API_KEY
vercel env add BEATOVEN_API_KEY

# Deploy again
vercel --prod
```

Then reconfigure frontend:
1. Clear browser cache completely
2. Go to manage.html
3. Set backend URL
4. Test health check
5. Try generating reel
