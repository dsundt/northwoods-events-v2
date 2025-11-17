# Backend URL Workaround - Using Hashed Deployment URLs

## Problem

The Vercel production domain (`northwoods-reel-api.vercel.app`) keeps pointing to old deployments, even after manual aliasing. The OPTIONS preflight request returns 404, causing CORS failures.

## Root Cause

Vercel is not automatically assigning the production domain to new deployments, and manual aliases don't persist or get overridden.

## Solution Implemented

**Frontend now uses the working hashed deployment URL directly:**

```
https://northwoods-reel-bktn7xmx6-dan-sundts-projects.vercel.app/api/generate-reel
```

This deployment has:
- ✅ Rewrite rule for OPTIONS routing
- ✅ CORS headers properly configured
- ✅ All environment variables set
- ✅ Working OPTIONS preflight (returns 200)

## Testing

```bash
# Test OPTIONS (preflight) - Should return 200
curl -I -X OPTIONS https://northwoods-reel-bktn7xmx6-dan-sundts-projects.vercel.app/api/generate-reel

# Expected output:
# HTTP/2 200
# access-control-allow-origin: *
# access-control-allow-methods: GET, POST, OPTIONS

# Test GET (health check)
curl https://northwoods-reel-bktn7xmx6-dan-sundts-projects.vercel.app/api/generate-reel

# Expected output:
# {"status":"ok","runwayConfigured":true,"beatovenConfigured":true,"cors":"enabled"}
```

## Frontend Changes

Updated default backend URL in:
- `/workspace/public/manage.js`
- `/workspace/docs/manage.js`
- `/workspace/github-pages/manage.js`

Changes:
```javascript
// OLD (doesn't work):
const BACKEND_URL = localStorage.getItem('reel_backend_url') || 
                    'https://northwoods-reel-api.vercel.app/api/generate-reel';

// NEW (works):
const BACKEND_URL = localStorage.getItem('reel_backend_url') || 
                    'https://northwoods-reel-bktn7xmx6-dan-sundts-projects.vercel.app/api/generate-reel';
```

## Browser Testing

After GitHub Pages deploys (2-3 minutes):

1. **Clear browser cache**: Cmd+Shift+Delete → Clear all data
2. **Close all tabs**
3. Open: https://dsundt.github.io/northwoods-events-v2/manage.html
4. Select event → Create Reel → Generate
5. **Should work without CORS errors!**

## When To Update URL

Each time you redeploy the backend, you'll get a new hashed URL. Update the frontend when:

1. You add new backend features
2. You change backend configuration
3. The current deployment expires (Vercel keeps them ~30 days)

### How To Update

1. **Deploy backend**:
   ```bash
   cd ~/Documents/northwoods-events-v2/backend-example
   vercel --prod --force
   ```

2. **Note the deployment URL** from output:
   ```
   ✅  Production: https://northwoods-reel-XXXXX-dan-sundts-projects.vercel.app
   ```

3. **Update frontend** (3 locations):
   - Edit `/workspace/public/manage.js`
   - Replace URL in 2 places (search for `northwoods-reel-bktn7xmx6`)
   - Copy to `docs/` and `github-pages/`
   - Commit and push

4. **Test immediately**:
   ```bash
   # Test OPTIONS
   curl -I -X OPTIONS https://northwoods-reel-XXXXX-dan-sundts-projects.vercel.app/api/generate-reel
   ```

## Alternative: Fix Production Domain (TODO)

To avoid this workaround in the future:

### Option 1: Vercel Dashboard Configuration

1. Go to: https://vercel.com/dan-sundts-projects/northwoods-reel-api/settings/general
2. Under **"Production Branch"**, ensure it's set to `main`
3. Go to **Domains** tab
4. Remove existing `northwoods-reel-api.vercel.app` if present
5. Click **"Add Domain"**
6. Enter: `northwoods-reel-api.vercel.app`
7. Ensure it shows **"Production"** badge
8. **Important**: Check "Assign to all production deployments"

### Option 2: Deployment Script

Create `backend-example/deploy.sh`:

```bash
#!/bin/bash
cd ~/Documents/northwoods-events-v2/backend-example

# Deploy
vercel --prod --force > /tmp/deploy.log 2>&1

# Extract deployment URL
DEPLOY_URL=$(grep -o 'https://northwoods-reel-[^.]*\.vercel\.app' /tmp/deploy.log | head -1)

if [ -n "$DEPLOY_URL" ]; then
    echo "Deployment: $DEPLOY_URL"
    
    # Alias
    sleep 5
    vercel alias "$DEPLOY_URL" northwoods-reel-api.vercel.app
    
    # Test
    sleep 5
    curl -I -X OPTIONS https://northwoods-reel-api.vercel.app/api/generate-reel | head -3
else
    echo "ERROR: Could not extract deployment URL"
    cat /tmp/deploy.log
    exit 1
fi
```

Usage:
```bash
chmod +x deploy.sh
./deploy.sh
```

## Known Issues

1. **Production domain aliasing doesn't persist**
   - Workaround: Use hashed URLs directly (current solution)
   - Long-term: Fix domain configuration in Vercel dashboard

2. **Browser caching is extremely aggressive**
   - Always test in incognito/private window first
   - Clear cache completely (not just refresh)
   - Check Network tab for OPTIONS requests

3. **GitHub Pages deployment delay**
   - Changes take 2-3 minutes to deploy
   - Always verify GitHub Actions completed
   - Hard refresh after deployment

## Verification Checklist

After any backend/frontend update:

- [ ] Backend OPTIONS returns 200 (not 404)
- [ ] Backend GET returns JSON health check
- [ ] CORS headers present in response
- [ ] Frontend deployed to GitHub Pages
- [ ] Browser cache cleared
- [ ] Reel generation works end-to-end
- [ ] Video saves to repository
- [ ] Gallery displays new reel

## Current Status

**Backend**: ✅ Working on hashed URL  
**Frontend**: ✅ Updated to use hashed URL  
**Production Domain**: ❌ Not working (points to old deployment)  
**Workaround**: ✅ Functional and deployed  

**Last Updated**: 2025-11-17  
**Current Backend URL**: `https://northwoods-reel-bktn7xmx6-dan-sundts-projects.vercel.app/api/generate-reel`  
**Status**: Production Ready with Workaround
