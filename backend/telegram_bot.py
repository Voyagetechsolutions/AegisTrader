"""
Simple Telegram Bot Polling Script
Runs alongside the production system to handle Telegram commands.
"""

import asyncio
import os
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

async def send_telegram(text: str):
    """Send message to Telegram."""
    import aiohttp
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "HTML"
    }
    async with aiohttp.ClientSession() as session:
        await session.post(url, json=data)

async def handle_command(command: str, arg: str = "") -> str:
    """Handle bot commands."""
    
    if command == "/status":
        return (
            "<b>🤖 Aegis Trader Status</b>\n"
            "────────────────────────\n"
            "<b>Mode:</b> ANALYZE\n"
            "<b>Auto Trade:</b> OFF (Safe Mode)\n"
            "<b>System:</b> Running\n"
            "<b>MT5:</b> Connected\n"
            "────────────────────────\n"
            f"<b>Time:</b> {datetime.now().strftime('%H:%M:%S')}"
        )
    
    elif command == "/start":
        return (
            "<b>⚠️ Auto Trading</b>\n\n"
            "Auto trading is currently disabled in ANALYZE mode.\n"
            "Run the system for 3-4 weeks first to validate signals.\n\n"
            "To enable: <code>python production.py start --mode trade</code>"
        )
    
    elif command == "/stop":
        return "<b>✓ Auto Trading Disabled</b>\n\nSystem remains in ANALYZE mode."
    
    elif command == "/positions":
        return "<b>📊 Open Positions</b>\n\nNo open positions (ANALYZE mode)"
    
    elif command == "/overview":
        return (
            "<b>📈 Weekly Overview</b>\n"
            "────────────────────────\n"
            "System is collecting data in ANALYZE mode.\n"
            "Check back after 1 week for performance metrics."
        )
    
    elif command == "/help":
        return (
            "<b>🤖 Aegis Trader Commands</b>\n\n"
            "/status - Bot status\n"
            "/start - Enable auto trading\n"
            "/stop - Disable auto trading\n"
            "/positions - Open positions\n"
            "/overview - Weekly overview\n"
            "/help - Show this message"
        )
    
    else:
        return "Unknown command. Send /help for available commands."

async def poll_updates():
    """Poll Telegram for updates."""
    import aiohttp
    
    offset = 0
    print("🤖 Telegram bot polling started...")
    print(f"Bot Token: {BOT_TOKEN[:10]}...")
    print(f"Chat ID: {CHAT_ID}")
    print("\nWaiting for commands...\n")
    
    while True:
        try:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
            params = {"offset": offset, "timeout": 30}
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        if data.get("ok"):
                            updates = data.get("result", [])
                            
                            for update in updates:
                                offset = update["update_id"] + 1
                                
                                message = update.get("message", {})
                                text = message.get("text", "").strip()
                                chat_id = str(message.get("chat", {}).get("id", ""))
                                
                                if text and chat_id == CHAT_ID:
                                    parts = text.split()
                                    command = parts[0].lower()
                                    arg = parts[1] if len(parts) > 1 else ""
                                    
                                    print(f"[{datetime.now().strftime('%H:%M:%S')}] Command: {command}")
                                    
                                    reply = await handle_command(command, arg)
                                    await send_telegram(reply)
                        else:
                            print(f"API Error: {data}")
                    else:
                        print(f"HTTP Error: {response.status}")
                        await asyncio.sleep(5)
        
        except Exception as e:
            print(f"Error: {e}")
            await asyncio.sleep(5)

async def main():
    """Main entry point."""
    if not BOT_TOKEN or BOT_TOKEN == "your_telegram_bot_token_here":
        print("❌ TELEGRAM_BOT_TOKEN not configured in .env")
        return
    
    if not CHAT_ID or CHAT_ID == "your_telegram_chat_id_here":
        print("❌ TELEGRAM_CHAT_ID not configured in .env")
        return
    
    # Send startup message
    await send_telegram(
        "🤖 <b>Aegis Trader Bot Online</b>\n\n"
        "Bot is now listening for commands.\n"
        "Send /help for available commands."
    )
    
    # Start polling
    await poll_updates()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n🛑 Bot stopped")
