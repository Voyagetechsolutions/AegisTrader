# Deployment Checklist ✓

Use this to verify your deployment is configured correctly.

## Pre-Deployment Checks

- [ ] `backend/requirements.txt` exists and is complete
- [ ] `render.yaml` exists in project root
- [ ] All code is committed to GitHub
- [ ] Local startup test passes: `python -m backend.check_startup`

## Render Configuration

### Build Settings
- [ ] Build Command: `pip install -r backend/requirements.txt`
- [ ] Start Command: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
- [ ] **CRITICAL**: Start command uses `$PORT` not `8000`
- [ ] **CRITICAL**: Start command is `uvicorn` not `python -m uvicorn`

### Environment Variables
- [ ] `APP_ENV` = `production`
- [ ] `TIMEZONE` = `Africa/Johannesburg`
- [ ] `PYTHON_VERSION` = `3.11`
- [ ] **DO NOT SET**: `DATABASE_URL` (SQLite is default)
- [ ] **DO NOT SET**: `DASHBOARD_JWT_SECRET` (auto-generated)
- [ ] **DO NOT SET**: `MT5_NODE_SECRET` (auto-generated)

### Optional (if using Telegram)
- [ ] `TELEGRAM_BOT_TOKEN` = your bot token
- [ ] `TELEGRAM_CHAT_ID` = your chat ID

## Deployment Logs Check

After deploying, check logs for these success indicators:

### ✓ Good Signs
```
==> Build successful 🎉
INFO:backend.main:Starting Aegis Trader backend [production]
INFO:backend.main:Database tables created/verified
INFO:backend.main:APScheduler started
INFO:uvicorn.error:Application startup complete.
INFO:uvicorn.error:Uvicorn running on http://0.0.0.0:XXXXX
```

### ✗ Bad Signs

**"Exited with status 1"**
- Problem: App crashed during startup
- Fix: Check start command uses `$PORT` and `uvicorn` (not `python -m uvicorn`)

**"No module named 'xxx'"**
- Problem: Missing dependency
- Fix: Add to `backend/requirements.txt` and redeploy

**"ValidationError"**
- Problem: Config validation failed
- Fix: Check environment variables, don't set weak secrets

**"No open ports detected"**
- Problem: App not binding to port
- Fix: Use `$PORT` in start command

## Post-Deployment Tests

### Test 1: Health Check
```bash
curl https://your-app.onrender.com/health
```

Expected:
```json
{
  "status": "ok",
  "env": "production",
  "version": "1.0.0",
  "database": "connected"
}
```

### Test 2: Root Endpoint
```bash
curl https://your-app.onrender.com/
```

Expected:
```json
{
  "message": "Aegis Trader API is running",
  "version": "1.0.0",
  "docs": "disabled in production",
  "health": "/health"
}
```

### Test 3: Dashboard Status
```bash
curl https://your-app.onrender.com/dashboard/status
```

Should return system status (may require auth).

## Common Issues & Fixes

| Issue | Cause | Fix |
|-------|-------|-----|
| Exit status 1 | Wrong start command | Use `uvicorn backend.main:app --host 0.0.0.0 --port $PORT` |
| No ports detected | Hardcoded port | Use `$PORT` not `8000` |
| Module not found | Missing dependency | Add to requirements.txt |
| Validation error | Bad env vars | Remove weak secrets, let them auto-generate |
| Database error | Wrong DB URL | Don't set DATABASE_URL for SQLite |

## Keep-Alive Setup (Render Only)

Render free tier spins down after 15 minutes of inactivity.

### Option A: Cron-Job.org (Recommended)
1. Go to https://cron-job.org
2. Create free account
3. Add cron job:
   - URL: `https://your-app.onrender.com/health`
   - Schedule: Every 10 minutes
4. Save

### Option B: Local Script
Run on your computer:
```bash
python keep_alive.py
```

## Mobile App Update

After successful deployment:

1. Edit `mobile/services/api.ts`:
```typescript
const API_BASE_URL = 'https://your-app.onrender.com';
```

2. Rebuild mobile app:
```bash
cd mobile
npm run build
```

3. Test connection in mobile app

## Troubleshooting

If deployment fails:

1. **Check logs** in Render dashboard
2. **Run diagnostic**: `python -m backend.check_startup`
3. **Verify settings** against this checklist
4. **Read**: `RENDER_DEPLOYMENT_FIX.md` for detailed fixes

## Success Criteria

Your deployment is successful when:

- [ ] Build completes without errors
- [ ] App starts and stays running
- [ ] `/health` endpoint returns 200 OK
- [ ] Logs show "Application startup complete"
- [ ] No "Exited with status 1" errors
- [ ] Mobile app can connect to cloud backend

## Next Steps

After successful deployment:

1. Set up keep-alive (if using Render)
2. Update mobile app with cloud URL
3. Test all features end-to-end
4. Monitor logs for any issues
5. Set up alerts (optional)

---

**Quick Reference:**

Start Command: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`

Environment Variables: `APP_ENV=production`, `TIMEZONE=Africa/Johannesburg`

Health Check: `https://your-app.onrender.com/health`
