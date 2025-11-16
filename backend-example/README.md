# Instagram Reel Generation Backend

This directory contains a deployable backend service for AI-powered Instagram Reel generation.

## 🚀 Quick Deploy to Vercel

### Prerequisites

1. **Runway ML Account**: Sign up at [app.runwayml.com](https://app.runwayml.com/)
   - Get API key from Settings → API Keys
   - Purchase credits ($10 minimum)

2. **Vercel Account** (free): Sign up at [vercel.com](https://vercel.com/)

3. **Mubert Account** (optional): For AI music generation
   - Sign up at [mubert.com](https://mubert.com/)
   - Get API key from API section

### Deployment Steps

```bash
# 1. Install Vercel CLI
npm install -g vercel

# 2. Navigate to backend directory
cd backend-example

# 3. Install dependencies
npm install

# 4. Login to Vercel
vercel login

# 5. Deploy
vercel

# 6. Set environment variables
vercel env add RUNWAY_API_KEY
# Paste your Runway ML API key when prompted

# Optional: Add Mubert API key for music
vercel env add MUBERT_API_KEY

# 7. Deploy to production
vercel --prod
```

### Get Your API Endpoint

After deployment, you'll get a URL like:
```
https://your-project.vercel.app
```

Your API endpoint will be:
```
https://your-project.vercel.app/api/generate-reel
```

### Update Frontend

Edit `/workspace/public/manage.js` and update the `BACKEND_URL`:

```javascript
// Around line 1580 in startReelGeneration function
const BACKEND_URL = 'https://your-project.vercel.app/api/generate-reel';
```

## 🧪 Testing

Test your API with cURL:

```bash
curl -X POST https://your-project.vercel.app/api/generate-reel \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Create a 20-second vertical video showcasing a beautiful Northern Wisconsin lake surrounded by pine forests, golden hour lighting, cinematic camera movements.",
    "event": {
      "title": "Test Event",
      "start_utc": "2025-07-15T18:00:00Z",
      "location": "Minocqua, WI"
    },
    "addMusic": false
  }'
```

Expected response (after 2-5 minutes):
```json
{
  "success": true,
  "videoUrl": "https://...",
  "duration": 20,
  "message": "Reel generated successfully!"
}
```

## 🔧 Alternative Platforms

### Netlify Functions

```bash
# Install Netlify CLI
npm install -g netlify-cli

# Deploy
netlify deploy --prod

# Set environment variables
netlify env:set RUNWAY_API_KEY your-key-here
```

### AWS Lambda

Use AWS SAM or Serverless Framework:

```bash
# Install Serverless Framework
npm install -g serverless

# Deploy
serverless deploy

# Set environment variables
serverless deploy --stage production
```

### Railway

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login
railway login

# Deploy
railway up

# Set environment variables
railway variables set RUNWAY_API_KEY=your-key-here
```

## 💰 Cost Estimates

### Runway ML
- **Gen-2**: $0.05/second = $1.00 per 20-second reel
- **Gen-3**: $0.10/second = $2.00 per 20-second reel

### Mubert AI (Optional)
- **Free**: 25 tracks/month
- **Pro**: $14/month unlimited

### Vercel
- **Hobby**: Free (100GB bandwidth, 100 hours compute)
- **Pro**: $20/month (1TB bandwidth, 1000 hours compute)

### Total per Reel
- **Without music**: $1-2
- **With music**: $1-2 (free tier) or +$0.50 (pro tier)

## 🔍 Troubleshooting

### "Runway API error (401)"
- Check that `RUNWAY_API_KEY` environment variable is set correctly
- Verify API key is valid at [app.runwayml.com](https://app.runwayml.com/)

### "Video generation timeout"
- Increase `maxDuration` in `vercel.json` (max: 300s for hobby, 900s for pro)
- Complex prompts take longer - simplify your prompt

### "Insufficient credits"
- Purchase more credits at [app.runwayml.com](https://app.runwayml.com/)
- Each 5-second video costs ~$0.25-0.50

### CORS errors
- Ensure `Access-Control-Allow-Origin: *` is set in response headers
- Check that API endpoint URL is correct in frontend

### "Music generation failed"
- Verify `MUBERT_API_KEY` is set
- Check free tier limits (25 tracks/month)
- Music is optional - try without music first

## 📚 API Documentation

### Request

```typescript
POST /api/generate-reel
Content-Type: application/json

{
  prompt: string;        // AI video generation prompt
  event: {
    title: string;       // Event name
    start_utc: string;   // ISO 8601 date
    location: string;    // Event location
  };
  addMusic: boolean;     // Whether to add background music
}
```

### Response

```typescript
{
  success: boolean;
  videoUrl: string;      // Direct download URL
  duration: number;      // Video duration in seconds
  message: string;       // Success message
  tips?: string[];       // Helpful tips
}
```

### Error Response

```typescript
{
  error: string;         // Error message
  troubleshooting: string[];  // Troubleshooting steps
}
```

## 🎬 Video Specifications

Generated reels meet Instagram's requirements:

- **Aspect Ratio**: 9:16 (vertical)
- **Resolution**: 1080x1920 pixels
- **Duration**: 15-30 seconds
- **Format**: MP4 (H.264)
- **Frame Rate**: 30 fps
- **File Size**: Under 50 MB

## 🔐 Security Notes

- **Never commit API keys** to version control
- Use environment variables for all secrets
- Rotate API keys regularly
- Monitor usage to prevent abuse
- Consider rate limiting in production

## 📖 Additional Resources

- **Runway ML API Docs**: [docs.runwayml.com](https://docs.runwayml.com/)
- **Mubert API Docs**: [mubert.com/api](https://mubert.com/api)
- **Vercel Functions**: [vercel.com/docs/functions](https://vercel.com/docs/functions)
- **Instagram Reels Specs**: [help.instagram.com](https://help.instagram.com/270447560766967)

## ❓ Need Help?

1. Check the [main documentation](/workspace/docs/INSTAGRAM_REEL_GENERATION.md)
2. Review Runway ML status page
3. Test with cURL to isolate frontend/backend issues
4. Check Vercel logs: `vercel logs`

---

**Ready to deploy?** Run `vercel` in this directory! 🚀
