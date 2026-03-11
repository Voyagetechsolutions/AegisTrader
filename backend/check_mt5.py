"""
Pre-flight check for MT5 connection before starting production.
Run this before starting the production system.
"""
try:
    import MetaTrader5 as mt5  # type: ignore
except ImportError:
    print("ERROR: MetaTrader5 package not installed")
    print("Install with: pip install MetaTrader5")
    import sys
    sys.exit(1)

import sys

def check_mt5():
    print("=" * 60)
    print("MT5 PRE-FLIGHT CHECK")
    print("=" * 60)
    
    # 1. Check if MT5 can initialize
    print("\n[1/5] Checking MT5 initialization...")
    if not mt5.initialize():
        error = mt5.last_error()
        print(f"  ✗ FAILED: {error}")
        print("\n  Solutions:")
        print("  1. Open MetaTrader 5 terminal")
        print("  2. Login to your trading account")
        print("  3. Keep MT5 running in the background")
        return False
    print("  ✓ MT5 initialized")
    
    # 2. Check terminal info
    print("\n[2/5] Checking terminal connection...")
    terminal = mt5.terminal_info()
    if not terminal:
        print("  ✗ FAILED: Cannot get terminal info")
        mt5.shutdown()
        return False
    print(f"  ✓ Terminal connected")
    print(f"    Build: {terminal.build}")
    print(f"    Connected: {terminal.connected}")
    
    # 3. Check account
    print("\n[3/5] Checking account...")
    account = mt5.account_info()
    if not account:
        print("  ✗ FAILED: Not logged in to any account")
        print("\n  Solutions:")
        print("  1. Login to your MT5 account")
        print("  2. Make sure account credentials are correct")
        mt5.shutdown()
        return False
    print(f"  ✓ Account logged in")
    print(f"    Login: {account.login}")
    print(f"    Server: {account.server}")
    print(f"    Balance: ${account.balance:.2f}")
    
    # 4. Check algorithmic trading
    print("\n[4/5] Checking algorithmic trading settings...")
    if not terminal.trade_allowed:
        print("  ✗ WARNING: Trading not allowed")
        print("\n  Solutions:")
        print("  1. Go to Tools → Options → Expert Advisors")
        print("  2. Enable 'Allow algorithmic trading'")
        print("  3. Enable 'Allow DLL imports'")
    else:
        print("  ✓ Algorithmic trading enabled")
    
    # 5. Check US30 symbol
    print("\n[5/5] Checking US30 symbol...")
    for symbol_name in ["US30", "US30.cash", "US30Cash", "DJ30", "USTEC"]:
        symbol_info = mt5.symbol_info(symbol_name)
        if symbol_info:
            if not symbol_info.visible:
                if mt5.symbol_select(symbol_name, True):
                    print(f"  ✓ Symbol found: {symbol_name} (added to Market Watch)")
                else:
                    print(f"  ⚠ Symbol found: {symbol_name} (but couldn't add to Market Watch)")
            else:
                print(f"  ✓ Symbol found: {symbol_name}")
            
            # Test data fetch
            rates = mt5.copy_rates_from_pos(symbol_name, mt5.TIMEFRAME_M1, 0, 1)
            if rates is not None and len(rates) > 0:
                print(f"    Latest price: {rates[0]['close']:.2f}")
                print(f"    Spread: {symbol_info.spread} points")
                
                mt5.shutdown()
                print("\n" + "=" * 60)
                print("✓ ALL CHECKS PASSED")
                print("=" * 60)
                print(f"\nMT5 is ready! Use symbol: {symbol_name}")
                print("You can now start the production system.")
                return True
            else:
                print(f"  ⚠ Symbol {symbol_name} found but no data available")
    
    print("  ✗ FAILED: US30 symbol not found or no data")
    print("\n  Solutions:")
    print("  1. Check if your broker offers US30 (Dow Jones)")
    print("  2. Try alternative names: US30.cash, DJ30, USTEC")
    print("  3. Add the symbol to Market Watch manually")
    
    mt5.shutdown()
    return False

if __name__ == "__main__":
    success = check_mt5()
    sys.exit(0 if success else 1)
