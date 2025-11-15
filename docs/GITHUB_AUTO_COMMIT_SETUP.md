# Auto-Commit to GitHub Setup Guide

This guide explains how to set up automatic commits from the web interface so you don't need to manually download and commit the curated.yaml file.

## Overview

With GitHub API integration, the web interface can:
1. **Auto-save** configurations directly to your repository
2. **Auto-trigger** GitHub Actions workflow to regenerate feeds
3. **Eliminate** manual download/commit steps

## Quick Setup (5 Minutes)

### Step 1: Create a GitHub Personal Access Token

1. Go to https://github.com/settings/tokens
2. Click "Generate new token" → "Generate new token (classic)"
3. Give it a name: `Northwoods Events Manager`
4. Set expiration: `No expiration` (or your preference)
5. Select scopes:
   - ✅ **`repo`** (Full control of private repositories)
   - ✅ **`workflow`** (Update GitHub Action workflows)
6. Click "Generate token"
7. **Copy the token** (you won't see it again!)

### Step 2: Configure in Web Interface

1. Visit your manage.html page
2. Click **"🔑 Configure GitHub Token"** button
3. Paste your token
4. Click **"Save Token"**
5. Status should show: "✓ GitHub Connected"

### Step 3: Use Auto-Save

Now when you create/edit feeds:
1. Make changes in web interface
2. Click **"💾 Save to GitHub"** (instead of "Download Config")
3. Optionally check **"🔄 Auto-trigger workflow"**
4. Done! Changes are committed and workflow triggered automatically

## Detailed Instructions

### Creating the GitHub Token

**Required Permissions:**
- `repo` scope - Allows committing files to your repository
- `workflow` scope - Allows triggering GitHub Actions workflows

**Security Notes:**
- Token is stored in browser localStorage (your device only)
- Never share your token with anyone
- Can be revoked anytime at https://github.com/settings/tokens
- Consider setting an expiration date for security

### Using Auto-Commit

**Method 1: Save Individual Feed**
```
1. Edit feed in web interface
2. Click "💾 Save to GitHub" button
3. Feed config auto-commits to repository
4. (Optional) Workflow auto-triggers
5. ICS files regenerate automatically
```

**Method 2: Save All Feeds**
```
1. Go to "My Feeds" page
2. Click "💾 Save All to GitHub" button
3. All feed configs auto-commit
4. Workflow auto-triggers
5. All ICS files regenerate
```

### Workflow Triggers

**Auto-trigger Options:**
- **Manual**: Save config, trigger workflow later
- **Automatic**: Save config + trigger workflow in one click
- **Scheduled**: Workflow runs daily at 09:15 UTC anyway

**Checking Workflow Status:**
1. Go to https://github.com/your-username/your-repo/actions
2. See the running/completed workflows
3. Click for details and logs

## Implementation Code

### JavaScript Functions Added

```javascript
// Auto-detect repository from URL
detectGitHubRepo()  // Called on page load

// Save feed configuration to GitHub
saveToGitHub(autoTrigger = false)

// Trigger GitHub Actions workflow
triggerWorkflow()

// Token management
saveGitHubToken(token)
clearGitHubToken()
```

### API Calls Made

**1. Get Current File SHA** (to update existing file)
```
GET /repos/{owner}/{repo}/contents/config/curated.yaml
```

**2. Commit File**
```
PUT /repos/{owner}/{repo}/contents/config/curated.yaml
Body: {
  message: "Update curated feeds via web interface",
  content: base64(yaml),
  sha: current_sha,
  branch: "main"
}
```

**3. Trigger Workflow** (optional)
```
POST /repos/{owner}/{repo}/actions/workflows/build-ics-and-deploy.yml/dispatches
Body: {
  ref: "main"
}
```

## UI Changes

### Updated Alert Banner
```html
<div class="alert alert-info">
  <strong>ℹ️ GitHub Integration:</strong>
  <span id="github-status">✓ GitHub Connected</span>
  <button onclick="showGitHubTokenDialog()">🔑 Configure Token</button>
</div>
```

### New Buttons on My Feeds Page
```html
<button onclick="saveToGitHub(false)">💾 Save to GitHub</button>
<button onclick="saveToGitHub(true)">💾🔄 Save & Trigger Workflow</button>
```

### Token Configuration Dialog
```html
<div id="github-token-dialog">
  <input type="password" placeholder="Paste GitHub token...">
  <button onclick="saveToken()">Save Token</button>
  <button onclick="clearToken()">Clear Token</button>
</div>
```

## Security Considerations

### Token Storage
- Stored in browser `localStorage`
- Only accessible on your device
- Not sent to any third parties
- Only used for GitHub API calls

### Token Permissions
- `repo` scope gives full repository access
- Can commit to any branch
- Can read private repositories
- **Use carefully** - treat like a password

### Best Practices
1. **Don't share** your token
2. **Set expiration** dates when possible
3. **Revoke immediately** if compromised
4. **Create repo-specific** tokens if sharing device
5. **Use GitHub Apps** for production (more secure)

## Troubleshooting

### "GitHub Token Required" Error

**Cause**: Token not configured

**Solution**:
1. Click "🔑 Configure GitHub Token"
2. Enter your Personal Access Token
3. Click "Save Token"

### "Failed to commit file" Error

**Possible Causes:**
- Invalid token
- Token expired
- Insufficient permissions
- Repository doesn't exist

**Solutions:**
1. Verify token is correct
2. Check token hasn't expired
3. Ensure `repo` scope is enabled
4. Verify repository name is correct

### "Failed to trigger workflow" Error

**Possible Causes:**
- `workflow` scope not enabled
- Workflow file doesn't exist
- Branch name incorrect

**Solutions:**
1. Ensure `workflow` scope is enabled on token
2. Verify workflow file exists: `.github/workflows/build-ics-and-deploy.yml`
3. Check branch name (usually `main`)

### Token Keeps Getting Cleared

**Cause**: Browser localStorage cleared

**Solutions:**
1. Don't use private/incognito mode
2. Don't clear browser data
3. Re-enter token when needed
4. Consider browser extensions that preserve localStorage

## Advanced Usage

### Multiple Devices

**Option 1: Same Token**
- Enter same token on each device
- All devices can commit

**Option 2: Different Tokens**
- Create separate token per device
- Name tokens by device for tracking
- Easier to revoke individual devices

### Automation

**With GitHub API:**
```javascript
// Programmatic save
await saveToGitHub(true);  // Save and trigger

// Check status
const configured = isGitHubConfigured();
```

**With CI/CD:**
- Commits from web interface trigger CI
- Can run tests before deploying
- Can notify on changes

### Repository Detection

The system auto-detects your repository from the URL:
```
URL: https://username.github.io/repo-name/manage.html
Detects:
  owner: username
  repo: repo-name
```

**Manual Override:**
```javascript
GITHUB_OWNER = 'my-username';
GITHUB_REPO = 'my-repo';
GITHUB_BRANCH = 'main';  // or 'develop', etc.
```

## Comparison: Manual vs Auto

| Feature | Manual Download | Auto-Commit |
|---------|----------------|-------------|
| **Download File** | Required | Not needed |
| **Open Terminal** | Required | Not needed |
| **Git Commands** | Required | Not needed |
| **Commit Message** | Manual | Automatic |
| **Push to GitHub** | Manual | Automatic |
| **Trigger Workflow** | Manual | Automatic (optional) |
| **Time Required** | 2-3 minutes | 5 seconds |
| **Steps** | 6+ steps | 1 click |

## Migration from Manual to Auto

**If you've been using manual download:**

1. **One-time setup**: Configure GitHub token (5 minutes)
2. **From now on**: Use "Save to GitHub" button
3. **That's it!** No more manual commits needed

**Your existing feeds:**
- Continue to work
- No migration needed
- Just start using auto-save

## FAQs

**Q: Is my token secure?**
A: Token is stored locally in your browser only. However, it provides full repository access, so treat it like a password.

**Q: What if I lose my token?**
A: Create a new one at https://github.com/settings/tokens and re-enter it in the interface.

**Q: Can others see my token?**
A: No, it's stored in your browser's localStorage, not sent anywhere except to GitHub API.

**Q: Do I need this for local Flask server?**
A: No, Flask server can write files directly. This is for GitHub Pages only.

**Q: Can I use fine-grained tokens?**
A: Yes! Create a fine-grained token with `Contents: Read and write` + `Workflows: Read and write` permissions.

**Q: What happens if token expires?**
A: Auto-save stops working. Create new token and re-enter it.

## Next Steps

1. ✅ **Create GitHub token** (Step 1)
2. ✅ **Configure in web interface** (Step 2)
3. ✅ **Test with a feed** - Create/edit and save to GitHub
4. ✅ **Verify commit** - Check GitHub repository
5. ✅ **Check workflow** - Ensure it runs
6. ✅ **Subscribe to feed** - Add ICS URL to calendar

Enjoy seamless curated feed management! 🎉
