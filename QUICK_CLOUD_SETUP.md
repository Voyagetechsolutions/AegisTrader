# Quick Cloud Setup (5 Minutes)

## Option 1: Render.com (Recommended)

### 1. Go to Render
https://render.com

### 2. Click "New +" → "Web Service"

### 3. Connect GitHub
- Select your `AegisTrader` repo
- Click "Connect"

### 4. Configure Service
```
Name: aegis-trader-backend
Environment: Python 3
Build Command: pip install -r backend/requirements.txt
Start Command: python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
Plan: Free
```

### 5. Add Environment Variables
Click "Advanced" → "Add Environment Variable"

Add these:
- `DATABASE_URL` = `sqlite:///./aegis_trader.db`
- `APP_ENV` = `production`
- `TIMEZONE` = `Africa/Johannesburg`

### 6. Deploy
Click "Create Web Service"

**Wait 2-3 minutes...**

You'll get a URL like: `https://aegis-trader-backend.onrender.com`

### 7. Test It
Open in browser:
```
https://aegis-trader-backend.onrender.com/health
```

Should show:
```json
{"status":"ok","env":"production","version":"1.0.0"}
```

### 8. Update Mobile App
Edit `mobile/services/api.ts`:

Change:
```typescript
const API_BASE_URL = 'http://192.168.8.152:8000';
```

To:
```typescript
const API_BASE_URL = 'https://aegis-trader-backend.onrender.com';
```

### 9. Rebuild Mobile App
```bash
cd mobile
npm run build
```

---

## Option 2: Railway.app

### 1. Go to Railway
https://railway.app

### 2. Click "New Project"

### 3. Select "Deploy from GitHub repo"

### 4. Choose `AegisTrader` repo

### 5. Railway auto-configures
- Detects Python
- Reads Dockerfile
- Auto-deploys

### 6. Add Environment Variables
In Railway dashboard:
- `DATABASE_URL` = `sqlite:///./aegis_trader.db`
- `APP_ENV` = `production`
- `TIMEZONE` = `Africa/Johannesburg`

### 7. Get Your URL
Railway shows your URL in the dashboard

### 8. Update Mobile App
Same as Render - update `mobile/services/api.ts`

---

## Keep Backend Awake (Render Only)

Render spins down after 15 min inactivity. To prevent this:

### Option A: Use Cron Job
Create a free cron service at https://cron-job.org

Add job:
```
URL: https://aegis-trader-backend.onrender.com/health
Interval: Every 10 minutes
```

### Option B: Run Keep-Alive Script
On your local machine, run:
```bash
python keep_alive.py
```

This pings your backend every 10 minutes to keep it awake.

---

## Verify Everything Works

### 1. Test Backend Health
```bash
curl https://your-cloud-url.onrender.com/health
```

### 2. Test Dashboard
```bash
curl https://your-cloud-url.onrender.com/dashboard/status
```

### 3. Test Mobile App
- Update API URL in code
- Rebuild app
- Connect from mobile device
- Should see data from cloud backend

---

## Important Notes

### MT5 Connection
Your MT5 terminal must still run locally. The cloud backend connects to your local MT5 via heartbeat.

### Database
SQLite database is stored on the cloud. Data persists between deployments.

### Costs
- Render free tier: $0/month
- Railway free tier: $5/month credit (usually enough)
- Both are truly free for small projects

### Performance
- Free tier is slower than paid
- Acceptable for trading signals
- Not for high-frequency trading

---

## Troubleshooting

### Backend won't deploy
1. Check logs in dashboard
2. Verify `requirements.txt` exists
3. Check Python version (3.11+)

### Mobile app can't connect
1. Verify URL is correct
2. Check CORS in backend
3. Test URL in browser first

### Backend keeps spinning down (Render)
1. Set up keep-alive cron job
2. Or run keep_alive.py locally

---

## Next: Auto-Deploy on Push

Both Render and Railway auto-deploy when you push to GitHub!

Just push your changes:
```bash
git add .
git commit -m "Update backend"
git push
```

Your cloud backend updates automatically!

---

## Support

- Render docs: https://render.com/docs
- Railway docs: https://docs.railway.app
- FastAPI docs: https://fastapi.tiangolo.com

You're live on the cloud! 🚀
