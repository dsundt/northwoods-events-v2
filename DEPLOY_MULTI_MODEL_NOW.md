# 🚀 Deploy Image Generation - Quick Start

## ⚡ **5-Minute Setup**

### **Step 1: Deploy Backend** (2 minutes)

```bash
cd backend-example

# Deploy to Vercel
vercel --prod

# Set alias (optional)
vercel alias your-deployment-url.vercel.app northwoods-reel-api.vercel.app
```

### **Step 2: Add OpenAI API Key** (2 minutes)

```bash
# Add OpenAI key for DALL-E 3
vercel env add OPENAI_API_KEY production
# Paste your key when prompted

# Redeploy to apply
vercel --prod
```

### **Step 3: Verify** (1 minute)

```bash
# Check environment variables
vercel env ls
```

Should show:
```
OPENAI_API_KEY → Encrypted (Production) ✅
```

---

## 🧪 **Test It**

### **Quick API Test**

```bash
curl https://your-backend.vercel.app/api/generate-image \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"prompt":"Beautiful Wisconsin lake at sunset"}'
```

**Expected response**:
```json
{
  "success": true,
  "imageBase64": "iVBORw0KGgo...",
  "model": "dall-e-3",
  "cost": 0.04,
  "size": "1024x1024"
}
```

### **UI Test**

1. Open manage.html
2. Click "📸 Generate Image" on any event
3. Click "✨ Generate Image ($0.04)"
4. Wait 10-30 seconds
5. Image appears!

---

## 📊 **What's Included**

### **Backend**
- ✅ `/api/generate-image` endpoint
- ✅ OpenAI DALL-E 3 integration
- ✅ Secure API key handling
- ✅ Error handling with helpful messages

### **Frontend**
- ✅ Generate Image button on events
- ✅ AI prompt editor
- ✅ Image preview
- ✅ Download functionality

---

## 🐛 **Troubleshooting**

### **"OpenAI API key not configured"**

```bash
vercel env add OPENAI_API_KEY production
vercel --prod
```

### **"DALL-E API error"**

1. Check API key: https://platform.openai.com/api-keys
2. Check credits: https://platform.openai.com/usage
3. Check status: https://status.openai.com

---

## 💰 **Costs**

| Action | Cost |
|--------|------|
| Generate 1 image | $0.04 |
| Generate 10 images | $0.40 |
| Generate 25 images | $1.00 |

---

## ✅ **Checklist**

- [ ] Deploy backend: `vercel --prod`
- [ ] Add OPENAI_API_KEY
- [ ] Test API with curl
- [ ] Test UI with manage.html

---

**Done!** Your image generation is ready to use. 🎨
