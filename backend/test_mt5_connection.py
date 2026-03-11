"""Quick MT5 connection test script"""
import MetaTrader5 as mt5  # type: ignore

print("=" * 60)
print("MT5 CONNECTION TEST")
print("=" * 60)

# Try to initialize MT5
if mt5.initialize():
    print("✓ MT5 connected successfully!")
    
    # Get terminal info
    terminal = mt5.terminal_info()
    if terminal:
        print(f"\nTerminal Info:")
        print(f"  Path: {terminal.path}")
        print(f"  Build: {terminal.build}")
        print(f"  Connected: {terminal.connected}")
    
    # Get account info
    account = mt5.account_info()
    if account:
        print(f"\nAccount Info:")
        print(f"  Login: {account.login}")
        print(f"  Server: {account.server}")
        print(f"  Balance: ${account.balance:.2f}")
    
    # Test fetching US30 data
    print(f"\nTesting US30 data fetch...")
    rates = mt5.copy_rates_from_pos("US30", mt5.TIMEFRAME_M1, 0, 10)
    
    if rates is not None and len(rates) > 0:
        print(f"✓ Fetched {len(rates)} candles")
        print(f"  Latest close: {rates[-1]['close']}")
    else:
        error = mt5.last_error()
        print(f"✗ Failed to fetch data: {error}")
        print(f"\nTrying alternative symbol names...")
        
        # Try alternative names
        for symbol in ["US30", "US30.cash", "US30Cash", "USTEC", "DJ30"]:
            rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M1, 0, 1)
            if rates is not None and len(rates) > 0:
                print(f"  ✓ Found working symbol: {symbol}")
                break
            else:
                print(f"  ✗ {symbol} - not available")
    
    mt5.shutdown()
    print("\n" + "=" * 60)
    print("MT5 SHUTDOWN COMPLETE")
    print("=" * 60)
    
else:
    error = mt5.last_error()
    print(f"✗ MT5 initialization failed!")
    print(f"  Error: {error}")
    print(f"\nPossible causes:")
    print(f"  1. MetaTrader 5 is not running")
    print(f"  2. MetaTrader 5 is not installed")
    print(f"  3. MT5 terminal is not logged in")
    print(f"  4. Algorithmic trading is disabled in MT5")
    print(f"\nSolutions:")
    print(f"  1. Open MetaTrader 5 terminal")
    print(f"  2. Login to your trading account")
    print(f"  3. Go to Tools → Options → Expert Advisors")
    print(f"  4. Enable 'Allow algorithmic trading'")
    print(f"  5. Enable 'Allow DLL imports'")
