@echo off
echo Starting Aegis Trader Mobile App...
echo.
cd app
echo Installing dependencies (if needed)...
call npm install
echo.
echo Starting Expo...
echo.
echo Open Expo Go app on your phone and scan the QR code!
echo.
call npx expo start
pause