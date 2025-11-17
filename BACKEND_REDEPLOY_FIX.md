# CRITICAL: Backend Redeployment Fix

## 🚨 **Problem**

Your backend is returning **404 errors** instead of the API function. This means:
- Function not deployed properly
- Vercel configuration broken
- Old/corrupted deployment

## ✅ **Complete Fix** (10 minutes)

### Step 1: Clean Slate

```bash
cd ~/Documents/northwoods-events-v2/backend-example

# Remove old Vercel configuration
rm -rf .vercel

# Verify vercel.json exists and is correct
cat vercel.json
```

**Should show** CORS headers configuration.

---

### Step 2: Fresh Deployment

```bash
# Deploy as new project
vercel --prod
```

**You'll be asked**:
1. **Set up and deploy?** → `Y` (Yes)
2. **Which scope?** → Select your account
3. **Link to existing project?** → `Y` (Yes)
4. **Project name?** → Type: `northwoods-reel-api` (or select existing)
5. **Overwrite settings?** → `N` (No, unless you want to reconfigure)

**Wait for**:
```
✅ Production: https://northwoods-reel-api.vercel.app
```

---

### Step 3: Verify Deployment

```bash
# Test health check
curl https://northwoods-reel-api.vercel.app/api/generate-reel
```

**Should show JSON** with:
```json
{
  "status": "ok",
  "service": "Instagram Reel Generation API",
  "cors": "enabled",
  ...
}
```

**If you see HTML or 404**: Deployment failed, try again.

---

### Step 4: Test CORS Headers

```bash
curl -I https://northwoods-reel-api.vercel.app/api/generate-reel
```

**Should show**:
```
HTTP/2 200
access-control-allow-origin: *
access-control-allow-methods: GET, POST, OPTIONS
...
```

**If CORS headers missing**: vercel.json not applied, see Step 5.

---

### Step 5: Force Vercel to Use Configuration

If CORS headers still missing:

```bash
cd ~/Documents/northwoods-events-v2/backend-example

# Make a dummy change to force rebuild
echo "// Force rebuild $(date)" >> api/generate-reel.js

# Redeploy
vercel --prod

# Test again
curl -I https://northwoods-reel-api.vercel.app/api/generate-reel | grep access-control
```

---

### Step 6: Alternative - Deploy to New Project Name

If nothing works, deploy as completely new project:

```bash
cd ~/Documents/northwoods-events-v2/backend-example

# Remove linkage
rm -rf .vercel

# Deploy as NEW project with different name
vercel --prod
```

When asked for project name, use: `northwoods-reel-api-v2`

You'll get a new URL like:
```
https://northwoods-reel-api-v2.vercel.app
```

Then update in manage.html:
1. Click "⚙️ Backend URL"
2. Paste new URL: `https://northwoods-reel-api-v2.vercel.app/api/generate-reel`
3. Save

---

## 🐛 **Troubleshooting**

### Error: "No Vercel project found"

```bash
vercel link
```

Follow prompts to link to existing project.

### Error: "Insufficient permissions"

```bash
vercel login
```

Log in again and retry.

### Error: "Function not found"

**Check** that `api/generate-reel.js` exists:
```bash
ls -la api/
```

Should show `generate-reel.js`.

---

## 📊 **Verification Checklist**

After successful deployment:

- [ ] `curl https://your-url/api/generate-reel` returns JSON (not HTML/404)
- [ ] JSON shows `"status": "ok"`
- [ ] JSON shows `"cors": "enabled"`
- [ ] `curl -I` shows `access-control-allow-origin: *`
- [ ] Browser can access URL without CORS errors
- [ ] manage.html can generate reels

---

## ⚡ **Quick Copy-Paste Fix**

Run this complete sequence:

```bash
cd ~/Documents/northwoods-events-v2/backend-example && \
rm -rf .vercel && \
echo "Vercel config removed" && \
cat vercel.json && \
echo "" && \
echo "Deploying to Vercel..." && \
vercel --prod
```

Then test:

```bash
curl https://northwoods-reel-api.vercel.app/api/generate-reel
```

---

## 🎯 **Expected vs Current**

| Test | Expected | Your Current |
|------|----------|--------------|
| Health Check | `{"status":"ok"...}` | **404 "Page not found"** ❌ |
| CORS Headers | `access-control-allow-origin: *` | **Missing** ❌ |
| Function | Deployed and working | **Not deployed** ❌ |

**Your backend is NOT deployed correctly!**

---

**Run the commands above to completely redeploy the backend!** 🚀
