# Authentication Setup Guide

## 🔐 Simple Authentication for GitHub Pages

Your Northwoods Events solution now includes basic authentication to control access.

---

## ⚙️ Configuration

### Default Credentials

**Password**: `northwoods2025`

(Username is optional - you can just use the password)

---

## 🔧 How to Change the Password

### Method 1: Generate New Password Hash (Recommended)

1. **Go to a SHA-256 hash generator**:
   - https://emn178.github.io/online-tools/sha256.html
   - Or use browser console (see Method 2)

2. **Enter your new password** (e.g., "MySecurePassword123")

3. **Copy the generated hash** (64-character hex string)

4. **Update `public/auth.js`**:
   - Find line with `VALID_PASSWORD_HASH`
   - Replace the hash value with your new hash

```javascript
// Change this line:
const VALID_PASSWORD_HASH = 'a1b2c3d4e5f6...'; // old hash

// To:
const VALID_PASSWORD_HASH = 'your_new_hash_here';
```

5. **Commit and push** to GitHub:
   ```bash
   cd ~/Documents/northwoods-events-v2
   git add public/auth.js
   git commit -m "Update authentication password"
   git push origin main
   ```

### Method 2: Use Browser Console

1. Open browser console (F12)
2. Paste and run:
   ```javascript
   const password = 'YourNewPassword123';
   crypto.subtle.digest('SHA-256', new TextEncoder().encode(password))
     .then(h => console.log(Array.from(new Uint8Array(h))
       .map(b => b.toString(16).padStart(2, '0')).join('')));
   ```
3. Copy the output hash
4. Update `public/auth.js` as shown in Method 1

---

## 👥 Adding Multiple Users

You can add username/password combinations for different users.

### Edit `public/auth.js`

Find the `VALID_USERS` object:

```javascript
const VALID_USERS = {
    // Example: username: password hash
    'user1': 'hash_here',
    'admin': 'another_hash_here',
    'john': 'johns_password_hash',
};
```

### Adding a New User

1. **Generate password hash** for new user
2. **Add to VALID_USERS**:
   ```javascript
   const VALID_USERS = {
       'user1': 'e7d4a9a6c8f4b5c6...',  // existing
       'jane': 'your_generated_hash...',  // new user
   };
   ```
3. **Commit and push** changes

---

## 🚀 How It Works

### Login Process

1. User visits any page (e.g., manage.html, reel-gallery.html)
2. `auth.js` checks for valid session in localStorage
3. If not authenticated, shows login dialog
4. User enters username (optional) and password
5. Password is hashed with SHA-256 and compared
6. If valid, session token stored for 24 hours
7. User can access all pages

### Session Management

- **Duration**: 24 hours
- **Storage**: localStorage (client-side)
- **Auto-logout**: After 24 hours
- **Manual logout**: Click "🚪 Sign Out" button (bottom-right)

---

## 📁 Protected Pages

Add authentication to any page by including the script:

```html
<script src="auth.js"></script>
```

### Already Protected:
- ✅ `manage.html` (main interface)
- ✅ `instagram-gallery.html` (image gallery)
- ✅ `reel-gallery.html` (video gallery)

### To Protect Additional Pages:

1. Open the HTML file
2. Add before closing `</body>` tag:
   ```html
   <script src="auth.js"></script>
   </body>
   ```
3. Commit and push

---

## 🔒 Security Notes

### What This Provides:
- ✅ Basic access control for casual use
- ✅ Prevents casual browsing / search engine indexing
- ✅ Good for limiting access to friends/family/team
- ✅ Client-side authentication (no server needed)

### What This Does NOT Provide:
- ❌ **NOT** secure against determined attackers
- ❌ **NOT** suitable for highly sensitive data
- ❌ Passwords stored as hashes in client-side code (visible in source)
- ❌ No rate limiting or brute-force protection
- ❌ Can be bypassed by viewing page source or API calls

### For Stronger Security:
- Use GitHub Pages + Cloudflare Access
- Deploy behind a backend with OAuth (Auth0, Firebase)
- Use Netlify with Identity or Vercel with authentication
- Move to a platform with built-in auth (e.g., Heroku, AWS Amplify)

---

## 🎯 Use Cases

### Good For:
- ✅ Personal projects
- ✅ Small team internal tools
- ✅ Family/friend access control
- ✅ Preventing accidental public access
- ✅ Keeping content off search engines

### Not Good For:
- ❌ Financial data
- ❌ Personal health information
- ❌ Business-critical systems
- ❌ Compliance-required applications
- ❌ Protection against skilled attackers

---

## 🔄 Logout

### Manual Logout:
- Click **"🚪 Sign Out"** button (bottom-right of any page)
- Confirms before logging out
- Clears session and reloads page

### Automatic Logout:
- After 24 hours of inactivity
- When manually logging out
- When clearing browser data

### Force Logout (Developer):
```javascript
// Run in browser console
localStorage.removeItem('northwoods_auth_token');
localStorage.removeItem('northwoods_auth_expiry');
location.reload();
```

---

## 🧪 Testing

### Test Login:
1. Go to https://dsundt.github.io/northwoods-events-v2/manage.html
2. Enter password: `northwoods2025`
3. Should grant access

### Test Logout:
1. Click "🚪 Sign Out"
2. Should show login dialog again

### Test Session Expiry:
```javascript
// In browser console - set expiry to past
localStorage.setItem('northwoods_auth_expiry', '0');
location.reload();
// Should show login dialog
```

---

## 📊 Monitoring Access

Since this is client-side auth, there's no built-in logging. To track access:

### Option 1: GitHub Pages Analytics
- Use Google Analytics
- Add tracking script to your HTML pages

### Option 2: Vercel Analytics (if migrating)
- Deploy to Vercel instead of GitHub Pages
- Built-in analytics available

### Option 3: Cloudflare (if using custom domain)
- Put domain through Cloudflare
- View analytics in Cloudflare dashboard

---

## 🛠️ Customization

### Change Session Duration

Edit `public/auth.js`:

```javascript
// Change from 24 hours to 7 days
const SESSION_DURATION = 7 * 24 * 60 * 60 * 1000; // 7 days

// Or 1 hour
const SESSION_DURATION = 60 * 60 * 1000; // 1 hour
```

### Customize Login Dialog

Find `showLoginDialog()` function in `auth.js` and modify HTML/CSS.

### Remove "Sign Out" Button

Comment out or remove:

```javascript
// addLogoutButton(); // Comment this line
```

---

## ❓ FAQ

### Q: Can users share login credentials?
**A**: Yes - this is password-based auth. Multiple users can use the same password.

### Q: Can I track who accessed what?
**A**: Not with this client-side solution. You'd need backend analytics.

### Q: What if I forget the password?
**A**: You can update the hash in `auth.js` and redeploy. No password recovery mechanism.

### Q: Can I add two-factor authentication?
**A**: Not with this simple solution. You'd need a backend service.

### Q: Is this GDPR/HIPAA compliant?
**A**: No. This is basic access control only. Not suitable for compliance requirements.

### Q: Can I use this with a custom domain?
**A**: Yes! Works with custom domains on GitHub Pages.

---

## 🚀 Quick Reference

### Default Password
```
northwoods2025
```

### Generate Hash (Browser Console)
```javascript
const pw = 'YourPassword';
crypto.subtle.digest('SHA-256', new TextEncoder().encode(pw))
  .then(h => console.log(Array.from(new Uint8Array(h))
    .map(b => b.toString(16).padStart(2, '0')).join('')));
```

### Files to Edit
- **Password**: `public/auth.js` → `VALID_PASSWORD_HASH`
- **Users**: `public/auth.js` → `VALID_USERS`
- **Duration**: `public/auth.js` → `SESSION_DURATION`

### Protect New Page
```html
<script src="auth.js"></script>
```

---

**Your site now has basic authentication! Remember to change the default password.** 🔐
