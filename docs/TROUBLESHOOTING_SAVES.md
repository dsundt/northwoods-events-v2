# Troubleshooting - Images and Reels Not Saving to Repository

## 🔍 **Issue 1: ICS File Not Found**

### Problem:
Looking for: `https://dsundt.github.io/northwoods-events-v2/curated/rcltest.ics`  
Getting: 404 error

### Root Cause:
**Wrong filename!** The filename is auto-generated from the Feed ID.

- **Feed ID**: `RCLMinocquaEvents`
- **Generated filename**: `rclminocquaevents.ics` (lowercase, no camelCase)

### ✅ **Correct URL**:
```
https://dsundt.github.io/northwoods-events-v2/curated/rclminocquaevents.ics
```

### How to Find Your ICS URL:
1. Go to manage.html
2. Find your feed
3. Look for "ICS Filename" field
4. Use the exact filename shown

### To Get `rcltest.ics` Instead:
1. Edit the feed in manage.html
2. Change Feed ID from `RCLMinocquaEvents` to `rcltest`
3. Save configuration
4. Click "⚡ Regenerate Feed"
5. New file will be `rcltest.ics`

---

## 🔍 **Issue 2: Images and Reels Not Saving to Repository**

### Symptoms:
- Images/reels generate successfully
- Click "Save to Repository"
- Shows success message
- But files DON'T appear in GitHub repository
- Gallery pages show no images/reels

### Common Causes:

#### 1. **GitHub Token Not Configured**
**Check**: Click "🔑 GitHub Token" - is a token configured?

**Fix**:
1. Go to: https://github.com/settings/tokens
2. Click "Generate new token (classic)"
3. Set expiration (e.g., 90 days)
4. Check scopes:
   - ✅ `repo` (all)
   - ✅ `workflow`
5. Generate token
6. Copy token
7. In manage.html, click "🔑 GitHub Token"
8. Paste token
9. Save

#### 2. **GitHub Token Missing Permissions**
**Check**: Does your token have `repo` scope?

**Fix**: Create new token with correct permissions (see above)

#### 3. **GITHUB_OWNER/GITHUB_REPO Not Set**
**Check**: Open browser console (F12) and run:
```javascript
console.log({
  owner: localStorage.getItem('github_owner'),
  repo: localStorage.getItem('github_repo'),
  token: localStorage.getItem('github_token') ? 'Set' : 'Not set'
});
```

**Fix if null**:
```javascript
localStorage.setItem('github_owner', 'dsundt');
localStorage.setItem('github_repo', 'northwoods-events-v2');
```

Then refresh page.

#### 4. **Silent Failures**
**Check**: Open console (F12) when clicking "Save to Repository"

**Look for**:
- `GitHub config: {owner: "dsundt", repo: "northwoods-events-v2", hasToken: true}`
- `Uploading to: public/instagram/...`
- `GitHub API error:` (shows actual error)

**Common errors**:
- `Bad credentials` → Token invalid
- `Resource not accessible` → Token lacks permissions
- `Not Found` → Owner/repo wrong

---

## 🔧 **Complete Fix for Saves Not Working**

### Step 1: Verify GitHub Configuration

In browser console (F12):
```javascript
// Check all GitHub settings
console.log('GitHub Owner:', localStorage.getItem('github_owner'));
console.log('GitHub Repo:', localStorage.getItem('github_repo'));
console.log('GitHub Token:', localStorage.getItem('github_token') ? '✅ Set (length: ' + localStorage.getItem('github_token').length + ')' : '❌ Not set');
console.log('GitHub Branch:', localStorage.getItem('github_branch'));
```

**All should show values!**

### Step 2: Set Missing Values

If any are null, run:
```javascript
localStorage.setItem('github_owner', 'dsundt');
localStorage.setItem('github_repo', 'northwoods-events-v2');
localStorage.setItem('github_branch', 'main');
```

### Step 3: Configure GitHub Token

1. Create token at: https://github.com/settings/tokens
2. Click "🔑 GitHub Token" in manage.html
3. Paste token
4. Save

### Step 4: Test Save

1. Generate an image
2. Click "Save to Repository"
3. **Watch console (F12)** for errors
4. Should see: `✅ Image saved to repository!`

### Step 5: Verify in GitHub

1. Go to: https://github.com/dsundt/northwoods-events-v2/tree/main/public/instagram
2. Image should appear within 5-10 seconds
3. Refresh if needed

---

## 🐛 **Debugging Saves**

### Enable Detailed Logging

When you click "Save to Repository", watch console (F12):

**Successful Save**:
```
GitHub config: {owner: "dsundt", repo: "northwoods-events-v2", hasToken: true}
Uploading to: public/instagram/2025-11-20-event-name.jpg
[Network tab shows PUT request to api.github.com - Status 201]
Video committed successfully: {content: {...}, commit: {...}}
```

**Failed Save**:
```
GitHub config: {owner: "", repo: "", hasToken: false}
Upload error: GitHub token not configured

OR

GitHub API error: {message: "Bad credentials", documentation_url: "..."}
Upload error: Bad credentials
```

### Common Error Messages:

| Error | Cause | Fix |
|-------|-------|-----|
| `GitHub token not configured` | No token set | Configure token |
| `Bad credentials` | Token invalid/expired | Create new token |
| `Resource not accessible` | Token lacks `repo` scope | Create token with `repo` scope |
| `Not Found` | Owner/repo wrong | Set owner/repo in localStorage |
| `Validation Failed` | File too large (>100MB) | Reduce video quality |
| `Reference does not exist` | Branch doesn't exist | Check branch name is 'main' |

---

## ✅ **Quick Diagnostic**

Run this in browser console (F12):

```javascript
// Complete diagnostic
async function testGitHubSave() {
  const owner = localStorage.getItem('github_owner') || 'dsundt';
  const repo = localStorage.getItem('github_repo') || 'northwoods-events-v2';
  const token = localStorage.getItem('github_token');
  
  console.log('Testing GitHub API access...');
  console.log('Owner:', owner);
  console.log('Repo:', repo);
  console.log('Token:', token ? '✅ Set (length: ' + token.length + ')' : '❌ Not set');
  
  if (!token) {
    console.error('❌ No GitHub token configured!');
    return;
  }
  
  // Test API access
  try {
    const response = await fetch(`https://api.github.com/repos/${owner}/${repo}`, {
      headers: {
        'Authorization': `Bearer ${token}`,
        'Accept': 'application/vnd.github.v3+json'
      }
    });
    
    if (response.ok) {
      const data = await response.json();
      console.log('✅ GitHub API access working!');
      console.log('Repository:', data.full_name);
      console.log('Permissions:', data.permissions);
    } else {
      const error = await response.json();
      console.error('❌ GitHub API error:', error);
    }
  } catch (error) {
    console.error('❌ Failed to connect to GitHub API:', error);
  }
}

testGitHubSave();
```

---

## 📋 **Checklist for Saves to Work**

Before images/reels can save:

- [ ] GitHub Token configured (click "🔑 GitHub Token")
- [ ] Token has `repo` scope
- [ ] Token is not expired
- [ ] Owner set: `dsundt`
- [ ] Repo set: `northwoods-events-v2`
- [ ] Branch set: `main`
- [ ] Console shows `hasToken: true` when saving

---

## 🎯 **Expected Success Flow**

### When Save Works:

1. **Click** "Save to Repository"
2. **Toast**: "Uploading image to repository..."
3. **Console**: `GitHub config: {owner: "dsundt", repo: "northwoods-events-v2", hasToken: true}`
4. **Console**: `Uploading to: public/instagram/2025-11-20-event.jpg`
5. **Toast**: "Committing to repository..."
6. **Console**: `Video committed successfully: {...}`
7. **Toast**: "✅ Image saved to repository!"
8. **UI**: Shows "✅ Saved!" with gallery link

### When Save Fails:

1. **Click** "Save to Repository"
2. **Console**: Shows error with details
3. **Toast**: "Failed to save: [specific error message]"
4. **Check** error message for cause

---

## ✅ **After GitHub Pages Updates**

Once the fixes deploy (2-5 minutes):

1. **Refresh** manage.html
2. **Configure** GitHub token if not already
3. **Generate** image
4. **Save** to repository
5. **Check** GitHub repo - file should appear
6. **Check** instagram-gallery.html - image should appear

---

**The code for saving is correct - the issue is likely GitHub token configuration or permissions!** 🔑

Run the diagnostic script above to check your GitHub API access!
