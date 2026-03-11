# Render Deployment Fix Guide

Your app is crashing on Render with "Exited with status 1". Here's how to fix it.

## The Problem

Looking at your logs:
```
==> Running 'python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000'
==> Exited with status 1
```

The app crashes immediately after starting. Common causes:
1. Wrong start command (should use `$PORT` not `8000`)
2. Missing Python path setup
3. Environment variable issues

## The Solution

### Option 1: Use render.yaml (Recommended)

I've created a `render.yaml` file in your project root. This tells Render exactly how to deploy.

1. Commit and push the new `render.yaml`:
```bash
git add render.yaml
git commit -m "Add Render configuration"
git push
```

2. In Render dashboard:
   - Go to your service
   - Click "Settings"
   - Scroll to "Build & Deploy"
   - Click "Apply render.yaml"

3. Redeploy:
   - Click "Manual Deploy" → "Deploy latest commit"

### Option 2: Fix Settings Manually

If you prefer manual configuration:

1. Go to your Render service dashboard
2. Click "Settings"
3. Update these fields:

**Build Command:**
```
pip install -r backend/requirements.txt
```

**Start Command:**
```
uvicorn backend.main:app --host 0.0.0.0 --port $PORT
```

**CRITICAL**: Use `$PORT` not `8000`! Render assigns the port dynamically.

4. Environment Variables:
   - `APP_ENV` = `production`
   - `TIMEZONE` = `Africa/Johannesburg`
   - `PYTHON_VERSION` = `3.11`

5. Click "Save Changes"
6. Click "Manual Deploy" → "Deploy latest commit"

## Verification

After redeployment, check the logs. You should see:

```
INFO:backend.main:Starting Aegis Trader backend [production]
INFO:backend.main:Database tables created/verified
INFO:backend.main:APScheduler started
INFO:uvicorn.error:Application startup complete.
```

Then test your URL:
```
https://your-app.onrender.com/health
```

Should return:
```json
{
  "status": "ok",
  "env": "production",
  "version": "1.0.0",
  "database": "connected"
}
```

## Still Not Working?

### Check Logs

In Render dashboard → Logs, look for:

**Import Errors:**
```
ModuleNotFoundError: No module named 'xxx'
```
Fix: Add missing package to `backend/requirements.txt`

**Config Errors:**
```
ValidationError: xxx
```
Fix: Check environment variables are set correctly

**Database Errors:**
```
sqlalchemy.exc.xxx
```
Fix: Ensure DATABASE_URL is not set (we use SQLite by default)

### Run Diagnostic Locally

Test if your app can start:
```bash
python -m backend.check_startup
```

Should show all checks passing.

### Common Issues

**Issue: "No module named 'backend'"**
- Fix: Start command should be `uvicorn backend.main:app` not `python -m uvicorn`

**Issue: "Port already in use"**
- Fix: Use `$PORT` in start command, not hardcoded `8000`

**Issue: "Database connection failed"**
- Fix: Don't set DATABASE_URL env var - SQLite is used by default

**Issue: "Validation error for secrets"**
- Fix: Don't set DASHBOARD_JWT_SECRET or MT5_NODE_SECRET - they auto-generate

## Alternative: Try Railway

If Render continues to have issues, Railway is easier:

1. Go to https://railway.app
2. Click "New Project" → "Deploy from GitHub"
3. Select your repo
4. Railway auto-configures everything
5. Add environment variables:
   - `APP_ENV` = `production`
   - `TIMEZONE` = `Africa/Johannesburg`

Railway is more forgiving with Python apps.

## Next Steps

Once deployed successfully:

1. Test all endpoints:
   - `/health` - Should return 200 OK
   - `/dashboard/status` - Should return system status
   - `/docs` - Should be disabled in production

2. Update mobile app with your cloud URL

3. Set up keep-alive (Render spins down after 15 min):
   - Use cron-job.org to ping `/health` every 10 minutes

## Support

If you're still stuck:
1. Share the full deployment logs
2. Run `python -m backend.check_startup` and share output
3. Check Render's troubleshooting guide: https://render.com/docs/troubleshooting-deploys

---

**Quick Fix Summary:**
1. Use `uvicorn backend.main:app --host 0.0.0.0 --port $PORT` as start command
2. Set `APP_ENV=production` and `TIMEZONE=Africa/Johannesburg`
3. Don't set DATABASE_URL (SQLite is default)
4. Redeploy and check logs
