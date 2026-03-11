# Cloud Deployment Ready ✓

Your Aegis Trader backend is now ready for cloud deployment!

## What's Included

### Configuration Files
- ✓ `Dockerfile` - Container configuration
- ✓ `render.yaml` - Render.com deployment config
- ✓ `railway.json` - Railway.app deployment config
- ✓ `.dockerignore` - Exclude unnecessary files

### Documentation
- ✓ `CLOUD_DEPLOYMENT_GUIDE.md` - Comprehensive guide
- ✓ `QUICK_CLOUD_SETUP.md` - 5-minute setup
- ✓ `BACKEND_RESTART_GUIDE.md` - Local backend management

### Scripts
- ✓ `keep_alive.py` - Keep Render backend awake
- ✓ `check_backend_status.py` - Test backend connectivity

---

## Quick Start (Choose One)

### Render.com (Easiest - Recommended)
1. Go to https://render.com
2. Sign up with GitHub
3. Click "New Web Service"
4. Select your AegisTrader repo
5. Use build command: `pip install -r backend/requirements.txt`
6. Use start command: `python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000`
7. Add environment variables (see QUICK_CLOUD_SETUP.md)
8. Deploy!

**Result**: Your backend is live in 2-3 minutes

### Railway.app (Better Resources)
1. Go to https://railway.app
2. Sign up with GitHub
3. Click "New Project"
4. Select "Deploy from GitHub repo"
5. Choose AegisTrader
6. Railway auto-configures everything
7. Add environment variables
8. Deploy!

**Result**: Your backend is live with better performance

---

## After Deployment

### 1. Test Backend
```bash
curl https://your-backend-url.onrender.com/health
```

### 2. Update Mobile App
Edit `mobile/services/api.ts`:
```typescript
const API_BASE_URL = 'https://your-backend-url.onrender.com';
```

### 3. Rebuild Mobile App
```bash
cd mobile
npm run build
```

### 4. Keep Backend Awake (Render Only)
Run on your local machine:
```bash
python keep_alive.py
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    CLOUD DEPLOYMENT                     │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌──────────────────────────────────────────────────┐  │
│  │  Render.com / Railway.app (Cloud Backend)        │  │
│  │  - FastAPI Server                                │  │
│  │  - SQLite Database                               │  │
│  │  - REST API Endpoints                            │  │
│  │  - URL: https://aegis-trader-backend.onrender.com│  │
│  └──────────────────────────────────────────────────┘  │
│                         ↑                               │
│                         │ HTTPS                         │
│                         │                               │
│  ┌──────────────────────────────────────────────────┐  │
│  │  Mobile App (Any Device)                         │  │
│  │  - React Native / Expo                           │  │
│  │  - Connects to cloud backend                     │  │
│  │  - Real-time trading signals                     │  │
│  └──────────────────────────────────────────────────┘  │
│                                                         │
└─────────────────────────────────────────────────────────┘
                         ↑
                         │ Heartbeat
                         │
┌─────────────────────────────────────────────────────────┐
│                   LOCAL MACHINE                         │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌──────────────────────────────────────────────────┐  │
│  │  MT5 Terminal (Local)                            │  │
│  │  - AegisTradeBridge EA                           │  │
│  │  - Sends heartbeat to cloud backend              │  │
│  │  - Executes trades                               │  │
│  │  - Manages positions                             │  │
│  └──────────────────────────────────────────────────┘  │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## Important Notes

### MT5 Connection
- MT5 terminal must run on your local machine
- Cloud backend connects to local MT5 via heartbeat
- Your local machine must stay online
- Network connectivity must be maintained

### Database
- SQLite database stored on cloud
- Data persists between deployments
- Automatic backups recommended

### Costs
- **Render**: $0/month (free tier)
- **Railway**: $5/month credit (usually enough)
- Both are truly free for small projects

### Performance
- Free tier is slower than paid
- Acceptable for trading signals
- Not for high-frequency trading

### Auto-Deploy
Both platforms auto-deploy when you push to GitHub:
```bash
git add .
git commit -m "Update backend"
git push
```

Your cloud backend updates automatically!

---

## Troubleshooting

### Backend won't start
- Check logs in platform dashboard
- Verify requirements.txt exists
- Check Python version (3.11+)

### Mobile app can't connect
- Verify cloud URL is correct
- Check CORS settings
- Test URL in browser first

### MT5 connection fails
- Ensure local MT5 is running
- Check network connectivity
- Verify heartbeat endpoint works

### Backend keeps spinning down (Render)
- Set up keep-alive cron job
- Or run keep_alive.py locally

---

## Next Steps

1. **Choose platform**: Render (easiest) or Railway (better)
2. **Deploy**: Follow QUICK_CLOUD_SETUP.md
3. **Test**: Verify endpoints work
4. **Update mobile**: Point to cloud URL
5. **Monitor**: Check logs regularly

Your backend will be live on the cloud within 10 minutes!

---

## Support

- Render docs: https://render.com/docs
- Railway docs: https://docs.railway.app
- FastAPI docs: https://fastapi.tiangolo.com
- GitHub: https://github.com/Voyagetechsolutions/AegisTrader

You're ready to go live! 🚀
