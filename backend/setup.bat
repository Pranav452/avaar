@echo off
:: AI Video Dubbing System - Windows launcher
:: Double-click this file OR run it from cmd to set up and start the backend.

echo ==========================================================
echo  AI Video Dubbing System - Windows Setup
echo ==========================================================
echo.

:: Bypass the default "scripts are disabled" execution policy for this session only.
:: This does NOT permanently change your system policy.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup.ps1"

:: Keep the window open if the script exits so the user can read any errors.
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Setup failed with error code %ERRORLEVEL%.
    echo See the messages above for details.
    pause
)
