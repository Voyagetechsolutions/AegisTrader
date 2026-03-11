"""
Complete Trading System Runner - FIXED (No Unicode Emojis)
Connects backend + dual-engine strategies + MT5 + mobile app
"""

import asyncio
import MetaTrader5 as mt5
from datetime import datetime
import logging
import sys

# Setup logging with UTF-8 encoding to handle any remaining unicode
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('trading_system.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

# Import backend components
from backend.strategy.dual_engine_models import Instrument, OHLCVBar, Direction
from backend.strategy.multi_market_coordinator import MultiMarketCoordinator, MultiMarketConfig
from backend.strategy.session_manager import SessionManager
from backend.database import AsyncSessionLocal

class LiveMT5Trader:
    """
    Complete trading system that:
    1. Connects to MT5 directly
    2. Uses dual-engine strategies
    3. Takes real trades
    4. Provides data to mobile app via backend
    """
    
    def __init__(self):
        self.running = False
        self.session_manager = SessionManager()
        self.coordinator = MultiMarketCoordinator(
            config=MultiMarketConfig(),
            session_manager=self.session_manager,
            news_filter=None
        )
        
        # Trading settings
        self.enabled_instruments = [
            Instrument.US30,
            Instrument.NAS100,
            Instrument.XAUUSD
        ]
        self.lot_size = 0.01
        self.magic_number = 202600
        
        # Statistics
        self.signals_generated = 0
        self.trades_executed = 0
        self.iteration_count = 0
    
    async def connect_mt5(self):
        """Connect to MT5"""
        logger.info("Connecting to MT5...")
        
        if not mt5.initialize():
            logger.error(f"MT5 initialization failed: {mt5.last_error()}")
            return False
        
        account_info = mt5.account_info()
        if account_info is None:
            logger.error("Failed to get account info")
            return False
        
        logger.info(f"[OK] Connected to MT5")
        logger.info(f"Account: {account_info.login}")
        logger.info(f"Balance: ${account_info.balance:.2f}")
        logger.info(f"Server: {account_info.server}")
        
        return True
    
    def get_mt5_symbol_name(self, instrument: Instrument) -> str:
        """Map our instrument enum to MT5 symbol name"""
        # Try common variations
        base_name = instrument.value
        variations = [
            base_name,
            f"{base_name}Cash",
            f"{base_name}.cash",
            f"{base_name}_",
        ]
        
        for symbol in variations:
            if mt5.symbol_info(symbol) is not None:
                return symbol
        
        # If not found, return base name and let it fail with helpful error
        return base_name
    
    async def fetch_market_data(self, instrument: Instrument) -> tuple[list[OHLCVBar], float]:
        """Fetch OHLCV data from MT5"""
        symbol = self.get_mt5_symbol_name(instrument)
        
        # Get 300 bars of M5 data
        rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M5, 0, 300)
        
        if rates is None or len(rates) == 0:
            logger.warning(f"No data for {symbol}")
            return [], 999.0
        
        # Convert to OHLCVBar objects
        bars = []
        for rate in rates:
            bar = OHLCVBar(
                timestamp=datetime.fromtimestamp(rate['time']),
                open=float(rate['open']),
                high=float(rate['high']),
                low=float(rate['low']),
                close=float(rate['close']),
                volume=int(rate['tick_volume'])
            )
            bars.append(bar)
        
        # Get current spread
        tick = mt5.symbol_info_tick(symbol)
        spread = (tick.ask - tick.bid) if tick else 999.0
        
        logger.debug(f"Fetched {len(bars)} bars for {symbol}, spread: {spread:.2f}")
        
        return bars, spread
    
    async def execute_trade(self, signal):
        """Execute trade via MT5"""
        symbol = self.get_mt5_symbol_name(signal.instrument)
        
        logger.info(f"[TRADE] Executing: {signal.engine.value} - {symbol} {signal.direction.value}")
        
        # Prepare order request
        point = mt5.symbol_info(symbol).point
        
        if signal.direction == Direction.LONG:
            order_type = mt5.ORDER_TYPE_BUY
            price = mt5.symbol_info_tick(symbol).ask
        else:
            order_type = mt5.ORDER_TYPE_SELL
            price = mt5.symbol_info_tick(symbol).bid
        
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": self.lot_size,
            "type": order_type,
            "price": price,
            "sl": signal.stop_loss,
            "tp": signal.tp1,
            "deviation": 20,
            "magic": self.magic_number,
            "comment": f"{signal.engine.value}_{signal.signal_id[:8]}",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        
        # Send order
        result = mt5.order_send(request)
        
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            logger.error(f"[FAIL] Trade failed: {result.retcode} - {result.comment}")
            return False
        
        logger.info(f"[SUCCESS] Trade executed: Ticket #{result.order}")
        logger.info(f"   Entry: {price:.2f}")
        logger.info(f"   SL: {signal.stop_loss:.2f}")
        logger.info(f"   TP: {signal.tp1:.2f}")
        
        self.trades_executed += 1
        return True
    
    async def run_iteration(self):
        """Run one trading iteration"""
        self.iteration_count += 1
        
        logger.info(f"\n{'='*70}")
        logger.info(f"ITERATION #{self.iteration_count} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"{'='*70}")
        
        # Fetch market data for all instruments
        market_data = {}
        
        for instrument in self.enabled_instruments:
            try:
                bars, spread = await self.fetch_market_data(instrument)
                
                if len(bars) >= 250:  # Minimum for regime detection
                    market_data[instrument] = (bars, spread)
                    logger.info(f"[OK] {instrument.value}: {len(bars)} bars, spread: {spread:.2f}")
                else:
                    logger.warning(f"[WARN] {instrument.value}: Insufficient data ({len(bars)} bars)")
            
            except Exception as e:
                logger.error(f"Error fetching {instrument.value}: {e}")
        
        if not market_data:
            logger.warning("No market data available")
            return
        
        # Process all markets through dual-engine coordinator
        logger.info(f"\n[ANALYZE] Processing {len(market_data)} markets...")
        
        signals = await self.coordinator.process_all_markets(market_data)
        
        # Handle generated signals
        for instrument, signal in signals.items():
            if signal:
                self.signals_generated += 1
                
                logger.info(f"\n[SIGNAL] New signal generated:")
                logger.info(f"   Engine: {signal.engine.value}")
                logger.info(f"   Instrument: {signal.instrument.value}")
                logger.info(f"   Direction: {signal.direction.value}")
                logger.info(f"   Entry: {signal.entry_price:.2f}")
                logger.info(f"   SL: {signal.stop_loss:.2f}")
                logger.info(f"   TP1: {signal.tp1:.2f}")
                logger.info(f"   R:R: {signal.get_risk_reward_ratio():.2f}")
                logger.info(f"   Status: {signal.status.value}")
                
                # Execute if approved
                if signal.status.value == "APPROVED":
                    await self.execute_trade(signal)
                else:
                    logger.info(f"   [SKIP] Signal not approved - skipping execution")
        
        # Show statistics
        logger.info(f"\n[STATS] Statistics:")
        logger.info(f"   Iterations: {self.iteration_count}")
        logger.info(f"   Signals Generated: {self.signals_generated}")
        logger.info(f"   Trades Executed: {self.trades_executed}")
        
        # Show account status
        account_info = mt5.account_info()
        if account_info:
            logger.info(f"\n[ACCOUNT] Account status:")
            logger.info(f"   Balance: ${account_info.balance:.2f}")
            logger.info(f"   Equity: ${account_info.equity:.2f}")
            logger.info(f"   Profit: ${account_info.profit:.2f}")
        
        # Show open positions
        positions = mt5.positions_get()
        if positions:
            logger.info(f"\n[POSITIONS] Open: {len(positions)}")
            for pos in positions:
                logger.info(f"   #{pos.ticket}: {pos.type_str} {pos.volume} {pos.symbol}")
                logger.info(f"      Entry: {pos.price_open:.2f} | Current: {pos.price_current:.2f}")
                logger.info(f"      Profit: ${pos.profit:.2f}")
    
    async def start(self):
        """Start the trading system"""
        logger.info("\n" + "="*70)
        logger.info("DUAL-ENGINE TRADING SYSTEM - STARTING")
        logger.info("="*70)
        
        # Connect to MT5
        if not await self.connect_mt5():
            logger.error("Failed to connect to MT5")
            return
        
        # Verify symbols exist
        logger.info("\n[VERIFY] Checking symbols...")
        for instrument in self.enabled_instruments:
            symbol = self.get_mt5_symbol_name(instrument)
            symbol_info = mt5.symbol_info(symbol)
            
            if symbol_info is None:
                logger.error(f"[ERROR] Symbol not found: {symbol}")
                logger.info("Available symbols:")
                symbols = mt5.symbols_get()
                for s in symbols[:20]:
                    if any(x in s.name.upper() for x in ['US30', 'NAS', 'GOLD', 'XAU']):
                        logger.info(f"   - {s.name}")
                return
            
            logger.info(f"[OK] {symbol} - {symbol_info.description}")
        
        logger.info(f"\n[START] Starting trading loop...")
        logger.info(f"   Instruments: {[i.value for i in self.enabled_instruments]}")
        logger.info(f"   Lot Size: {self.lot_size}")
        logger.info(f"   Check Interval: 60 seconds")
        logger.info(f"\nPress Ctrl+C to stop\n")
        
        self.running = True
        
        try:
            while self.running:
                try:
                    await self.run_iteration()
                    
                    # Wait 60 seconds before next iteration
                    logger.info(f"\n[WAIT] Next iteration in 60 seconds...")
                    await asyncio.sleep(60)
                
                except Exception as e:
                    logger.error(f"Error in iteration: {e}", exc_info=True)
                    await asyncio.sleep(10)
        
        except KeyboardInterrupt:
            logger.info("\n\n[STOP] Stopping trading system...")
        
        finally:
            self.running = False
            
            # Final statistics
            logger.info("\n" + "="*70)
            logger.info("FINAL STATISTICS")
            logger.info("="*70)
            logger.info(f"Total Iterations: {self.iteration_count}")
            logger.info(f"Signals Generated: {self.signals_generated}")
            logger.info(f"Trades Executed: {self.trades_executed}")
            
            account_info = mt5.account_info()
            if account_info:
                logger.info(f"\nFinal Balance: ${account_info.balance:.2f}")
                logger.info(f"Final Equity: ${account_info.equity:.2f}")
                logger.info(f"Total Profit: ${account_info.profit:.2f}")
            
            mt5.shutdown()
            logger.info("\n[OK] System stopped cleanly")


async def main():
    """Main entry point"""
    trader = LiveMT5Trader()
    await trader.start()


if __name__ == "__main__":
    asyncio.run(main())
