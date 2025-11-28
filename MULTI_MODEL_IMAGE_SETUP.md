# 🎨 Image Generation - Setup Guide

## ✅ **Using OpenAI DALL-E 3**

Image generation uses **OpenAI DALL-E 3** for high-quality, artistic images.

- **Cost**: $0.04 per image
- **Quality**: Excellent at following complex prompts
- **Style**: Creative, artistic, stylized images

---

## 🔧 **Setup Required**

### **Step 1: Get OpenAI API Key**

1. Go to: https://platform.openai.com/api-keys
2. Click "Create new secret key"
3. Copy the API key (starts with `sk-...`)

### **Step 2: Add to Vercel**

```bash
cd backend-example

# Add OpenAI API key
vercel env add OPENAI_API_KEY production
# Paste your key when prompted

# Deploy
vercel --prod
```

### **Step 3: Test**

```bash
curl https://your-backend.vercel.app/api/generate-image \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"prompt":"A beautiful sunset over a Wisconsin lake"}'
```

---

## 📋 **Environment Variables**

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | ✅ Yes | Your OpenAI API key |

---

## 🧪 **Testing**

1. Open manage.html in your browser
2. Click "📸 Generate Image" on any event
3. Edit the prompt if desired
4. Click "✨ Generate Image ($0.04)"
5. Wait 10-30 seconds for generation

---

## 🐛 **Troubleshooting**

### "OpenAI API key not configured"

**Solution**:
```bash
vercel env add OPENAI_API_KEY production
vercel --prod
```

### "DALL-E API error"

1. Check your API key is valid: https://platform.openai.com/api-keys
2. Verify you have credits: https://platform.openai.com/usage
3. Check OpenAI status: https://status.openai.com

---

## 📚 **Resources**

- OpenAI DALL-E Docs: https://platform.openai.com/docs/guides/images
- OpenAI Pricing: https://openai.com/pricing
- API Keys: https://platform.openai.com/api-keys

---

**Last Updated**: 2025-11-28  
**Model**: OpenAI DALL-E 3
