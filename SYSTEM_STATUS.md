# AEGIS TRADER - SYSTEM STATUS

**Last Updated:** 2024  
**Status:** ✅ PRODUCTION READY (with configuration)

---

## Quick Start

### 1. Generate Secrets
```bash
python generate_secrets.py
```

### 2. Configure Environment
```bash
cp .env.example .env
# Edit .env and paste the generated secrets
# Add your Telegram bot token and chat ID
```

### 3. Run Backend
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### 4. Verify System
- Open http://localhost:8000/docs
- Check http://localhost:8000/health
- Test Telegram bot with `/status` command

---

## System Health

### ✅ Security
- [x] No hardcoded credentials
- [x] Required secrets with validation
- [x] Log injection protection
- [x] Telegram chat validation
- [x] Thread-safe operations

### ✅ Core Functionality
- [x] TradingView webhook handler
- [x] Signal processing pipeline
- [x] Trade execution via MT5 bridge
- [x] Trade lifecycle management (TP1/TP2/runner)
- [x] Telegram bot commands
- [x] Dashboard API endpoints
- [x] Risk engine with kill switch
- [x] News filter with blackout windows
- [x] Session filter (London/NY/Power Hour)
- [x] Spread filter with adaptive limits

### ✅ Scheduled Jobs
- [x] Weekly report (Sunday 07:00 SAST)
- [x] News sync (Daily 00:01 SAST)
- [x] Position monitoring (Every 60 seconds)

### ✅ Timezone Correctness
- [x] UTC internal storage
- [x] SAST conversion for display
- [x] Session windows correct
- [x] News blackout timing correct
- [x] Daily risk reset timing correct

---

## Architecture Overview

```
┌─────────────────┐
│  TradingView    │
│  (Pine Script)  │
└────────┬────────┘
         │ Webhook
         ▼
┌─────────────────────────────────────────┐
│         FastAPI Backend (Render)        │
│  ┌───────────────────────────────────┐  │
│  │  Signal Engine                    │  │
│  │  • Idempotency check              │  │
│  │  • Session filter                 │  │
│  │  • Spread filter                  │  │
│  │  • News filter                    │  │
│  │  • Confluence scoring             │  │
│  │  • Risk engine                    │  │
│  └───────────────────────────────────┘  │
│  ┌───────────────────────────────────┐  │
│  │  Trade Manager                    │  │
│  │  • Lot size calculation           │  │
│  │  • MT5 bridge integration         │  │
│  │  • TP1/TP2/Runner management      │  │
│  │  • State machine                  │  │
│  └───────────────────────────────────┘  │
│  ┌───────────────────────────────────┐  │
│  │  Alert Manager                    │  │
│  │  • Telegram notifications         │  │
│  │  • Signal alerts                  │  │
│  │  • Trade alerts                   │  │
│  │  • Risk alerts                    │  │
│  └───────────────────────────────────┘  │
└─────────────────────────────────────────┘
         │                    │
         │                    │
         ▼                    ▼
┌─────────────────┐  ┌─────────────────┐
│  MT5 Terminal   │  │  Telegram Bot   │
│  (Expert Advisor)│  │  (Commands)     │
└─────────────────┘  └─────────────────┘
```

---

## Configuration Reference

### Required Environment Variables

| Variable | Description | Min Length | Example |
|----------|-------------|------------|---------|
| `WEBHOOK_SECRET` | TradingView webhook auth | 16 chars | `abc123...` |
| `DASHBOARD_JWT_SECRET` | JWT signing key | 32 chars | `xyz789...` |
| `MT5_NODE_SECRET` | MT5 bridge auth | 16 chars | `def456...` |
| `TELEGRAM_BOT_TOKEN` | Bot token from @BotFather | - | `123456:ABC...` |
| `TELEGRAM_CHAT_ID` | Your Telegram chat ID | - | `123456789` |

### Optional Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_ENV` | `development` | Environment mode |
| `DATABASE_URL` | SQLite | PostgreSQL connection string |
| `MT5_NODE_URL` | `http://localhost:8001` | MT5 bridge URL |
| `NEWS_FILTER_BYPASS` | `false` | Disable news filter (testing) |
| `MAX_DAILY_TRADES` | `2` | Max trades per day |
| `MAX_DAILY_LOSSES` | `2` | Max losses per day |
| `MAX_DAILY_DRAWDOWN_PCT` | `2.0` | Max daily drawdown % |
| `MAX_SPREAD_POINTS` | `5.0` | Max spread in points |
| `TIMEZONE` | `Africa/Johannesburg` | Session timezone |

---

## Bot Modes

### ANALYZE Mode (Recommended for first 3-4 weeks)
- Receives signals from TradingView
- Scores and grades setups
- Sends Telegram alerts
- **Does NOT execute trades**
- Tracks paper trade results
- Validates strategy performance

**Use this mode to:**
- Verify signal quality
- Test news filter effectiveness
- Validate session timing
- Check spread filtering
- Review confluence scoring

### TRADE Mode (After successful paper trading)
- All ANALYZE mode features
- **Automatically executes A+ grade signals**
- Respects risk limits (2 trades, 2 losses, 2% drawdown)
- Manages positions (TP1/TP2/runner)
- Kill switch on risk limit breach

**Requirements before enabling:**
- 3-4 weeks successful paper trading
- Win rate > 50%
- Positive expectancy
- Risk limits tested
- News filter validated

### SWING Mode
- Receives signals
- Sends alerts for manual review
- **Never auto-executes**
- User must manually approve trades
- Good for high-timeframe setups

---

## Telegram Commands

| Command | Description |
|---------|-------------|
| `/status` | Show bot mode, balance, risk limits |
| `/start` | Enable auto trading (TRADE mode only) |
| `/stop` | Disable auto trading |
| `/mode analyze` | Switch to analyze mode |
| `/mode trade` | Switch to trade mode |
| `/mode swing` | Switch to swing mode |
| `/positions` | List open MT5 positions |
| `/closeall` | Emergency close all positions |
| `/overview` | Generate weekly market overview |

---

## Risk Management

### Daily Limits (Per Spec)
- **Max 2 trades per day** - Prevents overtrading
- **Max 2 losses per day** - Kill switch protection
- **Max 2% daily drawdown** - Account protection
- **Max 5 points spread** - Execution quality
- **Max 10 points slippage** - Fill quality

### Kill Switch Triggers
1. 2 losses in same day → Auto trading disabled
2. Daily drawdown ≥ 2% → Auto trading disabled
3. Manual `/stop` command → Auto trading disabled

**When kill switch activates:**
- Auto trading stops immediately
- Telegram alert sent
- Existing positions remain open
- Signal alerts continue
- Resets at midnight SAST

---

## Session Windows (SAST)

| Session | Time | Characteristics |
|---------|------|-----------------|
| London | 10:00 - 13:00 | High volatility, liquidity sweeps |
| New York | 15:30 - 17:30 | Trend continuation, strong moves |
| Power Hour | 20:00 - 22:00 | Late session reversals |

**Outside sessions:**
- Signals are scored and logged
- Alerts are sent
- Trades are NOT executed (even in TRADE mode)

---

## News Blackout

### Standard Events (15 min before/after)
- Retail Sales
- Jobless Claims
- PMI Data
- Consumer Confidence

### Major Events (30 min before/after)
- CPI (Consumer Price Index)
- NFP (Non-Farm Payrolls)
- FOMC (Federal Reserve meetings)
- Interest Rate Decisions
- GDP Reports

**During blackout:**
- Auto trading paused
- Signals still scored
- Alerts still sent
- Resumes automatically after blackout

---

## Trade Management

### Position Sizing
Three modes available:

1. **Minimum Lot** - Always use broker minimum (0.01)
2. **Fixed Lot** - Use configured lot size (e.g., 0.05)
3. **Risk Percent** - Calculate based on account % risk
   - Formula: `lots = (account × risk%) / (SL_points × 100)`
   - Example: $1000 account, 1% risk, 50 point SL = 0.02 lots

### Take Profit Management
- **TP1 (50%)** - Close half position, move SL to break even
- **TP2 (40%)** - Close 40% more, leave runner
- **Runner (10%)** - Trail with 5M structure breaks

---

## Monitoring & Alerts

### Telegram Notifications
- ✅ Signal detected (A/A+ grades)
- ⚡ Trade executed
- 🎯 TP1 hit (50% closed, BE active)
- 🎯🎯 TP2 hit (40% closed, runner active)
- ✅/❌ Trade closed (with P&L)
- 🚨 Risk limit reached
- ⚠️ Spread too wide
- 📰 News blackout active
- 📊 Weekly overview (Sunday 07:00)

### Dashboard Monitoring
- Real-time bot status
- Open positions
- Recent signals
- Recent trades
- Performance metrics
- Risk limit status
- Connection health

---

## Troubleshooting

### System won't start
```
Error: webhook_secret field required
```
**Fix:** Create `.env` file with required secrets (run `python generate_secrets.py`)

### Telegram alerts not working
```
Warning: Telegram not configured - skipping alert
```
**Fix:** Add `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` to `.env`

### Webhook returns 401
```
Invalid webhook secret
```
**Fix:** Ensure TradingView alert uses same secret as `WEBHOOK_SECRET` in `.env`

### Trades not executing
**Check:**
1. Bot mode is TRADE (not ANALYZE)
2. Auto trading enabled (`/start` command)
3. Within session window
4. No news blackout active
5. Risk limits not hit
6. Signal grade is A+ (not A or B)

### Position monitoring not working
**Check:**
1. Scheduler is running (check logs for "position_monitor")
2. MT5 bridge is connected
3. `monitor_positions()` function exists in trade_manager.py

---

## Production Deployment

### Pre-Deployment Checklist
- [ ] Generate strong secrets
- [ ] Configure PostgreSQL database
- [ ] Set `APP_ENV=production`
- [ ] Configure Telegram bot
- [ ] Test webhook endpoint
- [ ] Verify MT5 connection
- [ ] Enable HTTPS
- [ ] Set up monitoring
- [ ] Configure backups
- [ ] Test kill switch
- [ ] Run in ANALYZE mode for 3-4 weeks

### Render Deployment
1. Push to GitHub
2. Connect Render to repository
3. Add environment variables in Render dashboard
4. Deploy from `render.yaml`
5. Verify health endpoint
6. Test webhook with TradingView

### Monitoring Setup
- CloudWatch / Datadog for logs
- Uptime monitoring (e.g., UptimeRobot)
- Error tracking (e.g., Sentry)
- Performance monitoring
- Database backups (daily)

---

## Support & Documentation

### Files
- `README.md` - Project overview
- `AUDIT_BATCH_3_RESULTS.md` - Security audit results
- `FIXES_APPLIED.md` - Detailed fix documentation
- `.env.example` - Configuration template
- `generate_secrets.py` - Secret generator

### Logs
- Application logs: Check console output
- Scheduler logs: Look for job execution messages
- Error logs: Check for ERROR/WARNING level messages

### Testing
```bash
# Run tests
cd backend
pytest tests/ -v

# Test webhook
curl -X POST http://localhost:8000/webhooks/tradingview \
  -H "Content-Type: application/json" \
  -d '{"secret":"your_secret","symbol":"US30","direction":"long",...}'

# Test health
curl http://localhost:8000/health
```

---

## Next Steps

1. **Generate secrets** - Run `python generate_secrets.py`
2. **Configure .env** - Copy secrets and add Telegram credentials
3. **Start backend** - `uvicorn backend.main:app --reload`
4. **Test system** - Verify health endpoint and Telegram commands
5. **Paper trade** - Run in ANALYZE mode for 3-4 weeks
6. **Review results** - Check win rate, expectancy, drawdown
7. **Go live** - Switch to TRADE mode if results are positive

---

**Remember:** This system enforces discipline. It removes emotion. It filters bad setups. That's the real edge.

Good luck! 🚀
