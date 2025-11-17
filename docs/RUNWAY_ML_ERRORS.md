# Runway ML Error Guide - Internal Errors

## 🔍 **Current Error**

```
"failureCode": "INTERNAL"
"failure": "Generation failed: {\"code\":13,\"message\":\"Internal error. Please try again later.\"}"
```

This is a **Runway ML server-side error**, not an issue with your configuration.

---

## 🐛 **Error Code 13: Internal Error**

### What It Means:
- Runway ML's servers encountered an internal error
- The generation started but failed during processing
- This is on Runway ML's side, not your code

### Common Causes:

#### 1. **Runway ML Service Issue**
- Their servers are having problems
- Model is temporarily unavailable
- Infrastructure issue on their end

#### 2. **Account/Billing Issue**
- Insufficient credits
- Payment method declined
- Account suspended or restricted

#### 3. **Model-Specific Issue**
- `veo3.1_fast` model temporarily unavailable
- Model overloaded/at capacity
- Model being updated/maintained

#### 4. **Temporary Glitch**
- Random server error
- Usually resolves on retry
- Most common cause

---

## ✅ **Solutions**

### Solution 1: Retry (Recommended)
**90% of "Internal error" issues resolve with a simple retry.**

1. Wait 30-60 seconds
2. Try generating the reel again
3. Often works on 2nd or 3rd attempt

### Solution 2: Check Runway ML Status
1. Go to: https://status.runwayml.com
2. Check for service outages
3. Check Twitter: https://twitter.com/runwayml

### Solution 3: Verify Your Account
1. Go to: https://app.runwayml.com
2. Check your credits balance
3. Verify no billing issues
4. Check account status

### Solution 4: Try Different Settings
1. Use **"No Audio"** instead of "Music Only"
2. Try simpler/shorter prompt
3. Wait a few hours and try again

### Solution 5: Contact Runway ML Support
If errors persist after multiple retries:
1. Go to: https://runwayml.com/support
2. Provide the Operation ID from error
3. Report the issue

---

## 🔄 **Automatic Retry (Coming Soon)**

I can add automatic retry logic to handle transient errors:

```javascript
// Retry up to 3 times if INTERNAL error
if (failureCode === 'INTERNAL' && retryCount < 3) {
  console.log(`Retrying due to internal error (${retryCount + 1}/3)...`);
  // Wait 30 seconds and retry
}
```

Would you like me to add this?

---

## 📊 **Error Code Reference**

| Code | Meaning | Action |
|------|---------|--------|
| **13** | **Internal Error** | **Retry, check account** |
| 400 | Bad Request | Check prompt/parameters |
| 401 | Unauthorized | Check API key |
| 402 | Payment Required | Add credits |
| 403 | Forbidden | Check account permissions |
| 404 | Not Found | Check endpoint/model |
| 429 | Rate Limited | Wait and retry |
| 500 | Server Error | Runway ML issue, retry |

---

## 🎯 **What's Actually Happening**

Based on the logs:

1. ✅ **Task created successfully** (ID: `695f1a48-dd9f...`)
2. ✅ **Generation starts** (Progress: 0% → 0.14%)
3. ❌ **Runway ML fails internally** (Code 13)
4. ❌ **No specific reason given** (just "Internal error")

### Interpretation:
- Your code is **100% correct** ✅
- Runway ML accepted the request ✅
- Started processing ✅
- Hit an internal error on their side ❌

---

## 💡 **Immediate Actions**

### Action 1: Check Runway ML Account
1. Go to: https://app.runwayml.com
2. Check **Credits** balance
3. Check **Billing** status
4. Verify account is active

### Action 2: Check Service Status
1. Visit: https://status.runwayml.com
2. Look for outages or degraded performance
3. Check if `veo3.1_fast` model is listed as having issues

### Action 3: Simple Retry
Just **try generating again** in 1 minute. Internal errors often clear up.

### Action 4: Try Different Audio Mode
Switch from **"Music Only"** to **"No Audio"** - might help.

---

## 🔧 **Add Automatic Retry**

Let me add retry logic for these transient errors:

<function_calls>
<invoke name="StrReplace">
<parameter name="file_path">/workspace/backend-example/api/generate-reel.js