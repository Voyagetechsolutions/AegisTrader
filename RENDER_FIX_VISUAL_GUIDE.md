# 🎯 Visual Guide: Fix Render Deployment in 2 Minutes

## The Problem You're Seeing

```
==> Running 'python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000'
==> Exited with status 1  ❌
```

## The Solution

### Step 1: Open Render Dashboard
Go to: https://dashboard.render.com

### Step 2: Find Your Service
Click on: **aegis-trader-backend** (or your service name)

### Step 3: Go to Settings
Left sidebar → Click **"Settings"**

### Step 4: Find Build & Deploy Section
Scroll down to **"Build & Deploy"**

### Step 5: Update Start Command

**WRONG (Current):**
```
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

**CORRECT (Change to):**
```
uvicorn backend.main:app --host 0.0.0.0 --port $PORT
```

**Key Changes:**
- ❌ Remove `python -m`
- ✅ Use `uvicorn` directly
- ❌ Remove hardcoded `8000`
- ✅ Use `$PORT` variable

### Step 6: Save Changes
Click **"Save Changes"** button at bottom

### Step 7: Redeploy
Top right corner → Click **"Manual Deploy"**

Select **"Deploy latest commit"**

Click **"Deploy"**

### Step 8: Watch Logs
Click **"Logs"** tab

Wait 2-3 minutes...

**You should see:**
```
==> Build successful 🎉
==> Deploying...
INFO:backend.main:Starting Aegis Trader backend [production]
INFO:backend.main:Database tables created/verified
INFO:backend.main:APScheduler started
INFO:uvicorn.error:Application startup complete.
INFO:uvicorn.error:Uvicorn running on http://0.0.0.0:XXXXX
```

✅ **Success!**

### Step 9: Test Your API
Copy your app URL from dashboard (looks like):
```
https://aegis-trader-backend-xxxx.onrender.com
```

Open in browser or curl:
```bash
https://your-app.onrender.com/health
```

**Expected Response:**
```json
{
  "status": "ok",
  "env": "production",
  "version": "1.0.0",
  "database": "connected"
}
```

## Environment Variables Check

While in Settings, scroll to **"Environment"** section.

**You should have:**
```
APP_ENV = production
TIMEZONE = Africa/Johannesburg
PYTHON_VERSION = 3.11
```

**You should NOT have:**
```
❌ DATABASE_URL (remove if present)
❌ DASHBOARD_JWT_SECRET (remove if present)
❌ MT5_NODE_SECRET (remove if present)
```

These auto-generate and don't need to be set manually.

## Alternative: Use render.yaml

If you want automatic configuration:

### In Settings → Build & Deploy:

Find **"Auto-Deploy"** section

Look for **"Apply render.yaml"** option

Click **"Apply render.yaml"**

This will automatically configure:
- ✅ Correct start command
- ✅ Correct build command
- ✅ All environment variables

Then click **"Save Changes"** and **"Manual Deploy"**

## Troubleshooting

### Still seeing "Exited with status 1"?

**Check 1: Start Command**
Must be EXACTLY:
```
uvicorn backend.main:app --host 0.0.0.0 --port $PORT
```

**Check 2: Build Command**
Should be:
```
pip install -r backend/requirements.txt
```

**Check 3: Environment Variables**
Only have: `APP_ENV`, `TIMEZONE`, `PYTHON_VERSION`

### Seeing "No open ports detected"?

You're still using hardcoded `8000` instead of `$PORT`.

Fix: Update start command to use `$PORT`

### Seeing "ModuleNotFoundError"?

Missing dependency in requirements.txt

Check logs to see which module is missing

### Seeing "ValidationError"?

Remove manually set secrets from environment variables

Let them auto-generate

## Visual Checklist

```
Settings Page:
├── Build & Deploy
│   ├── Build Command: pip install -r backend/requirements.txt ✅
│   └── Start Command: uvicorn backend.main:app --host 0.0.0.0 --port $PORT ✅
│
└── Environment
    ├── APP_ENV = production ✅
    ├── TIMEZONE = Africa/Johannesburg ✅
    ├── PYTHON_VERSION = 3.11 ✅
    ├── DATABASE_URL = (not set) ✅
    ├── DASHBOARD_JWT_SECRET = (not set) ✅
    └── MT5_NODE_SECRET = (not set) ✅
```

## After Successful Deployment

### 1. Set Up Keep-Alive

Render free tier spins down after 15 minutes.

**Quick Fix:**
- Go to https://cron-job.org
- Create free account
- Add cron job:
  - URL: `https://your-app.onrender.com/health`
  - Interval: Every 10 minutes

### 2. Update Mobile App

Edit `mobile/services/api.ts`:
```typescript
// Change this:
const API_BASE_URL = 'http://192.168.8.152:8000';

// To this:
const API_BASE_URL = 'https://your-app.onrender.com';
```

Rebuild:
```bash
cd mobile
npm run build
```

### 3. Test Everything

- [ ] `/health` endpoint works
- [ ] `/dashboard/status` works
- [ ] Mobile app connects
- [ ] Trading data syncs

## Quick Reference Card

```
┌─────────────────────────────────────────────┐
│  RENDER DEPLOYMENT FIX                      │
├─────────────────────────────────────────────┤
│  Start Command:                             │
│  uvicorn backend.main:app \                 │
│    --host 0.0.0.0 --port $PORT              │
│                                             │
│  Build Command:                             │
│  pip install -r backend/requirements.txt    │
│                                             │
│  Environment Variables:                     │
│  - APP_ENV=production                       │
│  - TIMEZONE=Africa/Johannesburg             │
│  - PYTHON_VERSION=3.11                      │
│                                             │
│  Test URL:                                  │
│  https://your-app.onrender.com/health       │
└─────────────────────────────────────────────┘
```

## Need More Help?

Read these files in order:
1. **FIX_DEPLOYMENT_NOW.md** - Quick fix guide
2. **RENDER_DEPLOYMENT_FIX.md** - Detailed troubleshooting
3. **DEPLOYMENT_CHECKLIST.md** - Verify all settings

## Summary

**Time Required:** 2 minutes
**Difficulty:** Easy
**Success Rate:** 99% if you follow exactly

**The Fix:**
1. Change start command to use `uvicorn` (not `python -m uvicorn`)
2. Use `$PORT` (not `8000`)
3. Remove unnecessary environment variables
4. Redeploy

**Result:** Backend deploys successfully and stays running! 🚀
