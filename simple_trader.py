"""
Simple MT5 Trader - Direct Connection
Takes real trades based on simple momentum strategy
"""

import MetaTrader5 as mt5
import pandas as pd
import time
from datetime import datetime
import numpy as np

# Configuration
SYMBOL = "US30"  # Change to your broker's symbol name
LOT_SIZE = 0.01  # Small size for testing
MAGIC_NUMBER = 999888
TIMEFRAME = mt5.TIMEFRAME_M5

def connect_mt5():
    """Connect to MT5"""
    if not mt5.initialize():
        print("❌ MT5 initialization failed")
        print(f"Error: {mt5.last_error()}")
        return False
    
    print("✅ Connected to MT5")
    account_info = mt5.account_info()
    if account_info:
        print(f"Account: {account_info.login}")
        print(f"Balance: ${account_info.balance:.2f}")
        print(f"Equity: ${account_info.equity:.2f}")
    return True

def get_market_data(symbol, timeframe, bars=100):
    """Get OHLC data from MT5"""
    rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, bars)
    if rates is None:
        print(f"❌ Failed to get data for {symbol}")
        return None
    
    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    return df

def calculate_signals(df):
    """Simple momentum strategy"""
    # Calculate indicators
    df['ema_fast'] = df['close'].ewm(span=9).mean()
    df['ema_slow'] = df['close'].ewm(span=21).mean()
    df['rsi'] = calculate_rsi(df['close'], 14)
    
    # Get current values
    current = df.iloc[-1]
    prev = df.iloc[-2]
    
    # Buy signal: Fast EMA crosses above Slow EMA + RSI < 70
    buy_signal = (
        current['ema_fast'] > current['ema_slow'] and
        prev['ema_fast'] <= prev['ema_slow'] and
        current['rsi'] < 70
    )
    
    # Sell signal: Fast EMA crosses below Slow EMA + RSI > 30
    sell_signal = (
        current['ema_fast'] < current['ema_slow'] and
        prev['ema_fast'] >= prev['ema_slow'] and
        current['rsi'] > 30
    )
    
    return {
        'buy': buy_signal,
        'sell': sell_signal,
        'price': current['close'],
        'ema_fast': current['ema_fast'],
        'ema_slow': current['ema_slow'],
        'rsi': current['rsi']
    }

def calculate_rsi(prices, period=14):
    """Calculate RSI"""
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def get_open_positions(symbol):
    """Get open positions for symbol"""
    positions = mt5.positions_get(symbol=symbol)
    return positions if positions else []

def place_buy_order(symbol, lot_size, price, sl_points=50, tp_points=100):
    """Place buy order"""
    point = mt5.symbol_info(symbol).point
    
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": lot_size,
        "type": mt5.ORDER_TYPE_BUY,
        "price": price,
        "sl": price - sl_points * point,
        "tp": price + tp_points * point,
        "deviation": 20,
        "magic": MAGIC_NUMBER,
        "comment": "Simple Trader BUY",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }
    
    result = mt5.order_send(request)
    
    if result.retcode != mt5.TRADE_RETCODE_DONE:
        print(f"❌ Buy order failed: {result.retcode} - {result.comment}")
        return None
    
    print(f"✅ BUY order placed: Ticket #{result.order}")
    print(f"   Price: {price:.2f}")
    print(f"   SL: {request['sl']:.2f}")
    print(f"   TP: {request['tp']:.2f}")
    return result

def place_sell_order(symbol, lot_size, price, sl_points=50, tp_points=100):
    """Place sell order"""
    point = mt5.symbol_info(symbol).point
    
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": lot_size,
        "type": mt5.ORDER_TYPE_SELL,
        "price": price,
        "sl": price + sl_points * point,
        "tp": price - tp_points * point,
        "deviation": 20,
        "magic": MAGIC_NUMBER,
        "comment": "Simple Trader SELL",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }
    
    result = mt5.order_send(request)
    
    if result.retcode != mt5.TRADE_RETCODE_DONE:
        print(f"❌ Sell order failed: {result.retcode} - {result.comment}")
        return None
    
    print(f"✅ SELL order placed: Ticket #{result.order}")
    print(f"   Price: {price:.2f}")
    print(f"   SL: {request['sl']:.2f}")
    print(f"   TP: {request['tp']:.2f}")
    return result

def close_position(ticket):
    """Close position by ticket"""
    positions = mt5.positions_get(ticket=ticket)
    if not positions:
        return False
    
    position = positions[0]
    
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": position.symbol,
        "volume": position.volume,
        "type": mt5.ORDER_TYPE_SELL if position.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY,
        "position": ticket,
        "price": mt5.symbol_info_tick(position.symbol).bid if position.type == mt5.ORDER_TYPE_BUY else mt5.symbol_info_tick(position.symbol).ask,
        "deviation": 20,
        "magic": MAGIC_NUMBER,
        "comment": "Close by Simple Trader",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }
    
    result = mt5.order_send(request)
    return result.retcode == mt5.TRADE_RETCODE_DONE

def main():
    """Main trading loop"""
    print("=" * 60)
    print("SIMPLE MT5 TRADER - LIVE TRADING")
    print("=" * 60)
    
    # Connect to MT5
    if not connect_mt5():
        return
    
    # Check symbol exists
    symbol_info = mt5.symbol_info(SYMBOL)
    if symbol_info is None:
        print(f"❌ Symbol {SYMBOL} not found")
        print("Available symbols:")
        symbols = mt5.symbols_get()
        for s in symbols[:10]:
            print(f"  - {s.name}")
        mt5.shutdown()
        return
    
    # Enable symbol for trading
    if not symbol_info.visible:
        if not mt5.symbol_select(SYMBOL, True):
            print(f"❌ Failed to select {SYMBOL}")
            mt5.shutdown()
            return
    
    print(f"\n📊 Trading {SYMBOL}")
    print(f"💰 Lot Size: {LOT_SIZE}")
    print(f"🔢 Magic Number: {MAGIC_NUMBER}")
    print(f"\nPress Ctrl+C to stop\n")
    
    iteration = 0
    
    try:
        while True:
            iteration += 1
            print(f"\n{'='*60}")
            print(f"Iteration #{iteration} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"{'='*60}")
            
            # Get market data
            df = get_market_data(SYMBOL, TIMEFRAME)
            if df is None:
                time.sleep(10)
                continue
            
            # Calculate signals
            signals = calculate_signals(df)
            
            # Display current market state
            print(f"\n📈 Market Analysis:")
            print(f"   Price: {signals['price']:.2f}")
            print(f"   EMA Fast (9): {signals['ema_fast']:.2f}")
            print(f"   EMA Slow (21): {signals['ema_slow']:.2f}")
            print(f"   RSI (14): {signals['rsi']:.2f}")
            
            # Check for open positions
            positions = get_open_positions(SYMBOL)
            print(f"\n📊 Open Positions: {len(positions)}")
            
            for pos in positions:
                profit = pos.profit
                pos_type = "BUY" if pos.type == 0 else "SELL"
                print(f"   Ticket #{pos.ticket}: {pos_type} {pos.volume} lots")
                print(f"   Entry: {pos.price_open:.2f} | Current: {pos.price_current:.2f}")
                print(f"   Profit: ${profit:.2f}")
            
            # Trading logic
            if len(positions) == 0:  # No open positions
                if signals['buy']:
                    print(f"\n🟢 BUY SIGNAL DETECTED!")
                    place_buy_order(SYMBOL, LOT_SIZE, signals['price'])
                
                elif signals['sell']:
                    print(f"\n🔴 SELL SIGNAL DETECTED!")
                    place_sell_order(SYMBOL, LOT_SIZE, signals['price'])
                
                else:
                    print(f"\n⏸️  No signal - waiting...")
            
            else:
                print(f"\n⏳ Position open - monitoring...")
            
            # Wait before next iteration
            print(f"\n⏰ Next check in 30 seconds...")
            time.sleep(30)
    
    except KeyboardInterrupt:
        print("\n\n🛑 Stopping trader...")
    
    finally:
        # Show final stats
        print("\n" + "="*60)
        print("FINAL STATISTICS")
        print("="*60)
        
        account_info = mt5.account_info()
        if account_info:
            print(f"Balance: ${account_info.balance:.2f}")
            print(f"Equity: ${account_info.equity:.2f}")
            print(f"Profit: ${account_info.profit:.2f}")
        
        positions = get_open_positions(SYMBOL)
        print(f"\nOpen Positions: {len(positions)}")
        
        mt5.shutdown()
        print("\n✅ Disconnected from MT5")

if __name__ == "__main__":
    main()
