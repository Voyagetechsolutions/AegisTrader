@echo off
cls
echo ========================================================================
echo DUAL-ENGINE TRADING SYSTEM
echo ========================================================================
echo.
echo This will start the COMPLETE trading system:
echo   - Dual-Engine Strategies (Core + Quick Scalp)
echo   - Market Regime Detection
echo   - Performance Tracking
echo   - Direct MT5 Connection
echo   - Real Trade Execution
echo.
echo Make sure MT5 is running and you're logged in!
echo.
echo Press any key to start or Ctrl+C to cancel...
pause > nul

echo.
echo Starting trading system...
echo.

python run_complete_system.py

echo.
echo System stopped.
pause
