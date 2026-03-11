# Deploy Your Backend to Cloud NOW ✓

Your backend is ready to deploy. I've fixed the deployment issues.

---

## � What Was Fixed

Your deployment was failing because:
1. Wrong start command (used `python -m uvicorn` instead of `uvicorn`)
2. Hardcoded port `8000` instead of dynamic `$PORT`
3. Config validation issues in cloud environment

**All fixed!** ✓

---

## 🚀 OPTION 1: Render.com (Easiest - 5 Minutes)

### Quick Deploy with render.yaml

I've created a `render.yaml` file that configures everything automatically.

**Step 1: Push to GitHub**
```bash
git add .
git commit -m "Fix Render deployment configuration"
git push
```

**Step 2: Deploy on Render**
- Go to https://render.com/dashboard
- Click your service (or create new one)
- If existing: Settings → "Apply render.yaml" → Save
- Click "Manual Deploy" → "Deploy latest commit"

**Step 3: Wait 2-3 minutes**

**Step 4: Test**
```
https://your-app.onrender.com/health
```

Should return:
```json
{"status":"ok","env":"production","version":"1.0.0"}
```

✓ **Done!**

### Manual Configuration (Alternative)

If you prefer manual setup:

**Service Settings:**
```
Name: aegis-trader-backend
Environment: Python 3
Build Command: pip install -r backend/requirements.txt
Start Command: uvicorn backend.main:app --host 0.0.0.0 --port $PORT
Plan: Free
```

**CRITICAL**: Use `$PORT` not `8000`!

**Environment Variables:**
```
APP_ENV = production
TIMEZONE = Africa/Johannesburg
PYTHON_VERSION = 3.11
```

**Don't set DATABASE_URL** - SQLite is used by default.

---

## 🚀 OPTION 2: Railway.app (Better Performance)

### Step 1: Create Account
- Go to https://railway.app
- Click "Login with GitHub"
- Authorize Railway

### Step 2: Create Project
- Click "New Project"
- Select "Deploy from GitHub repo"
- Choose `AegisTrader`
- Click "Deploy"

### Step 3: Wait for Auto-Deploy
Railway auto-configures everything using your Dockerfile

**Wait 2-3 minutes...**

### Step 4: Add Environment Variables
In Railway dashboard:
- Click "Variables"
- Add these 3:
```
DATABASE_URL = sqlite:///./aegis_trader.db
APP_ENV = production
TIMEZONE = Africa/Johannesburg
```

### Step 5: Get Your URL
Railway shows your URL in the dashboard

### Step 6: Test
```
https://your-railway-url.railway.app/health
```

✓ **Your backend is live!**

---

## 📱 Update Mobile App

After deployment, update your mobile app to use the cloud backend.

### Edit File: `mobile/services/api.ts`

Find this line:
```typescript
const API_BASE_URL = 'http://192.168.8.152:8000';
```

Replace with your cloud URL:
```typescript
const API_BASE_URL = 'https://aegis-trader-backend.onrender.com';
// OR
const API_BASE_URL = 'https://your-railway-url.railway.app';
```

### Rebuild Mobile App
```bash
cd mobile
npm run build
```

### Test Connection
- Open mobile app
- Should connect to cloud backend
- Should see trading data

✓ **Mobile app is now using cloud backend!**

---

## 🔄 Keep Backend Awake (Render Only)

Render spins down after 15 minutes of inactivity. To prevent this:

### Option A: Cron Job (Easiest)
1. Go to https://cron-job.org
2. Create free account
3. Add new cron job:
   - URL: `https://aegis-trader-backend.onrender.com/health`
   - Interval: Every 10 minutes
4. Save

✓ **Backend stays awake 24/7**

### Option B: Keep-Alive Script
Run on your local machine:
```bash
python keep_alive.py
```

This pings your backend every 10 minutes.

---

## ✅ Verification Checklist

After deployment, verify everything works:

- [ ] Backend URL works in browser
- [ ] `/health` endpoint returns 200 OK
- [ ] `/dashboard/status` endpoint works
- [ ] Mobile app connects to cloud backend
- [ ] Mobile app shows trading data
- [ ] MT5 connection works (if needed)
- [ ] Keep-alive is running (Render only)

---

## 🎯 What's Next

### Auto-Deploy on Push
Both platforms auto-deploy when you push to GitHub!

```bash
# Make changes locally
git add .
git commit -m "Update backend"
git push
```

Your cloud backend updates automatically!

### Monitor Logs
- **Render**: Dashboard → Logs
- **Railway**: Dashboard → Logs

Check logs regularly to catch issues early.

### Scale Up (Later)
When you need more resources:
- Render: Upgrade to paid plan
- Railway: Add more credits

---

## 💰 Costs

| Platform | Free Tier | Cost |
|----------|-----------|------|
| Render | 1 web service | $0/month |
| Railway | $5/month credit | $0-5/month |
| Both | Enough for small projects | Very affordable |

---

## 🆘 Troubleshooting

### Backend won't deploy
1. Check logs in dashboard
2. Verify `requirements.txt` exists
3. Check Python version (3.11+)
4. Ensure no syntax errors in code

### Mobile app can't connect
1. Verify cloud URL is correct
2. Test URL in browser first
3. Check CORS settings in backend
4. Verify network connectivity

### Backend keeps spinning down (Render)
1. Set up cron job keep-alive
2. Or run keep_alive.py locally
3. Check logs for errors

### MT5 connection fails
1. Ensure local MT5 is running
2. Check network connectivity
3. Verify heartbeat endpoint works locally first

---

## 📚 Documentation

- **CLOUD_DEPLOYMENT_GUIDE.md** - Comprehensive guide
- **QUICK_CLOUD_SETUP.md** - Detailed setup steps
- **CLOUD_READY.md** - Architecture overview
- **BACKEND_RESTART_GUIDE.md** - Local backend management

---

## 🎉 You're Ready!

Your backend is cloud-ready. Choose Render or Railway and deploy now!

**Estimated time: 5-10 minutes**

After deployment:
1. Your backend is live on the internet
2. Mobile app connects from anywhere
3. MT5 trades execute from cloud
4. Data syncs in real-time

Let's go! 🚀

---

## Support

- Render: https://render.com/docs
- Railway: https://docs.railway.app
- FastAPI: https://fastapi.tiangolo.com
- GitHub: https://github.com/Voyagetechsolutions/AegisTrader

Questions? Check the documentation files or GitHub issues.
