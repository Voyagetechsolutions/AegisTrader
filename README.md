# Aegis Trader

**Automated trading assistant and execution engine for US30 (Dow Jones CFD)**

---

## System Overview

```
Strategy Engine → Render Backend (FastAPI) → Telegram Bot
                          ↑ ↓
                MQL5 Expert Advisor (EA)
                          ↓
                MetaTrader 5 Terminal
```

| Component | Location | Purpose |
|---|---|---|
| `backend/` | Render (cloud) | Signal processing, risk, alerts |
| `mql5/` | MT5 Terminal | Execution bridge (Expert Advisor) |
| `dashboard/` | Static web | Mobile-first control panel |
| `database/` | PostgreSQL/Supabase | All persistent data |

---

## Quick Start

### 1. Clone & configure

```bash
cp .env.example .env
# Fill in all values in .env
```

### 2. Run locally (Docker)

```bash
docker-compose up
```

Backend available at `http://localhost:8000/docs`

### 3. Run backend manually

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### 4. Install MT5 Bridge (Expert Advisor)

1. Open MetaTrader 5
2. Go to **File** → **Open Data Folder**
3. Copy `mql5/AegisTradeBridge.mq5` to `MQL5/Experts/`
4. Compile the EA in MetaEditor
5. Attach the EA to a chart and configure the `BackendURL` (e.g., `http://localhost:8000/mt5/poll`) and `ApiSecret`.

### 5. Open Dashboard

Open `dashboard/index.html` in a mobile browser.
Edit `dashboard/js/api.js` and set `API_BASE` to your Render URL.

---

## Environment Variables (`.env`)

| Variable | Description |
|---|---|
| `DATABASE_URL` | PostgreSQL connection string (asyncpg) |
| `TELEGRAM_BOT_TOKEN` | Bot token from @BotFather |
| `TELEGRAM_CHAT_ID` | Your Telegram chat/group ID |
| `MT5_NODE_URL` | URL of the Windows VPS MT5 node |
| `MT5_NODE_SECRET` | Shared secret for MT5 node auth |
| `NEWS_FILTER_BYPASS` | Set `true` to skip news filter (testing) |
| `TIMEZONE` | `Africa/Johannesburg` (SAST) |

---

## Telegram Bot Commands

| Command | Action |
|---|---|
| `/status` | Bot mode, auto trade status, balance |
| `/start` | Enable auto trading |
| `/stop` | Disable auto trading |
| `/mode analyze` | Switch to analyze mode (no trades) |
| `/mode trade` | Switch to trade mode (auto execute) |
| `/mode swing` | Switch to swing mode (alerts only) |
| `/positions` | List open MT5 positions |
| `/closeall` | Close all open positions |
| `/overview` | Generate weekly market overview |

---

## Scoring System

| Factor | Max Score |
|---|---|
| HTF Alignment | 20 |
| 250-Point Level | 15 |
| 125-Point Level | 10 |
| Liquidity Sweep | 15 |
| FVG Retest | 15 |
| Displacement Candle | 10 |
| Market Structure Shift | 10 |
| Session Timing | 5 |
| Spread Acceptable | 5 |

**Grades:** A+ (≥85) → auto trade · A (75–84) → alert only · B (<75) → ignored

---

## Session Windows (SAST)

| Session | Time |
|---|---|
| London | 10:00 – 13:00 |
| New York | 15:30 – 17:30 |
| Power Hour | 20:00 – 22:00 |

---

## Risk Rules

- Max **2 trades** per day
- Max **2 losses** per day  
- Max **2% daily drawdown**
- Max spread: **5 points** hard cap (also adaptive: ≤ avg×2)
- Max slippage: **10 points**
- News blackout: 15 min before/after (30 min for CPI/NFP/FOMC)

If any limit is hit → auto trading disabled, alerts continue.

---

## Trade Management

| Stage | Action |
|---|---|
| TP1 | Close 50%, move SL to Break Even |
| TP2 | Close 40% |
| Runner | Hold remaining 10% with trailing stop |

---

## Deploy to Render

1. Push repo to GitHub
2. Connect to [Render](https://render.com) → New Web Service
3. Render reads `render.yaml` automatically
4. Add all environment variables in the Render dashboard
5. The backend starts at your `*.onrender.com` URL

---

## Run Tests

```bash
cd backend
pip install pytest pytest-asyncio pytz
pytest tests/ -v
```

---

## Project Structure

```
Aegis Trader/
├── backend/
│   ├── main.py              # FastAPI app entry
│   ├── config.py            # Settings
│   ├── database.py          # Async SQLAlchemy
│   ├── models/              # ORM models
│   ├── schemas/             # Pydantic schemas
│   ├── modules/             # Business logic
│   │   ├── signal_engine.py
│   │   ├── confluence_scoring.py
│   │   ├── session_filter.py
│   │   ├── spread_filter.py
│   │   ├── news_filter.py
│   │   ├── trade_manager.py
│   │   ├── alert_manager.py
│   │   ├── risk_engine.py
│   │   └── analytics_engine.py
│   ├── routers/             # API endpoints
│   │   ├── webhook.py       # /execution/callback
│   │   ├── telegram.py      # /telegram/webhook
│   │   ├── dashboard.py     # /dashboard/*
│   │   └── mt5_bridge.py    # MT5 HTTP client
│   ├── services/
│   │   └── weekly_report.py
│   └── tests/
├── mql5/                    # MQL5 Execution Bridge
│   └── AegisTradeBridge.mq5
├── dashboard/               # Mobile web app
│   ├── index.html
│   ├── css/style.css
│   └── js/
│       ├── api.js
│       └── app.js
├── database/
│   └── schema.sql
├── docker-compose.yml
├── render.yaml
└── .env.example
```

---

> **Remember:** This system enforces discipline. It removes emotion. It filters bad setups.  
> That's the real edge.
