# Telegram Bot Setup Guide

## Step 1: Create Your Bot

1. Open Telegram and search for **@BotFather**
2. Send `/newbot`
3. Choose a name (e.g., "Aegis Trader Bot")
4. Choose a username (e.g., "aegis_trader_bot")
5. Copy the **bot token** (looks like: `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)

## Step 2: Get Your Chat ID

### Option A: Using the setup script
```bash
python setup_telegram.py --get-chat-id
```

### Option B: Manual method
1. Start a chat with your bot in Telegram
2. Send any message (e.g., "hello")
3. Visit this URL in your browser (replace YOUR_BOT_TOKEN):
   ```
   https://api.telegram.org/botYOUR_BOT_TOKEN/getUpdates
   ```
4. Look for `"chat":{"id":123456789}` - that's your Chat ID

## Step 3: Configure .env

Edit your `.env` file:

```bash
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_CHAT_ID=123456789
```

## Step 4: Test the Bot

```bash
python setup_telegram.py
```

You should receive a test message in Telegram!

## Step 5: Try Commands

In Telegram, send these commands to your bot:

- `/status` - Check bot status
- `/start` - Enable auto trading
- `/stop` - Disable auto trading
- `/positions` - View open positions
- `/overview` - Weekly market overview

## Troubleshooting

**Bot not responding?**
- Make sure you've started a chat with the bot first
- Check that bot token is correct
- Verify chat ID is correct

**"Unauthorized" error?**
- Bot token is invalid
- Create a new bot with @BotFather

**No messages received?**
- Check TELEGRAM_CHAT_ID is correct
- Make sure you've sent at least one message to the bot
