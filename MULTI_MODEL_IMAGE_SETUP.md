# 🎨 Multi-Model Image Generation - Setup Guide

## ✅ **Feature Implemented!**

You can now choose between **two image generation models**:

1. **🎨 OpenAI DALL-E 3** - Artistic, creative, stylized ($0.04/image)
2. **🤖 Google Gemini 2.5 Flash + Imagen 3** - Photorealistic, natural ($0.02/image)

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
│ • Google Gemini 2.5 Flash ($0.02)        │
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

#### **Option B: Add Google Gemini** (Recommended - Cheaper!)

**Get Gemini API Key**:

1. **Go to**: https://aistudio.google.com/app/apikey

2. **Click**: "Get API Key" or "Create API Key"

3. **Select/Create Project**: Choose a Google Cloud project or create new

4. **Copy the key**: Starts with something like `AIza...`

5. **Add to Vercel**:
   ```bash
   cd ~/Documents/northwoods-events-v2/backend-example
   
   # Add Gemini API key
   vercel env add GOOGLE_GEMINI_API_KEY production
   # Paste your key when prompted
   
   # Redeploy to apply
   vercel --prod
   
   # Re-alias
   vercel alias northwoods-reel-api.vercel.app
   ```

6. **Test**:
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
RUNWAY_API_KEY       → Encrypted (Production)
BEATOVEN_API_KEY     → Encrypted (Production)
OPENAI_API_KEY       → Encrypted (Production)      [For DALL-E]
GOOGLE_GEMINI_API_KEY → Encrypted (Production)     [NEW!]
```

**If missing**:
```bash
# Add OpenAI key (if not already set)
vercel env add OPENAI_API_KEY production

# Add Google Gemini key
vercel env add GOOGLE_GEMINI_API_KEY production
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

### **Test 3: Google Gemini Generation**

1. Select "🤖 Google Gemini 2.5 Flash"
2. Click "✨ Generate Image ($0.02)"
3. **If API key configured**: Image generates
4. **If not configured**: Shows helpful error with setup instructions

---

## 📊 **Model Comparison**

| Feature | DALL-E 3 | Google Gemini 2.5 Flash |
|---------|----------|------------------------|
| **Cost** | $0.04/image | $0.02/image (50% cheaper!) |
| **Style** | Artistic, creative | Photorealistic, natural |
| **Speed** | 10-30 seconds | 10-30 seconds |
| **Quality** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **Best For** | Stylized, artistic scenes | Realistic event photos |
| **Prompt Following** | Excellent | Very Good |
| **Setup** | OpenAI account | Google AI Studio |

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

### **Use Google Gemini for**:
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
  "model": "google-gemini",  // or "dall-e-3"
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
  "model": "google-gemini-2.5-flash-imagen",
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

### **"Google Gemini API key not configured"**

**Solution**:
1. Get key from: https://aistudio.google.com/app/apikey
2. Add to Vercel:
   ```bash
   vercel env add GOOGLE_GEMINI_API_KEY production
   ```
3. Redeploy:
   ```bash
   cd ~/Documents/northwoods-events-v2
   ./deploy-backend.sh
   ```

---

### **"Google Gemini image generation not available"**

**Possible causes**:
1. **Region restriction**: Gemini image gen may not be available in your region yet
2. **API not enabled**: Need to enable Imagen API in Google Cloud
3. **Wrong endpoint**: Google's API structure may have changed

**Solutions**:
- Use DALL-E 3 instead (always works)
- Check Google AI Studio for image generation availability
- Wait for Gemini image generation to launch in your region

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
- [ ] Add Google Gemini API key to Vercel (if using)
- [ ] Test DALL-E 3: Generate an image
- [ ] Test Google Gemini: Generate an image
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

2. **Add Google Gemini API key** (optional)
   ```bash
   vercel env add GOOGLE_GEMINI_API_KEY production
   vercel --prod
   ```

3. **Test both models** (after GitHub Pages deploys)

4. **Compare results** - see which model you prefer!

5. **Save preference** - system remembers your choice

---

## 💡 **Pro Tips**

### **Model Selection Strategy**

**For events**:
- **Artistic/Creative events** → DALL-E 3
- **Outdoor/Nature events** → Google Gemini
- **Budget-conscious** → Google Gemini
- **Highest quality** → Try both, pick best!

### **Prompt Optimization**

**DALL-E 3 responds well to**:
- Artistic descriptions ("painterly", "vibrant", "dreamy")
- Style references ("in the style of...")
- Creative interpretations

**Google Gemini responds well to**:
- Realistic descriptions ("photorealistic", "natural lighting")
- Specific details ("golden hour", "wide-angle shot")
- Photography terms

---

## 📚 **Resources**

**OpenAI DALL-E 3**:
- Docs: https://platform.openai.com/docs/guides/images
- Pricing: https://openai.com/pricing
- API Keys: https://platform.openai.com/api-keys

**Google Gemini**:
- AI Studio: https://aistudio.google.com
- Docs: https://ai.google.dev/gemini-api/docs
- Image Generation: https://ai.google.dev/gemini-api/docs/imagen
- Pricing: https://ai.google.dev/pricing

---

## ✅ **Summary**

**Implemented**:
- ✅ Backend multi-model endpoint (`/api/generate-image`)
- ✅ Frontend model selector UI
- ✅ Support for DALL-E 3
- ✅ Support for Google Gemini 2.5 Flash + Imagen 3
- ✅ Dynamic cost display
- ✅ Model-specific descriptions
- ✅ Secure API key handling (backend only)
- ✅ Comprehensive error handling

**Next**:
- Deploy backend
- Add Google Gemini API key (optional)
- Test both models
- Compare results!

**Status**: Ready to deploy and test! 🚀

---

**Last Updated**: 2025-11-17  
**Feature**: Multi-Model Image Generation  
**Models**: DALL-E 3 + Google Gemini 2.5 Flash
