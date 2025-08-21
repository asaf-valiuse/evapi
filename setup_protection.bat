@echo off
REM API Protection Setup and Testing Script for Windows

echo 🔒 Setting up API Protection for EnerVibe API...

REM Install new requirements
echo 📦 Installing protection libraries...
pip install -r requirements.txt

REM Create blocked IPs file if it doesn't exist
if not exist "blocked_ips.json" (
    echo 📋 Creating blocked IPs configuration...
    echo {> blocked_ips.json
    echo   "ips": [],>> blocked_ips.json
    echo   "ranges": [>> blocked_ips.json
    echo     "127.0.0.1/32">> blocked_ips.json
    echo   ],>> blocked_ips.json
    echo   "updated": "%date% %time%">> blocked_ips.json
    echo }>> blocked_ips.json
)

REM Copy environment variables
if not exist ".env" (
    echo ⚙️ Creating environment configuration...
    copy .env.example .env
    echo Please edit .env file with your specific configuration
)

echo ✅ API Protection setup complete!
echo.
echo 📊 Monitoring:
echo - Check api_security.log for security events
echo - Use /usage endpoint to check quota usage
echo - Monitor blocked_ips.json for auto-blocked IPs
echo.
echo 🔧 Configuration files:
echo - .env - Environment variables
echo - blocked_ips.json - IP blocking configuration
echo - api_security.log - Security event log
echo.
echo 🧪 To test the API protection, start the server with:
echo python -m uvicorn app.main:app --reload --port 8000
echo.
echo Then test with PowerShell:
echo Invoke-RestMethod "http://localhost:8000/healthz"
