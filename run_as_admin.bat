@echo off
echo ===================================================
echo MyLocalAPI - Administrator Mode
echo ===================================================
echo.
echo MyLocalAPI now includes automatic elevation detection.
echo When you run main.py normally, it will automatically prompt
echo for administrator privileges if fan control is configured.
echo.
echo This script forces administrator mode without prompts.
echo.
echo Press any key to continue or Ctrl+C to cancel...
pause >nul

echo.
echo Starting MyLocalAPI as administrator (forced)...
echo.

REM Check if we're already running as admin
net session >nul 2>&1
if %errorlevel% == 0 (
    echo ✓ Running with administrator privileges
    echo.
    echo Starting MyLocalAPI server with --no-elevation flag...
    python main.py --no-elevation
) else (
    echo ✗ Administrator privileges required for fan control
    echo.
    echo Please right-click this batch file and select 
    echo "Run as administrator" to enable full functionality.
    echo.
    pause
)