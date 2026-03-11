# Fix Your Render Deployment NOW

Your code is pushed to GitHub with all fixes. Here's what to do next.

## The Problem

Your app was crashing with "Exited with status 1" because:
- Start command used `python -m uvicorn` instead of `uvicorn`
- Port was hardcoded to `8000` instead of using `$PORT`

## The Fix (2 Minutes)

### Step 1: Go to Render Dashboard
https://dashboard.render.com

### Step 2: Click Your Service
Find "aegis-trader-backend" (or whatever you named it)

### Step 3: Update Settings

Click "Settings" in the left sidebar

Scroll to "Build & Deploy" section

**Change Start Command to:**
```
uvicorn backend.main:app --host 0.0.0.0 --port $PORT
```

**CRITICAL**: 
- Remove `python -m` from the start
- Use `$PORT` not `8000`

Click "Save Changes"

### Step 4: Redeploy

Click "Manual Deploy" button (top right)

Select "Deploy latest commit"

Click "Deploy"

### Step 5: Watch Logs

Click "Logs" tab

Wait 2-3 minutes

You should see:
```
INFO:backend.main:Starting Aegis Trader backend [production]
INFO:backend.main:Database tables created/verified
INFO:backend.main:APScheduler started
INFO:uvicorn.error:Application startup complete.
```

### Step 6: Test

Open your app URL (shown in dashboard):
```
https://your-app.onrender.com/health
```

Should return:
```json
{"status":"ok","env":"production","version":"1.0.0"}
```

## ✓ Success!

Your backend is now live and working.

## Alternative: Use render.yaml

For automatic configuration:

1. In Render dashboard → Settings
2. Scroll to "Build & Deploy"
3. Click "Apply render.yaml"
4. Click "Save Changes"
5. Redeploy

The `render.yaml` file I created has all the correct settings.

## Still Having Issues?

### Check These:

**Environment Variables** (Settings → Environment):
- `APP_ENV` = `production` ✓
- `TIMEZONE` = `Africa/Johannesburg` ✓
- `PYTHON_VERSION` = `3.11` ✓

**Don't have these** (they auto-generate):
- ✗ DATABASE_URL
- ✗ DASHBOARD_JWT_SECRET
- ✗ MT5_NODE_SECRET

### Read the Logs

If you see errors in logs:

**"ModuleNotFoundError"**
- Missing dependency
- Check `backend/requirements.txt`

**"ValidationError"**
- Bad environment variable
- Remove weak secrets

**"No open ports detected"**
- Start command still wrong
- Must use `$PORT`

### Get Help

Read these files:
- `RENDER_DEPLOYMENT_FIX.md` - Detailed troubleshooting
- `DEPLOYMENT_CHECKLIST.md` - Verify all settings
- `DEPLOY_NOW.md` - Full deployment guide

## What Changed

I fixed these files:
1. `backend/config.py` - Better env var handling
2. `backend/main.py` - Improved error handling
3. `render.yaml` - Automatic configuration
4. `DEPLOY_NOW.md` - Updated instructions

All changes are pushed to GitHub.

## Next Steps

After deployment works:

1. **Set up keep-alive** (Render spins down after 15 min)
   - Go to https://cron-job.org
   - Ping your `/health` endpoint every 10 minutes

2. **Update mobile app**
   - Edit `mobile/services/api.ts`
   - Change URL to your Render URL
   - Rebuild app

3. **Test everything**
   - Mobile app connects
   - Trading data syncs
   - All features work

---

**Quick Fix:**
1. Render Dashboard → Your Service → Settings
2. Start Command: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
3. Save → Manual Deploy → Deploy latest commit
4. Wait 2 minutes → Test `/health` endpoint

Done! 🚀
