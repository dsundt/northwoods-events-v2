# Instagram Image Generation Feature

## Overview

The Instagram Image Generation feature allows you to create beautiful, branded social media images for events using AI-powered image generation. Images are automatically formatted for Instagram (1080x1080), include event details, and feature your Red Canoe Lodging logo.

## Features

✅ **AI Image Generation** - Uses OpenAI's DALL-E 3 for high-quality images  
✅ **Custom Prompts** - Fully customize the image generation prompt  
✅ **Auto-Branding** - Automatic logo overlay at 30% opacity  
✅ **Event Details** - Date and location overlaid on image  
✅ **Instagram Format** - Perfect 1080x1080 square format  
✅ **Auto-Save** - Images saved directly to your repository  
✅ **Regeneration** - Easy to regenerate with different prompts  

---

## Setup Requirements

### 1. OpenAI API Key

You'll need an OpenAI API key to generate images.

**Get Your API Key:**
1. Go to: https://platform.openai.com/api-keys
2. Sign in or create an account
3. Click "Create new secret key"
4. Copy the key (starts with `sk-`)

**Pricing:**
- ~$0.04 per image (DALL-E 3, 1024x1024, standard quality)
- First-time users get $5 in free credits
- Pay-as-you-go after free credits

**Configure in Interface:**
1. Visit: https://dsundt.github.io/northwoods-events-v2/manage.html
2. Click "🤖 OpenAI API Key" button (top right)
3. Paste your API key
4. Click "Save Key"

The key is stored securely in your browser's localStorage.

### 2. Red Canoe Logo

**IMPORTANT**: You need to upload your logo to the repository.

**Location**: `/public/assets/red-canoe-logo.png`

**Requirements:**
- PNG format with transparency
- Square or circular shape recommended
- Minimum 200x200 pixels
- Maximum 1000x1000 pixels

**To Upload:**
1. Go to: https://github.com/YOUR_USERNAME/northwoods-events-v2
2. Navigate to `public/assets/`
3. Click "Add file" → "Upload files"
4. Upload `red-canoe-logo.png`
5. Commit the file

The logo will automatically appear on all generated images at 30% opacity in the bottom-right corner.

---

## How to Use

### Step 1: Preview a Curated Feed

1. Go to "My Curated Feeds"
2. Click "👁️ Preview Events" on any feed
3. Find an event you want to create an image for

### Step 2: Generate Instagram Image

1. Click "🎨 Generate Instagram Image" button on the event
2. Review the auto-generated prompt (you can edit it!)
3. Click "✨ Generate Image ($0.04)"
4. Wait 10-30 seconds for generation

### Step 3: Customize (Optional)

The default prompt includes:
- Event title
- Northwoods theme
- Professional, tourism-focused style
- Nature elements (lakes, forests)

**To customize:**
- Edit the prompt text before generating
- Be specific about style, colors, mood
- Avoid requesting text in the image (added automatically)
- Click "🔄 Regenerate Image" to try again

### Step 4: Save

**Download locally:**
- Click "💾 Download Image"
- Image saves as: `instagram-{event-name}.jpg`

**Save to repository:**
- Click "☁️ Save to Repository"
- Image committed to: `public/instagram/YYYY-MM-DD-{event-name}.jpg`
- Accessible at: `https://github.com/YOUR_USER/northwoods-events-v2/tree/main/public/instagram`

---

## Example Prompts

### Default Prompt
```
Create a beautiful, vibrant Instagram post image for "Winter Festival". 
Style: Professional, eye-catching, suitable for tourism/events in the Northwoods 
region of Wisconsin. Include elements that reflect the event's theme and the 
natural beauty of the area (lakes, forests, outdoor activities).
Do not include any text in the image.
```

### Custom Examples

**For Music Event:**
```
Create a vibrant, energetic image for a live music concert in the Northwoods. 
Show musical instruments or a stage setup with pine forests in the background. 
Warm, inviting colors. Summer evening atmosphere. Professional photography style.
```

**For Family Event:**
```
Create a cheerful, family-friendly image for a kids festival in northern Wisconsin. 
Show activities like canoeing, hiking, or outdoor fun. Bright, happy colors. 
Cartoon or illustrated style acceptable. Include pine trees and lake scenery.
```

**For Winter Event:**
```
Create a cozy winter scene for a holiday event in the Northwoods. Snow-covered 
pine forests, warm cabin lights, festive atmosphere. Cool color palette with 
warm accent lights. Professional, inviting style.
```

---

## Technical Details

### Image Specifications

- **Format**: JPEG
- **Size**: 1080x1080 pixels (Instagram square)
- **Quality**: 95% JPEG quality
- **Model**: DALL-E 3 (OpenAI)
- **Generation Time**: 10-30 seconds

### Text Overlays

**Event Title:**
- Font: Bold Arial, 48px
- Color: White with shadow
- Position: Bottom, left-aligned
- Max: 2 lines (auto-wrapped)

**Event Details:**
- Font: Arial, 32px
- Color: White with shadow
- Position: Below title
- Format: "Dec 15, 2024 • Eagle River, WI"

**Background Gradient:**
- Semi-transparent black gradient at bottom
- Ensures text readability over any background

### Logo Overlay

- Position: Bottom-right corner
- Size: 120x120 pixels
- Opacity: 30%
- Margin: 20px from edges

---

## Troubleshooting

### "Please configure OpenAI API key first"
- Click "🤖 OpenAI API Key" button
- Enter your API key from OpenAI
- Make sure it starts with `sk-`

### "Invalid API key format"
- Verify you copied the entire key
- Check for extra spaces
- Key should start with `sk-`

### "Failed to generate image"
- Check API key is valid
- Verify you have credits remaining
- Try a shorter, simpler prompt
- Check OpenAI status: https://status.openai.com/

### "Logo not found, skipping overlay"
- Upload `red-canoe-logo.png` to `/public/assets/`
- Verify file name is exactly correct (case-sensitive)
- Refresh the page after upload

### "Failed to save image"
- Verify GitHub token is configured
- Check token has `repo` permissions
- Try downloading and manually uploading

---

## Best Practices

### Prompt Writing Tips

1. **Be Geographically Accurate**: 
   - Specify "Northern Wisconsin" or "Northwoods"
   - Mention "NO mountains" - Wisconsin has rolling hills
   - Focus on lakes, forests, and gentle terrain

2. **Include Regional Elements**:
   - Pine and birch trees (not palm trees!)
   - Lakes and rivers (Wisconsin is lake country)
   - Log cabins and rustic lodges
   - Small-town Main Streets
   - Outdoor recreation (canoeing, fishing, hiking)

3. **Seasonal Accuracy**:
   - Winter: Snow, ice fishing, cozy cabins
   - Spring: Budding trees, melting lakes
   - Summer: Lake activities, green forests
   - Fall: Colorful foliage, harvest themes

4. **Avoid Text**: Text is added automatically
5. **Use Descriptive Words**: "vibrant", "cozy", "rustic", "pristine"
6. **Mention Wisconsin**: Regional context helps AI

### Image Usage

1. **Preview Before Saving**: Download and review first
2. **Regenerate If Needed**: Don't settle for first attempt
3. **Save to Repository**: Easier to track and reuse
4. **Consistent Style**: Use similar prompts for brand consistency
5. **Test on Instagram**: Check how it looks in-feed

### Cost Management

- Each generation costs ~$0.04
- Preview before regenerating
- Refine prompts to reduce iterations
- Monitor OpenAI usage dashboard

---

## Security & Privacy

### API Key Storage
- Stored in browser localStorage only
- Never sent to GitHub or other servers
- Not accessible to other websites
- Clear browser data to remove

### Image Content
- AI-generated, not real photos
- No copyrighted material
- Safe for commercial use per OpenAI terms
- Generated images saved to your repository

---

## FAQ

**Q: Can I use different AI models?**  
A: Currently only DALL-E 3 is supported. It provides the best quality for promotional images.

**Q: What if I run out of OpenAI credits?**  
A: Add payment method at https://platform.openai.com/account/billing

**Q: Can I change the image size?**  
A: Currently fixed at 1080x1080 (Instagram square). Could be customized in code.

**Q: Can I remove the logo?**  
A: Yes, but it's auto-added. You'd need to download and edit manually.

**Q: How many images can I store?**  
A: GitHub repos have size limits. Monitor your repo size in Settings.

**Q: Can I batch generate images?**  
A: Not yet. Generate individually to customize each prompt.

---

## Future Enhancements

Potential features for future versions:
- Multiple image size options (story, portrait)
- Batch generation
- Image templates/presets
- Style consistency enforcement
- Alternative AI models
- Image editing tools

---

## Support

For issues or questions:
1. Check this documentation
2. Verify API keys are configured
3. Check OpenAI status page
4. Review browser console for errors
5. Create GitHub issue with details

---

## Cost Calculator

Typical usage costs:

| Usage | Cost |
|-------|------|
| 10 images | $0.40 |
| 50 images | $2.00 |
| 100 images | $4.00 |
| 250 images | $10.00 |

Plus any OpenAI API costs for other services you use.
