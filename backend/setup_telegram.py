"""
Telegram Bot Setup & Test Script

This script helps you:
1. Get your Telegram Bot Token from @BotFather
2. Get your Chat ID
3. Test the bot connection
4. Set up the webhook (optional)
"""

import asyncio
import os
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

async def test_telegram_bot():
    """Test Telegram bot connection and send a test message."""
    
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    
    print("=" * 60)
    print("TELEGRAM BOT SETUP & TEST")
    print("=" * 60)
    
    # Step 1: Check if bot token exists
    print("\n[1/4] Checking Bot Token...")
    if not bot_token or bot_token == "your_telegram_bot_token_here":
        print("  ✗ Bot token not configured")
        print("\n  Setup Instructions:")
        print("  1. Open Telegram and search for @BotFather")
        print("  2. Send /newbot and follow instructions")
        print("  3. Copy the bot token")
        print("  4. Add to .env: TELEGRAM_BOT_TOKEN=your_token_here")
        return False
    print(f"  ✓ Bot token found: {bot_token[:10]}...")
    
    # Step 2: Check if chat ID exists
    print("\n[2/4] Checking Chat ID...")
    if not chat_id or chat_id == "your_telegram_chat_id_here":
        print("  ✗ Chat ID not configured")
        print("\n  Setup Instructions:")
        print("  1. Start a chat with your bot in Telegram")
        print("  2. Send any message to the bot")
        print("  3. Visit: https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates")
        print("  4. Find 'chat':{'id': YOUR_CHAT_ID}")
        print("  5. Add to .env: TELEGRAM_CHAT_ID=your_chat_id")
        return False
    print(f"  ✓ Chat ID found: {chat_id}")
    
    # Step 3: Test bot connection
    print("\n[3/4] Testing Bot Connection...")
    try:
        import aiohttp
        
        url = f"https://api.telegram.org/bot{bot_token}/getMe"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("ok"):
                        bot_info = data.get("result", {})
                        print(f"  ✓ Bot connected: @{bot_info.get('username')}")
                        print(f"    Name: {bot_info.get('first_name')}")
                    else:
                        print(f"  ✗ Bot API error: {data}")
                        return False
                else:
                    print(f"  ✗ HTTP error: {response.status}")
                    return False
    except Exception as e:
        print(f"  ✗ Connection failed: {e}")
        return False
    
    # Step 4: Send test message
    print("\n[4/4] Sending Test Message...")
    try:
        from modules.alert_manager import send_message
        
        test_msg = (
            "🤖 <b>Aegis Trader Bot Connected!</b>\n\n"
            "Your bot is ready to send alerts.\n\n"
            "<b>Available Commands:</b>\n"
            "/status - Check bot status\n"
            "/start - Enable auto trading\n"
            "/stop - Disable auto trading\n"
            "/positions - View open positions\n"
            "/overview - Weekly market overview"
        )
        
        await send_message(test_msg, chat_id=chat_id)
        print("  ✓ Test message sent!")
        print("\n  Check your Telegram app for the message.")
        
    except Exception as e:
        print(f"  ✗ Failed to send message: {e}")
        return False
    
    print("\n" + "=" * 60)
    print("✓ TELEGRAM BOT SETUP COMPLETE")
    print("=" * 60)
    print("\nYour bot is ready to use!")
    print("Try sending /status to your bot in Telegram.")
    
    return True


async def get_chat_id_helper():
    """Helper to get chat ID from recent messages."""
    from dotenv import load_dotenv
    load_dotenv()
    
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    
    if not bot_token or bot_token == "your_telegram_bot_token_here":
        print("Please set TELEGRAM_BOT_TOKEN in .env first")
        return
    
    print("\n" + "=" * 60)
    print("CHAT ID FINDER")
    print("=" * 60)
    print("\n1. Send a message to your bot in Telegram")
    print("2. Press Enter here to fetch your Chat ID")
    input("\nPress Enter when ready...")
    
    try:
        import aiohttp
        
        url = f"https://api.telegram.org/bot{bot_token}/getUpdates"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("ok"):
                        updates = data.get("result", [])
                        if updates:
                            for update in updates[-3:]:  # Show last 3
                                msg = update.get("message", {})
                                chat = msg.get("chat", {})
                                chat_id = chat.get("id")
                                username = chat.get("username", "N/A")
                                text = msg.get("text", "")
                                
                                print(f"\n  Chat ID: {chat_id}")
                                print(f"  Username: @{username}")
                                print(f"  Message: {text}")
                            
                            print(f"\n✓ Add this to your .env:")
                            print(f"  TELEGRAM_CHAT_ID={chat_id}")
                        else:
                            print("\n✗ No messages found. Send a message to your bot first.")
                    else:
                        print(f"✗ API error: {data}")
                else:
                    print(f"✗ HTTP error: {response.status}")
    except Exception as e:
        print(f"✗ Error: {e}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Telegram Bot Setup")
    parser.add_argument("--get-chat-id", action="store_true", help="Get your chat ID")
    args = parser.parse_args()
    
    if args.get_chat_id:
        asyncio.run(get_chat_id_helper())
    else:
        asyncio.run(test_telegram_bot())
