# API Key Sync Guide - Access Keys from Any Machine

## 🔄 **Syncing API Keys Across Machines**

By default, API keys are stored in your browser's localStorage, which means they **don't sync** across different machines or browsers. This guide shows you how to sync them using GitHub.

---

## 🔐 **Current Storage (Default)**

### What Gets Stored in localStorage:
- ❌ **GitHub Token** - Machine-specific
- ❌ **OpenAI API Key** - Machine-specific
- ❌ **Runway ML Key** - Machine-specific
- ❌ **Beatoven.ai Key** - Machine-specific
- ❌ **Backend URL** - Machine-specific
- ❌ **Authentication Session** - Machine-specific

### What Gets Stored in GitHub (Synced):
- ✅ **Curated Feed Configurations** - Syncs automatically
- ✅ **Generated ICS Files** - Syncs automatically

---

## 💡 **New: Encrypted Key Sync**

I've added a feature to encrypt and sync your API keys across machines using GitHub!

### How It Works:
1. **Encrypt** all API keys with a master password
2. **Upload** encrypted file to your GitHub repository
3. **Download** from any other machine with the same password
4. Keys are **decrypted** and applied automatically

---

## 🚀 **How to Use Key Sync**

### Step 1: Set Up Keys on First Machine

1. Go to: https://dsundt.github.io/northwoods-events-v2/manage.html
2. Configure all your API keys:
   - GitHub Token
   - OpenAI API Key
   - Runway ML Key
   - Beatoven.ai Key
   - Backend URL

### Step 2: Upload Keys to GitHub

1. Click **"🔄 Sync Keys"** button (top-right)
2. Click **"⬆️ Upload to GitHub"**
3. Enter a **master password** (remember this!)
4. Click **"Execute"**
5. Keys are encrypted and uploaded ✅

### Step 3: Download on Another Machine

1. On new machine, go to manage.html
2. Click **"🔄 Sync Keys"** button
3. Click **"⬇️ Download from GitHub"**
4. Enter:
   - **Master password** (same as upload)
   - **GitHub Token** (temporary, just for download)
   - **GitHub Owner** (your username)
   - **GitHub Repo** (repository name)
5. Click **"Execute"**
6. Keys are downloaded and applied ✅
7. Page refreshes automatically

---

## 🔒 **Security**

### Encryption Details:
- **Algorithm**: AES-GCM (256-bit)
- **Key Derivation**: Password-based
- **Encrypted File**: `config/api-keys.json` in your repo

### What's Protected:
- ✅ Keys are encrypted with your master password
- ✅ No one can read keys without password
- ✅ File is stored in private repository
- ✅ Uses browser's built-in Web Crypto API

### Security Notes:
- ⚠️ **Remember your master password** - cannot be recovered
- ⚠️ Keep password secure - don't share it
- ⚠️ Use a strong password (12+ characters)
- ⚠️ Repository must be **private** for best security

---

## 📋 **Option 1: Manual Sync (Simple)**

If you prefer not to use the encrypted sync, you can manually configure keys on each machine.

### Steps:
1. On each machine/browser, go to manage.html
2. Configure keys manually:
   - Click "🤖 OpenAI API Key" → Enter key
   - Click "🎥 Runway ML Key" → Enter key
   - Click "🎵 Beatoven.ai Key" → Enter key
   - Click "⚙️ Backend URL" → Enter URL

This takes 2-3 minutes per machine but is simpler if you only have 1-2 machines.

---

## 📊 **Sync vs Manual Comparison**

| Method | Setup Time | Syncs Auto? | Security | Best For |
|--------|------------|-------------|----------|----------|
| **Encrypted Sync** | 5 min first time, 1 min after | No (manual click) | High (encrypted) | Multiple machines |
| **Manual Entry** | 2-3 min per machine | No | High (local only) | 1-2 machines |
| **Browser Sync** | Automatic | Yes | Medium | Chrome/Firefox users |

---

## 🌐 **Option 2: Browser Sync (Chrome/Firefox)**

If you use Chrome or Firefox with sync enabled, your localStorage data may sync automatically.

### Chrome Sync:
- Enable "Sync" in Chrome settings
- Sign in to Chrome on all devices
- May sync localStorage (not guaranteed)

### Firefox Sync:
- Enable "Sync" in Firefox settings
- Sign in to Firefox on all devices
- May sync localStorage (not guaranteed)

**Note**: This is browser-dependent and not reliable. Use encrypted sync for guaranteed syncing.

---

## ⚙️ **Technical Details**

### Where Keys are Stored:

#### localStorage (Default):
```javascript
localStorage.getItem('github_token')
localStorage.getItem('openai_api_key')
localStorage.getItem('runway_api_key')
localStorage.getItem('beatoven_api_key')
localStorage.getItem('reel_backend_url')
```

#### GitHub (Encrypted Sync):
```
https://github.com/yourusername/yourrepo/blob/main/config/api-keys.json
```

**File Contents** (encrypted example):
```
R0lGODlhAQABAIAAAAUEBAAAACwAAAAAAQABAAACAkQBADs=...
```

### Encryption Process:
1. Collect all keys from localStorage
2. Convert to JSON string
3. Encrypt with AES-GCM using master password
4. Encode as base64
5. Upload to GitHub via API

### Decryption Process:
1. Download encrypted file from GitHub
2. Decode from base64
3. Decrypt with master password
4. Parse JSON
5. Apply keys to localStorage

---

## 🐛 **Troubleshooting**

### Problem: "Decryption failed - wrong password"

**Cause**: Master password doesn't match the one used for encryption

**Solution**:
- Double-check password (case-sensitive)
- Try upload again with correct password
- Reset by uploading new encrypted file

### Problem: "Configuration file not found"

**Cause**: No encrypted config exists in repository

**Solution**:
1. Upload from a machine that has keys configured
2. Verify GitHub token, owner, and repo are correct

### Problem: "Failed to upload configuration"

**Causes**:
- GitHub token lacks write permissions
- Repository doesn't exist
- Internet connection issue

**Solutions**:
- Verify GitHub token has `repo` scope
- Check repository name and owner
- Try again with good internet connection

### Problem: Keys Don't Work After Download

**Cause**: Page needs refresh to load new keys

**Solution**:
- Page should auto-refresh
- If not, manually refresh (F5)
- Check browser console for errors

---

## 🔄 **Workflow Examples**

### Scenario 1: Set Up New Work Computer

**On Home Computer** (keys already configured):
1. Click "🔄 Sync Keys" → "⬆️ Upload"
2. Enter password: `MySecurePassword123`
3. Keys uploaded ✅

**On Work Computer** (first time):
1. Go to manage.html
2. Click "🔄 Sync Keys" → "⬇️ Download"
3. Enter:
   - Password: `MySecurePassword123`
   - GitHub Token: `ghp_...` (get from GitHub settings)
   - Owner: `yourusername`
   - Repo: `northwoods-events-v2`
4. Keys downloaded ✅
5. Page refreshes
6. Ready to use! ✅

### Scenario 2: Update Keys on All Machines

**After Updating Keys**:
1. Update keys on one machine (e.g., new OpenAI key)
2. Click "🔄 Sync Keys" → "⬆️ Upload"
3. Enter master password
4. New keys uploaded ✅

**On Other Machines**:
1. Click "🔄 Sync Keys" → "⬇️ Download"
2. Enter master password
3. Updated keys downloaded ✅

### Scenario 3: Different Browsers on Same Machine

**Firefox** (has keys):
1. Upload keys with "🔄 Sync Keys"

**Chrome** (needs keys):
1. Download keys with "🔄 Sync Keys"
2. Works across browsers! ✅

---

## 🎯 **Best Practices**

### 1. Use Strong Master Password
- At least 12 characters
- Mix of letters, numbers, symbols
- Don't reuse from other accounts
- Store in password manager

### 2. Keep Repository Private
- Settings → General → Change visibility
- Only you can access encrypted file
- Extra security layer

### 3. Update Keys Regularly
- Rotate API keys periodically
- Upload new version after rotation
- Old encrypted versions stay in Git history

### 4. Backup Master Password
- Write it down somewhere safe
- Store in password manager
- Cannot be recovered if forgotten

### 5. Delete Old Encrypted Files
- If you change master password
- Delete old `config/api-keys.json` from repo
- Upload new encrypted version

---

## 📱 **Mobile Access**

The encrypted sync also works on mobile browsers:

### iOS Safari:
1. Open manage.html in Safari
2. Click "🔄 Sync Keys" → "⬇️ Download"
3. Enter credentials
4. Keys applied to mobile browser ✅

### Android Chrome:
1. Open manage.html in Chrome
2. Click "🔄 Sync Keys" → "⬇️ Download"
3. Enter credentials
4. Keys applied to mobile browser ✅

---

## ⚡ **Quick Reference**

### Upload Keys (From Machine with Keys)
```
1. 🔄 Sync Keys
2. ⬆️ Upload to GitHub
3. Enter master password
4. Execute
```

### Download Keys (From New Machine)
```
1. 🔄 Sync Keys
2. ⬇️ Download from GitHub
3. Enter:
   - Master password
   - GitHub token
   - Owner
   - Repo
4. Execute
5. Page refreshes
```

### File Location
```
config/api-keys.json
```

### Encrypted File Format
```
Base64-encoded AES-GCM encrypted JSON
```

---

## ✅ **Summary**

### Default Behavior (No Sync):
- Keys stored in localStorage
- Specific to each browser/machine
- Must configure keys manually on each machine

### With Encrypted Sync:
- Keys encrypted and stored in GitHub
- Access from any machine with master password
- One-time setup, use everywhere

### Recommendation:
- **Multiple machines**: Use encrypted sync
- **Single machine**: Use default (simpler)
- **Team/shared**: Use encrypted sync with shared password

---

**Now your API keys can sync securely across all your devices!** 🔄🔐✨
