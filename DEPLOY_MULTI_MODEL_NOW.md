# 🚀 Deploy Multi-Model Image Generation - Action Plan

## ✅ **What's Ready**

Multi-model image generation is **coded and committed**! Now you need to deploy it.

---

## 📋 **Deployment Steps** (15 minutes total)

### **Step 1: Deploy Backend** (5 minutes)

**From your local machine**:

```bash
cd ~/Documents/northwoods-events-v2

# Pull latest changes
git pull origin main

# Deploy backend
./deploy-backend.sh
```

**What this does**:
- Deploys new `/api/generate-image` endpoint
- Supports both DALL-E 3 and Google Gemini
- Auto-aliases to production domain
- Tests deployment

**Expected output**:
```
✅ Deployment Complete!
Production URL: https://northwoods-reel-api.vercel.app/api/generate-reel
```

---

### **Step 2: Add Google Gemini API Key** (10 minutes)

#### **2A: Get Gemini API Key**

1. **Go to**: https://aistudio.google.com/app/apikey

2. **Sign in** with Google account

3. **Click**: "Get API key" or "Create API key"

4. **Select project** or create new one

5. **Copy the API key** (starts with `AIza...`)

#### **2B: Add to Vercel**

```bash
cd ~/Documents/northwoods-events-v2/backend-example

# Add Gemini API key
vercel env add GOOGLE_GEMINI_API_KEY production

# When prompted, paste your API key
# Then press Enter

# Verify it's added
vercel env ls
```

**Should show**:
```
GOOGLE_GEMINI_API_KEY → Encrypted (Production) ✅
```

#### **2C: Redeploy**

```bash
# Redeploy to apply new environment variable
cd ~/Documents/northwoods-events-v2
./deploy-backend.sh
```

---

### **Step 3: Test Multi-Model** (5 minutes)

**After backend deploys** (should be done now):

#### **3A: Test Backend Directly**

```bash
# Test with DALL-E 3
curl https://northwoods-reel-api.vercel.app/api/generate-image \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"prompt":"Beautiful Wisconsin lake","model":"dall-e-3"}'

# Test with Google Gemini
curl https://northwoods-reel-api.vercel.app/api/generate-image \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"prompt":"Beautiful Wisconsin lake","model":"google-gemini"}'
```

**Expected**:
- DALL-E: Returns image base64 (should work if OpenAI key configured)
- Gemini: Returns image or helpful error with setup instructions

---

#### **3B: Test in Browser**

**Wait 2-3 minutes for GitHub Pages**, then:

1. **Clear cache**: Cmd+Shift+Delete
2. **Go to**: https://dsundt.github.io/northwoods-events-v2/manage.html
3. **Click**: "📸 Generate Image" on any event
4. **Check**: Dropdown shows both models ✅
5. **Select**: Google Gemini
6. **Click**: Generate Image ($0.02)
7. **Wait**: 10-30 seconds
8. **Result**: Image should generate!

---

## 🎯 **Quick Start (If You Just Want DALL-E)**

If you only want to use DALL-E 3 (and skip Google setup):

1. **Deploy backend**:
   ```bash
   cd ~/Documents/northwoods-events-v2
   ./deploy-backend.sh
   ```

2. **That's it!**
   - DALL-E 3 option will work immediately
   - Google Gemini will show "not configured" (gracefully)
   - Can add Google later anytime

---

## 📊 **What's Been Added**

### **Backend**
- ✅ New `/api/generate-image` endpoint
- ✅ Supports DALL-E 3
- ✅ Supports Google Gemini 3 Pro Image (Vertex AI)
- ✅ Secure API key handling
- ✅ Model routing logic
- ✅ Error handling with helpful messages
- ✅ Fallback mechanisms

### **Frontend**
- ✅ Model selector dropdown
- ✅ Dynamic model info display
- ✅ Cost display per model
- ✅ Color-coded info boxes
- ✅ Backend API integration
- ✅ Model-specific error messages
- ✅ Removed API key from browser (more secure!)

### **Configuration**
- ✅ Updated `vercel.json` with new endpoint
- ✅ CORS headers for `/api/generate-image`
- ✅ Proper routing and rewrites
- ✅ Environment variable support

---

## 🔍 **Verification**

### **Check Backend Deployed**

```bash
# Should return JSON (not 404)
curl https://northwoods-reel-api.vercel.app/api/generate-image
```

**Expected**: Method not allowed (it's POST only) - but not 404!

### **Check Frontend Deployed**

**After 2-3 minutes**:
1. Open: https://dsundt.github.io/northwoods-events-v2/manage.html
2. Generate Image dialog should show model dropdown
3. Dropdown should have 2 options

---

## 🎨 **Model Selector Preview**

### **What You'll See**

```
┌────────────────────────────────────────────────┐
│ Image Generation Model:                        │
│ ┌────────────────────────────────────────────┐ │
│ │ 🎨 OpenAI DALL-E 3            [▼]         │ │
│ └────────────────────────────────────────────┘ │
│                                                │
│ ┌────────────────────────────────────────────┐ │
│ │ DALL-E 3: Best for creative, artistic,    │ │
│ │ and stylized images. Excellent at         │ │
│ │ following complex prompts. Higher cost    │ │
│ │ but consistently high quality.            │ │
│ └────────────────────────────────────────────┘ │
│                                                │
│ AI Image Prompt:                               │
│ ┌────────────────────────────────────────────┐ │
│ │ Create a beautiful, vibrant Instagram...  │ │
│ │                                            │ │
│ └────────────────────────────────────────────┘ │
│                                                │
│ [Close] [⚙️ Backend] [✨ Generate Image ($0.04)]│
└────────────────────────────────────────────────┘
```

**When you select Google Gemini**:
- Info box turns **green**
- Text updates to Gemini description
- Button shows **($0.02)** instead of ($0.04)

---

## ⚡ **DO THIS NOW**

### **Immediate Deployment**:

```bash
cd ~/Documents/northwoods-events-v2
git pull origin main
./deploy-backend.sh
```

**That's it!** DALL-E 3 will work immediately.

### **Add Google Gemini** (Optional):

```bash
# Get API key from: https://aistudio.google.com/app/apikey

# Add to Vercel
vercel env add GOOGLE_GEMINI_API_KEY production
# Paste key when prompted

# Redeploy
./deploy-backend.sh
```

---

## 🎉 **What You'll Get**

**Immediate**:
- ✅ Model selector in image generation dialog
- ✅ DALL-E 3 works as before
- ✅ Google Gemini option available (shows setup if not configured)

**After adding Gemini key**:
- ✅ Both models fully functional
- ✅ Choose best model per event
- ✅ Save 50% on costs with Gemini
- ✅ Compare artistic vs photorealistic styles

---

**Run `./deploy-backend.sh` now and the feature will be live in ~5 minutes!** 🚀

---

**Last Updated**: 2025-11-17  
**Status**: Ready to Deploy  
**Action**: Run deployment script
