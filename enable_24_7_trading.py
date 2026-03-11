"""
Enable 24/7 trading by enabling session override.
This allows the bot to trade at any time, not just during London, NY, and Power Hour sessions.
"""

from backend.strategy.session_manager import session_manager

# Enable session override
session_manager.enable_override()

print("✓ Session override ENABLED")
print("✓ Bot will now trade 24/7")
print("✓ Sessions (London, NY, Power Hour) are still tracked but won't block trades")
print()
print("To disable 24/7 trading, run: session_manager.disable_override()")
