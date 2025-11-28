# 🎨 Multi-Model Image Generation - Setup Guide

## ✅ **Feature Implemented!**

You can now choose between **two image generation models**:

1. **🎨 OpenAI DALL-E 3** - Artistic, creative, stylized ($0.04/image)
2. **🤖 Google Gemini 3 Pro Image** - Photorealistic, Vertex AI ($0.02/image)

---

## 🚀 **What's New**

### **Model Selector Dropdown**

When generating an image, you'll see:

```
┌──────────────────────────────────────────┐
│ Image Generation Model:                  │
│ ┌──────────────────────────────────────┐ │
│ │ 🎨 OpenAI DALL-E 3            [▼]   │ │
│ └──────────────────────────────────────┘ │
│                                          │
│ Options:                                 │
│ • DALL-E 3 - Artistic & Creative ($0.04) │
│ • Gemini 3 Pro Image ($0.02)             │
└──────────────────────────────────────────┘
```

**Model info updates dynamically** when you change selection!

---

## 🔧 **Setup Required**

### **Step 1: Deploy Backend** (5 minutes)

The backend now includes the multi-model endpoint.

**From your local machine**:

```bash
cd ~/Documents/northwoods-events-v2

# Pull latest changes
git pull origin main

# Deploy backend
./deploy-backend.sh
```

The script will:
- Deploy new `/api/generate-image` endpoint
- Auto-alias to production
- Test deployment

---

### **Step 2: Configure API Keys** (10 minutes)

You need API keys for the models you want to use:

#### **Option A: Just Use DALL-E 3** (No New Setup)

If you already have OpenAI configured:
- ✅ DALL-E 3 works immediately
- Skip Google Gemini setup
- Can add Google later if desired

#### **Option B: Add Google Gemini 3 Pro Image** (Recommended - Cheaper!)

**For full Gemini 3 Pro Image support, you need:**

1. **Google Cloud Project** with Vertex AI API enabled
2. **API Key** from Google AI Studio or service account

**Setup Steps:**

1. **Enable Vertex AI API**:
   - Go to: https://console.cloud.google.com/apis/library/aiplatform.googleapis.com
   - Select your project
   - Click "Enable"

2. **Get API Key** (from AI Studio):
   - Go to: https://aistudio.google.com/app/apikey
   - Click "Create API Key"
   - Select your Google Cloud project
   - Copy the API key

3. **Get Project ID**:
   - Go to: https://console.cloud.google.com/
   - Your project ID is in the URL or project selector
   - Example: `my-project-12345`

4. **Add Environment Variables to Vercel**:
   ```bash
   cd ~/Documents/northwoods-events-v2/backend-example
   
   # Add API key (required)
   vercel env add GOOGLE_GEMINI_API_KEY production
   # Paste your API key when prompted
   
   # Add Project ID (required for Vertex AI / Gemini 3 Pro)
   vercel env add GOOGLE_CLOUD_PROJECT_ID production
   # Enter your project ID when prompted
   
   # Optional: Set region (defaults to us-central1)
   vercel env add GOOGLE_CLOUD_REGION production
   # Enter: us-central1 (or your preferred region)
   
   # Redeploy to apply
   vercel --prod
   
   # Re-alias
   vercel alias northwoods-reel-api.vercel.app
   ```

5. **Test**:
   ```bash
   curl https://northwoods-reel-api.vercel.app/api/generate-image \
     -X POST \
     -H "Content-Type: application/json" \
     -d '{"prompt":"A beautiful lake in Wisconsin","model":"google-gemini"}'
   ```

---

### **Step 3: Verify Environment Variables** (2 minutes)

Check all keys are set:

```bash
cd ~/Documents/northwoods-events-v2/backend-example
vercel env ls
```

**Should show**:
```
RUNWAY_API_KEY           → Encrypted (Production)
BEATOVEN_API_KEY         → Encrypted (Production)
OPENAI_API_KEY           → Encrypted (Production)      [For DALL-E]
GOOGLE_GEMINI_API_KEY    → Encrypted (Production)      [For Gemini]
GOOGLE_CLOUD_PROJECT_ID  → Encrypted (Production)      [For Vertex AI]
GOOGLE_CLOUD_REGION      → Encrypted (Production)      [Optional]
```

**If missing**:
```bash
# Add OpenAI key (if not already set)
vercel env add OPENAI_API_KEY production

# Add Google credentials
vercel env add GOOGLE_GEMINI_API_KEY production
vercel env add GOOGLE_CLOUD_PROJECT_ID production
```

---

## 🧪 **Testing**

### **Test 1: Model Selector UI**

After GitHub Pages deploys (2-3 minutes):

1. Go to: https://dsundt.github.io/northwoods-events-v2/manage.html
2. Click "📸 Generate Image" on any event
3. **Check dropdown** shows both models
4. **Change model** - info box should update with different description and cost
5. **Button text** should update with cost

---

### **Test 2: DALL-E 3 Generation**

1. Select "🎨 OpenAI DALL-E 3"
2. Click "✨ Generate Image ($0.04)"
3. Should work (existing functionality)
4. Image generates in 10-30 seconds

---

### **Test 3: Google Gemini 3 Pro Image Generation**

1. Select "🤖 Google Gemini 3 Pro Image"
2. Click "✨ Generate Image ($0.02)"
3. **If credentials configured**: Image generates
4. **If not configured**: Shows helpful error with setup instructions

---

## 📊 **Model Comparison**

| Feature | DALL-E 3 | Google Gemini 3 Pro Image |
|---------|----------|--------------------------|
| **Cost** | $0.04/image | $0.02/image (50% cheaper!) |
| **Style** | Artistic, creative | Photorealistic, natural |
| **Speed** | 10-30 seconds | 10-30 seconds |
| **Quality** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **Best For** | Stylized, artistic scenes | Realistic event photos |
| **Prompt Following** | Excellent | Very Good |
| **Setup** | OpenAI account | Google Cloud + Vertex AI |

---

## 🎯 **When to Use Each Model**

### **Use DALL-E 3 for**:
- ✅ Creative, artistic interpretations
- ✅ Stylized event posters
- ✅ Abstract or whimsical images
- ✅ Complex, detailed prompts
- ✅ When you want artistic flair

**Example events**:
- Art festivals
- Music events
- Creative workshops
- Holiday celebrations

---

### **Use Google Gemini 3 Pro Image for**:
- ✅ Photorealistic event photography
- ✅ Natural landscape shots
- ✅ Realistic venue depictions
- ✅ Budget-conscious projects (50% cheaper!)
- ✅ When you want photo-like quality

**Example events**:
- Outdoor recreation
- Nature events
- Sports events
- Community gatherings

---

## 💰 **Cost Savings**

### **Current (All DALL-E 3)**
```
20 images/month × $0.04 = $0.80/month
```

### **Mixed Usage**
```
10 DALL-E 3 × $0.04 = $0.40
10 Gemini × $0.02 = $0.20
──────────────────────────
Total: $0.60/month (25% savings!)
```

### **All Google Gemini**
```
20 images/month × $0.02 = $0.40/month (50% savings!)
```

---

## 🔧 **Backend Endpoints**

### **New Endpoint**: `/api/generate-image`

**Request**:
```json
{
  "prompt": "Beautiful lake scene in Northern Wisconsin",
  "model": "google-gemini",
  "eventData": {
    "title": "Summer Concert",
    "location": "Minocqua",
    "date": "2025-07-15"
  }
}
```

**Response**:
```json
{
  "success": true,
  "imageBase64": "iVBORw0KGgo...",
  "model": "vertex-ai/gemini-3.0-pro-image-generation",
  "cost": 0.02,
  "size": "1024x1024"
}
```

---

## 🎨 **Frontend Changes**

### **1. Model Selector**
- Dropdown with 2 options
- Color-coded info boxes
- Dynamic cost display
- Saved preference (localStorage)

### **2. Backend Integration**
- Uses `/api/generate-image` endpoint
- No API keys in browser (secure!)
- Handles both models
- Better error messages

### **3. Improved UX**
- Shows which model is generating
- Model-specific tips
- Fallback suggestions if model unavailable

---

## 🐛 **Troubleshooting**

### **"Google credentials not configured"**

**Solution**:
1. Get API key from: https://aistudio.google.com/app/apikey
2. Get Project ID from Google Cloud Console
3. Add to Vercel:
   ```bash
   vercel env add GOOGLE_GEMINI_API_KEY production
   vercel env add GOOGLE_CLOUD_PROJECT_ID production
   ```
4. Redeploy:
   ```bash
   cd ~/Documents/northwoods-events-v2
   ./deploy-backend.sh
   ```

---

### **"Google Gemini image generation not available"**

**Possible causes**:
1. **Vertex AI API not enabled**: Enable it in Google Cloud Console
2. **API key not valid**: The API key may be invalid or expired
3. **Model not available**: Gemini 3 Pro Image may not be available in your region
4. **Billing not enabled**: Some features require billing on the Google Cloud project
5. **Wrong Project ID**: Ensure the project ID matches the API key's project

**Solutions**:
1. Enable Vertex AI API: https://console.cloud.google.com/apis/library/aiplatform.googleapis.com
2. Verify your API key at: https://aistudio.google.com/app/apikey
3. Ensure your Google Cloud project has billing enabled
4. Use DALL-E 3 instead (always works)
5. Check backend logs for detailed error messages

**Models attempted by backend** (in order):
1. `gemini-3.0-pro-image-generation` (Vertex AI - primary)
2. `gemini-3-pro-image` (Vertex AI)
3. `gemini-3.0-pro-vision` (Vertex AI)
4. `gemini-2.0-flash-preview-image-generation` (AI Studio fallback)
5. `imagen-3.0-generate-002` (AI Studio fallback)

---

### **DALL-E errors**

If DALL-E fails:
1. Check OpenAI API key is valid
2. Verify you have credits: https://platform.openai.com/usage
3. Check OpenAI status: https://status.openai.com

---

## 📋 **Deployment Checklist**

- [ ] Pull latest code: `git pull origin main`
- [ ] Deploy backend: `./deploy-backend.sh`
- [ ] Enable Vertex AI API in Google Cloud Console
- [ ] Add Google Gemini API key to Vercel
- [ ] Add Google Cloud Project ID to Vercel
- [ ] Test DALL-E 3: Generate an image
- [ ] Test Google Gemini 3 Pro: Generate an image
- [ ] Verify model selector shows both options
- [ ] Check cost display updates correctly

---

## 🎉 **What You Get**

### **Before**
- ❌ Only DALL-E 3
- ❌ Fixed cost ($0.04)
- ❌ One style
- ❌ API key in browser (less secure)

### **After**
- ✅ Two model choices
- ✅ Variable cost ($0.02-0.04)
- ✅ Two distinct styles (artistic vs photorealistic)
- ✅ API keys secure in backend
- ✅ Vertex AI integration for Gemini 3 Pro Image
- ✅ Easy to add more models later
- ✅ Better error handling
- ✅ Model-specific tips

---

## 🚀 **Next Steps**

1. **Deploy backend** with new endpoint
   ```bash
   cd ~/Documents/northwoods-events-v2
   ./deploy-backend.sh
   ```

2. **Enable Vertex AI API**
   - https://console.cloud.google.com/apis/library/aiplatform.googleapis.com

3. **Add Google credentials**
   ```bash
   vercel env add GOOGLE_GEMINI_API_KEY production
   vercel env add GOOGLE_CLOUD_PROJECT_ID production
   vercel --prod
   ```

4. **Test both models** (after GitHub Pages deploys)

5. **Compare results** - see which model you prefer!

6. **Save preference** - system remembers your choice

---

## 💡 **Pro Tips**

### **Model Selection Strategy**

**For events**:
- **Artistic/Creative events** → DALL-E 3
- **Outdoor/Nature events** → Google Gemini 3 Pro Image
- **Budget-conscious** → Google Gemini 3 Pro Image
- **Highest quality** → Try both, pick best!

### **Prompt Optimization**

**DALL-E 3 responds well to**:
- Artistic descriptions ("painterly", "vibrant", "dreamy")
- Style references ("in the style of...")
- Creative interpretations

**Google Gemini 3 Pro responds well to**:
- Realistic descriptions ("photorealistic", "natural lighting")
- Specific details ("golden hour", "wide-angle shot")
- Photography terms

---

## 📚 **Resources**

**OpenAI DALL-E 3**:
- Docs: https://platform.openai.com/docs/guides/images
- Pricing: https://openai.com/pricing
- API Keys: https://platform.openai.com/api-keys

**Google Gemini 3 Pro Image**:
- Vertex AI Docs: https://cloud.google.com/vertex-ai/generative-ai/docs/models/gemini/3-pro-image
- AI Studio: https://aistudio.google.com
- API Keys: https://aistudio.google.com/app/apikey
- Pricing: https://cloud.google.com/vertex-ai/pricing

---

## ✅ **Summary**

**Implemented**:
- ✅ Backend multi-model endpoint (`/api/generate-image`)
- ✅ Frontend model selector UI
- ✅ Support for DALL-E 3
- ✅ Support for Google Gemini 3 Pro Image (Vertex AI)
- ✅ Dynamic cost display
- ✅ Model-specific descriptions
- ✅ Secure API key handling (backend only)
- ✅ Comprehensive error handling
- ✅ Multiple fallback models

**Next**:
- Deploy backend
- Enable Vertex AI API
- Add Google credentials
- Test both models
- Compare results!

**Status**: Ready to deploy and test! 🚀

---

**Last Updated**: 2025-11-28  
**Feature**: Multi-Model Image Generation  
**Primary Model**: Google Gemini 3 Pro Image (Vertex AI)
