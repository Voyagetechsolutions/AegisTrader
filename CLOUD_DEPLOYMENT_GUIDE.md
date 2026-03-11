# Free Cloud Deployment Guide for Aegis Trader Backend

## Best Free Options for Your Backend

### 1. **Render.com** (RECOMMENDED - Best for FastAPI)
- **Free Tier**: 1 free web service, auto-deploys from GitHub
- **Specs**: 0.5 GB RAM, shared CPU
- **Perfect for**: Your FastAPI backend
- **Uptime**: Spins down after 15 min inactivity (acceptable for trading)

**Pros:**
- Direct GitHub integration
- Auto-deploys on push
- Easy environment variables
- Good for Python apps

**Cons:**
- Spins down after inactivity (need to wake it up)
- Limited resources

### 2. **Railway.app**
- **Free Tier**: $5/month credit (enough for small backend)
- **Specs**: Flexible, scales with usage
- **Perfect for**: Production-ready alternative

**Pros:**
- More generous free tier
- Better performance
- Doesn't spin down

**Cons:**
- Credit runs out eventually
- Requires payment method

### 3. **Heroku** (Legacy - No longer free)
- ❌ Removed free tier in November 2022
- Not recommended

### 4. **PythonAnywhere**
- **Free Tier**: Limited but works
- **Specs**: 512 MB RAM
- **Good for**: Simple backends

---

## Step-by-Step: Deploy to Render.com (Easiest)

### Prerequisites
1. GitHub account (already have it)
2. Render.com account (free)
3. Your code pushed to GitHub (done ✓)

### Step 1: Create Render Account
1. Go to https://render.com
2. Sign up with GitHub (easiest)
3. Authorize Render to access your repos

### Step 2: Create Web Service
1. Click "New +" → "Web Service"
2. Select your `AegisTrader` repository
3. Configure:
   - **Name**: `aegis-trader-backend`
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r backend/requirements.txt`
   - **Start Command**: `python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000`
   - **Plan**: Free

### Step 3: Set Environment Variables
In Render dashboard, go to Environment:
```
DATABASE_URL=sqlite:///./aegis_trader.db
APP_ENV=production
TIMEZONE=Africa/Johannesburg
```

### Step 4: Deploy
- Click "Create Web Service"
- Render auto-deploys from GitHub
- Takes 2-3 minutes
- You get a URL like: `https://aegis-trader-backend.onrender.com`

### Step 5: Update Mobile App
In `mobile/services/api.ts`, change:
```typescript
const API_BASE_URL = 'https://aegis-trader-backend.onrender.com';
```

---

## Step-by-Step: Deploy to Railway.app

### Step 1: Create Railway Account
1. Go to https://railway.app
2. Sign up with GitHub
3. Authorize Railway

### Step 2: Create New Project
1. Click "New Project"
2. Select "Deploy from GitHub repo"
3. Choose `AegisTrader`

### Step 3: Configure
1. Railway auto-detects Python
2. Set environment variables:
   - `DATABASE_URL`
   - `APP_ENV=production`
   - `TIMEZONE=Africa/Johannesburg`

### Step 4: Deploy
- Railway auto-deploys
- Get your URL from the dashboard
- Update mobile app with new URL

---

## Important Considerations for Your Backend

### MT5 Connection Issue
Your backend connects to MT5 via heartbeat. On cloud:
- MT5 must be running on your local machine
- Backend on cloud connects back to your local MT5
- This requires:
  1. Your local machine stays on
  2. MT5 terminal running 24/7
  3. Network connectivity maintained

**Solution**: Keep your local machine as MT5 bridge, cloud backend as API layer

### Database
- SQLite works on free tier
- Data persists between deployments
- Render/Railway provide persistent storage

### Keep-Alive (Render Only)
Render spins down after 15 min inactivity. To keep it alive:

Create `keep_alive.py`:
```python
import requests
import time
from datetime import datetime

BACKEND_URL = "https://aegis-trader-backend.onrender.com"

while True:
    try:
        response = requests.get(f"{BACKEND_URL}/health")
        print(f"[{datetime.now()}] Keep-alive ping: {response.status_code}")
    except Exception as e:
        print(f"[{datetime.now()}] Keep-alive failed: {e}")
    
    time.sleep(600)  # Ping every 10 minutes
```

Run this on your local machine to keep cloud backend awake.

---

## Deployment Checklist

- [ ] Create Render/Railway account
- [ ] Connect GitHub repository
- [ ] Set environment variables
- [ ] Deploy backend
- [ ] Test `/health` endpoint
- [ ] Update mobile app API URL
- [ ] Test mobile app connection
- [ ] Set up keep-alive (if using Render)
- [ ] Verify MT5 connection from cloud

---

## Testing Cloud Deployment

After deployment, test with:

```bash
# Replace with your cloud URL
curl https://aegis-trader-backend.onrender.com/health

# Should return:
# {"status":"ok","env":"production","version":"1.0.0"}
```

---

## Troubleshooting

### Backend won't start
- Check logs in Render/Railway dashboard
- Verify `requirements.txt` has all dependencies
- Check Python version compatibility

### Mobile app can't connect
- Verify cloud URL is correct
- Check CORS settings in `backend/main.py`
- Test URL in browser first

### MT5 connection fails
- Ensure local MT5 is running
- Check network connectivity
- Verify heartbeat endpoint works locally first

### Database errors
- Check file permissions
- Verify database path is writable
- Use persistent storage option

---

## Next Steps

1. **Choose platform**: Render (easiest) or Railway (better resources)
2. **Deploy**: Follow steps above
3. **Test**: Verify endpoints work
4. **Update mobile**: Point to cloud URL
5. **Monitor**: Check logs regularly

Your backend will be live on the cloud within 10 minutes!
