# 🚀 Complete Vercel Deployment Guide - Step by Step

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Create Vercel Account](#create-vercel-account)
3. [Install Vercel CLI](#install-vercel-cli)
4. [Prepare Your Project](#prepare-your-project)
5. [Deploy to Vercel](#deploy-to-vercel)
6. [Configure Environment Variables](#configure-environment-variables)
7. [Test Your Deployment](#test-your-deployment)
8. [Connect to GitHub (Optional)](#connect-to-github-optional)
9. [Monitor and Debug](#monitor-and-debug)
10. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### What You'll Need

✅ **Computer Requirements:**
- macOS, Windows, or Linux
- Internet connection
- Terminal/Command Prompt access

✅ **Software Requirements:**
- Node.js 14 or higher
- npm (comes with Node.js)
- Git (optional, for GitHub integration)

✅ **Accounts Required:**
- Vercel account (free)
- Runway ML account (paid - minimum $10)
- Email address for verification

### Check Node.js Installation

Open Terminal (Mac/Linux) or Command Prompt (Windows) and run:

```bash
node --version
```

**Expected output:** `v14.0.0` or higher

If not installed, download from: https://nodejs.org/ (choose LTS version)

---

## Create Vercel Account

### Step 1: Sign Up

1. **Go to Vercel website:**
   - URL: https://vercel.com/signup
   
2. **Choose sign-up method:**
   - **Option A: GitHub** (Recommended - enables auto-deployment)
     - Click "Continue with GitHub"
     - Click "Authorize Vercel"
     - Grant permissions
   
   - **Option B: GitLab**
     - Click "Continue with GitLab"
     - Follow authorization prompts
   
   - **Option C: Bitbucket**
     - Click "Continue with Bitbucket"
     - Follow authorization prompts
   
   - **Option D: Email**
     - Enter your email address
     - Check inbox for verification email
     - Click verification link
     - Set password

3. **Complete profile:**
   - Enter your name
   - Choose username (this will be in your URLs)
   - Select account type: "Hobby" (free)
   - Click "Continue"

4. **Skip tutorial** (or complete if you want)
   - Click "Skip" or follow the quick tour

✅ **You now have a Vercel account!**

---

## Install Vercel CLI

The Vercel Command Line Interface (CLI) lets you deploy from your computer.

### Step 1: Install CLI Globally

Open Terminal/Command Prompt and run:

```bash
npm install -g vercel
```

**What this does:**
- Downloads the Vercel CLI
- Installs it globally on your system
- Makes the `vercel` command available

**Expected output:**
```
+ vercel@32.0.0
added 123 packages in 45s
```

**Time required:** 1-2 minutes

### Step 2: Verify Installation

```bash
vercel --version
```

**Expected output:** `Vercel CLI 32.0.0` (or similar)

### Step 3: Login to Vercel CLI

```bash
vercel login
```

**What happens:**
1. Opens your web browser automatically
2. Shows "Confirm Login" page
3. Click "Confirm" button
4. Browser shows "Logged in successfully"
5. Terminal shows: `> Success! Email confirmed`

**If browser doesn't open:**
- Copy the URL shown in terminal
- Paste into your browser
- Click "Confirm"

✅ **You're now logged into Vercel CLI!**

---

## Prepare Your Project

### Step 1: Navigate to Backend Directory

```bash
cd /path/to/northwoods-events-v2/backend-example
```

**Replace** `/path/to/` with your actual path. Examples:

**macOS/Linux:**
```bash
cd ~/Documents/northwoods-events-v2/backend-example
```

**Windows:**
```bash
cd C:\Users\YourName\Documents\northwoods-events-v2\backend-example
```

### Step 2: Install Dependencies

```bash
npm install
```

**What this does:**
- Reads `package.json`
- Downloads required packages (`node-fetch`, `form-data`)
- Creates `node_modules` folder

**Expected output:**
```
added 15 packages in 5s
```

**Time required:** 30 seconds - 1 minute

### Step 3: Verify File Structure

```bash
ls -la
```

**You should see:**
```
api/
  generate-reel.js
node_modules/
package.json
vercel.json
README.md
```

✅ **Project is ready to deploy!**

---

## Deploy to Vercel

### Step 1: Initial Deployment

In the `backend-example` directory, run:

```bash
vercel
```

**Interactive prompts will appear:**

#### Prompt 1: Set up and deploy
```
? Set up and deploy "~/path/backend-example"? [Y/n]
```
**Answer:** Press `Enter` (Yes)

#### Prompt 2: Which scope?
```
? Which scope do you want to deploy to?
  Your Name (your-username)
```
**Answer:** Press `Enter` (select your account)

#### Prompt 3: Link to existing project?
```
? Link to existing project? [y/N]
```
**Answer:** Press `n` then `Enter` (No - this is a new project)

#### Prompt 4: Project name
```
? What's your project's name? (backend-example)
```
**Options:**
- Press `Enter` to use default name
- Or type a custom name like: `northwoods-reel-api`

**Tip:** Use lowercase, no spaces, hyphens ok

#### Prompt 5: Project location
```
? In which directory is your code located? ./
```
**Answer:** Press `Enter` (current directory)

#### Prompt 6: Deployment settings
```
Auto-detected Project Settings (Node.js):
- Build Command: `npm run build`
- Output Directory: `public`
- Development Command: None

? Want to modify these settings? [y/N]
```
**Answer:** Press `n` then `Enter` (No - use auto-detected settings)

### Step 2: Deployment Progress

You'll see:

```
🔗  Inspecting code and uploading...
✅  Preview: https://backend-example-abc123.vercel.app [copied]
📝  Deployed to preview in 15s
```

**What this means:**
- ✅ Code uploaded successfully
- ✅ Preview deployment created
- ✅ URL copied to clipboard

### Step 3: Save Your URLs

**Preview URL:** `https://backend-example-abc123.vercel.app`

**Your API endpoint:** `https://backend-example-abc123.vercel.app/api/generate-reel`

📋 **Copy this URL!** You'll need it later.

---

## Configure Environment Variables

Environment variables store your API keys securely.

### Step 1: Add Runway ML API Key

```bash
vercel env add RUNWAY_API_KEY
```

**Prompts:**

#### 1. Choose environment
```
? What's the value of RUNWAY_API_KEY?
```
**Answer:** Paste your Runway ML API key (from https://app.runwayml.com/)

**Example:** `sk_runway_abc123xyz789...`

#### 2. Select environments
```
? Add RUNWAY_API_KEY to which Environments?
  ◉ Production
  ◉ Preview
  ◯ Development
```
**Answer:** 
- Use arrow keys to select
- Press `Space` to toggle
- Select: **Production** and **Preview**
- Press `Enter`

**Expected output:**
```
✅ Added Environment Variable RUNWAY_API_KEY to Project backend-example
```

### Step 2: Add Mubert API Key (Optional)

```bash
vercel env add MUBERT_API_KEY
```

Follow same process as Step 1.

**To skip music:** Just don't add this variable. Videos will generate without music.

### Step 3: Verify Environment Variables

```bash
vercel env ls
```

**Expected output:**
```
Environment Variables
┌──────────────────┬──────────────┬───────────┬─────────┬─────────────┐
│ Name             │ Value        │ Prod      │ Preview │ Development │
├──────────────────┼──────────────┼───────────┼─────────┼─────────────┤
│ RUNWAY_API_KEY   │ sk_runway... │ Encrypted │ ✓       │             │
│ MUBERT_API_KEY   │ (hidden)     │ Encrypted │ ✓       │             │
└──────────────────┴──────────────┴───────────┴─────────┴─────────────┘
```

✅ **Environment variables configured!**

---

## Deploy to Production

### Step 1: Production Deployment

After setting environment variables, deploy to production:

```bash
vercel --prod
```

**What happens:**
1. Code is uploaded
2. Function is built
3. Environment variables are applied
4. Production URL is assigned

**Expected output:**
```
🔗  Production: https://backend-example.vercel.app [copied]
✅  Deployed to production in 20s
```

### Step 2: Save Production URL

**Production URL:** `https://backend-example.vercel.app`

**Your API endpoint:** `https://backend-example.vercel.app/api/generate-reel`

📋 **This is your FINAL URL!** Use this in the web interface.

### Step 3: Verify Deployment

Go to: https://vercel.com/dashboard

You should see:
- Project name: `backend-example`
- Status: ✅ Ready
- Latest deployment: Just now
- Production domain: Your URL

✅ **Production deployment complete!**

---

## Test Your Deployment

### Test 1: Health Check

Open browser and go to:
```
https://your-project.vercel.app/api/generate-reel
```

**Expected result:**
```json
{
  "error": "Method not allowed",
  "message": "This endpoint only accepts POST requests"
}
```

✅ **If you see this, your API is working!**

### Test 2: cURL Test (Basic)

```bash
curl -X POST https://your-project.vercel.app/api/generate-reel \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Test prompt",
    "event": {
      "title": "Test Event",
      "start_utc": "2025-07-15T18:00:00Z",
      "location": "Test Location"
    },
    "addMusic": false
  }'
```

**Expected result (if API keys are correct):**
```json
{
  "success": true,
  "videoUrl": "https://...",
  "duration": 20,
  "message": "Reel generated successfully!"
}
```

**This test will:**
- Use real Runway ML API
- Cost ~$1-2
- Take 2-5 minutes

**Alternative:** Skip this test and test from web interface instead.

---

## Connect to GitHub (Optional)

Connecting to GitHub enables automatic deployments when you push code.

### Step 1: Go to Project Settings

1. Open: https://vercel.com/dashboard
2. Click on your project: `backend-example`
3. Click: **Settings** tab
4. Click: **Git** in left sidebar

### Step 2: Connect Repository

1. Click: **Connect Git Repository**
2. Select: **GitHub**
3. Click: **Install Vercel** (if needed)
4. Select: Your repository (`northwoods-events-v2`)
5. Click: **Connect**

### Step 3: Configure Build Settings

1. **Root Directory:** `backend-example`
2. **Framework Preset:** None
3. **Build Command:** (leave empty)
4. **Output Directory:** (leave empty)
5. Click: **Save**

### Step 4: Test Auto-Deployment

1. Make a small change to `backend-example/README.md`
2. Commit and push:
   ```bash
   git add .
   git commit -m "Test auto-deploy"
   git push
   ```
3. Check Vercel dashboard - deployment should start automatically!

✅ **Auto-deployment configured!**

---

## Monitor and Debug

### View Logs

**Real-time logs:**
```bash
vercel logs
```

**Production logs only:**
```bash
vercel logs --prod
```

**Follow logs (live):**
```bash
vercel logs --follow
```

**What you'll see:**
- Function invocations
- Console.log output
- Errors and warnings
- Request timing

### View in Dashboard

1. Go to: https://vercel.com/dashboard
2. Click: Your project
3. Click: **Functions** tab
4. Click: `generate-reel.js`
5. View:
   - Invocations count
   - Error rate
   - Execution time
   - Memory usage

### Check Deployment Status

```bash
vercel inspect
```

Shows:
- Deployment URL
- Commit SHA
- Build time
- Function configuration

---

## Troubleshooting

### Problem: "Command not found: vercel"

**Cause:** Vercel CLI not installed or not in PATH

**Solution:**
```bash
# Reinstall globally
npm install -g vercel

# Or use npx (no installation needed)
npx vercel
```

### Problem: "Error: No existing credentials found"

**Cause:** Not logged into Vercel CLI

**Solution:**
```bash
vercel login
```

### Problem: "Error: Missing required environment variable RUNWAY_API_KEY"

**Cause:** Environment variable not set

**Solution:**
```bash
# Add the variable
vercel env add RUNWAY_API_KEY

# Redeploy
vercel --prod
```

### Problem: Deployment succeeds but API returns 500 errors

**Cause:** Runtime error in function

**Solution:**
1. Check logs:
   ```bash
   vercel logs --prod
   ```

2. Common issues:
   - Invalid Runway ML API key
   - Insufficient credits
   - Network timeout

3. Test API key directly:
   ```bash
   curl -H "Authorization: Bearer YOUR_KEY" \
        https://api.runwayml.com/v1/tasks
   ```

### Problem: "Error: Function execution timeout"

**Cause:** Video generation took too long (>300s)

**Solution:**

**Option 1:** Upgrade to Vercel Pro (900s timeout)

**Option 2:** Modify `vercel.json`:
```json
{
  "functions": {
    "api/generate-reel.js": {
      "maxDuration": 300
    }
  }
}
```

### Problem: "Error: Function size limit exceeded"

**Cause:** Dependencies too large

**Solution:**
1. Remove unused dependencies
2. Use `node-fetch` v2 (smaller than v3)
3. Check `package.json` for minimal dependencies

### Problem: CORS errors in browser

**Cause:** CORS headers not set correctly

**Solution:** Check `generate-reel.js` has:
```javascript
res.setHeader('Access-Control-Allow-Origin', '*');
res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
```

---

## Advanced Configuration

### Custom Domain

1. Go to: Project Settings → Domains
2. Click: **Add Domain**
3. Enter: `api.yourdomain.com`
4. Add DNS records as shown
5. Wait for verification

Your API will be available at:
`https://api.yourdomain.com/api/generate-reel`

### Environment-Specific Variables

```bash
# Development only
vercel env add DEBUG_MODE development

# Preview only
vercel env add ENABLE_LOGGING preview

# Production only
vercel env add RATE_LIMIT production
```

### Increase Memory

Edit `vercel.json`:
```json
{
  "functions": {
    "api/generate-reel.js": {
      "memory": 3008,
      "maxDuration": 300
    }
  }
}
```

Redeploy:
```bash
vercel --prod
```

---

## Usage Monitoring

### Check Bandwidth Usage

1. Go to: https://vercel.com/dashboard/usage
2. View:
   - Bandwidth used
   - Function executions
   - Build minutes

**Free tier limits:**
- 100 GB bandwidth/month
- 100 hours function execution/month
- 6000 minutes build time/month

### Set Up Alerts

1. Settings → Notifications
2. Enable:
   - Deployment failures
   - Usage warnings
   - Error rate alerts

---

## Cost Management

### Vercel Pricing

| Plan | Cost | Bandwidth | Function Time | Best For |
|------|------|-----------|---------------|----------|
| **Hobby** | Free | 100 GB | 100 hours | Testing |
| **Pro** | $20/mo | 1 TB | 1000 hours | Production |
| **Enterprise** | Custom | Unlimited | Unlimited | High volume |

### Estimate Your Costs

**Per reel generation:**
- Bandwidth: ~50 MB (0.05 GB)
- Function time: ~3 minutes (0.05 hours)

**Example: 100 reels/month**
- Bandwidth: 5 GB (within free tier)
- Function time: 5 hours (within free tier)
- **Vercel cost: $0** (free tier sufficient)

**Runway ML cost:** $100-200/month (main expense)

---

## Quick Reference Commands

```bash
# Deploy to preview
vercel

# Deploy to production
vercel --prod

# View logs
vercel logs --prod

# List deployments
vercel ls

# Remove deployment
vercel rm <deployment-url>

# List environment variables
vercel env ls

# Pull environment variables locally
vercel env pull

# Check project info
vercel inspect
```

---

## Next Steps

✅ **Deployment Complete!**

1. Copy your production URL:
   ```
   https://your-project.vercel.app/api/generate-reel
   ```

2. Configure in web interface:
   - Go to: https://dsundt.github.io/northwoods-events-v2/manage.html
   - Click: "⚙️ Backend URL"
   - Paste your URL

3. Test generation:
   - Preview a feed
   - Click "🎥 Generate Reel"
   - Wait 2-5 minutes
   - Preview your video!

---

## Support Resources

- **Vercel Documentation:** https://vercel.com/docs
- **Vercel CLI Reference:** https://vercel.com/docs/cli
- **Community Forum:** https://github.com/vercel/vercel/discussions
- **Status Page:** https://www.vercel-status.com/

---

**Need help?** Check the troubleshooting section above or review the logs with `vercel logs --prod`! 🚀
