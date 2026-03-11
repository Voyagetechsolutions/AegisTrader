# BATCH 3: Integration & Orchestration

Audit the following integration points:

1. `backend/main.py` or `backend/production.py` (scheduler/orchestrator)
2. `backend/routers/webhook.py` (TradingView webhook handler)
3. `backend/routers/telegram.py` (Telegram bot commands)
4. `backend/routers/dashboard.py` (dashboard API)
5. End-to-end signal flow

---

## Required Output Format

```
SEVERITY: [CRITICAL / MAJOR / MINOR]
FILE: backend/[exact_path]
LOCATION: [function/class name]
ISSUE: [exact problem]
PRD_VIOLATION: [which section]
PRODUCTION_IMPACT: [what breaks]
FIX: [exact fix needed]
```

---

## Scheduler/Orchestrator Checks

**Continuous Loop:**
- ✓ Runs every ~60 seconds
- ✓ Fetches market data from MT5
- ✓ Builds candles (1M, 5M, 15M, 1H, 4H, Daily, Weekly)
- ✓ Runs strategy engine
- ✓ Processes signals
- ✓ Monitors open positions
- ✓ Handles errors without crashing
- ✓ Logs each iteration

**Startup:**
- ✓ Connects to MT5
- ✓ Connects to database
- ✓ Syncs existing positions
- ✓ Loads risk state
- ✓ Validates configuration

---

## Webhook Handler Checks

**TradingView Webhook:**
- ✓ Validates webhook secret
- ✓ Parses JSON payload
- ✓ Extracts signal data
- ✓ Runs strategy engine
- ✓ Runs risk checks
- ✓ Routes to execution or alerts
- ✓ Returns 200 OK
- ✓ Handles duplicate signals

---

## Telegram Bot Checks

**Commands:**
- ✓ /status - shows bot mode, balance, limits
- ✓ /start - enables auto trading
- ✓ /stop - disables auto trading
- ✓ /mode analyze|trade|swing
- ✓ /positions - lists open trades
- ✓ /closeall - closes all positions
- ✓ /overview - weekly report

**Authentication:**
- ✓ Validates TELEGRAM_CHAT_ID
- ✓ Rejects unauthorized users

---

## End-to-End Flow

**Signal → Execution:**
1. ✓ TradingView sends webhook
2. ✓ Backend validates secret
3. ✓ Strategy engine analyzes
4. ✓ Confluence scoring grades signal
5. ✓ Risk engine checks limits
6. ✓ Trade manager executes (if A+ and auto-trade enabled)
7. ✓ Alert manager sends Telegram notification
8. ✓ Database records signal and trade

**Position Monitoring:**
1. ✓ Scheduler checks positions every iteration
2. ✓ Detects TP1/TP2/SL hits
3. ✓ Executes partial closes
4. ✓ Modifies SL to breakeven
5. ✓ Sends alerts
6. ✓ Updates database

---

Run audit. Give exact findings only.
