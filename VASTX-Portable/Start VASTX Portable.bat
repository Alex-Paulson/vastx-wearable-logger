@echo off
title VASTX Wearable Logger

cd /d "%~dp0"

echo ==========================================
echo Starting VASTX Wearable Logger
echo ==========================================
echo.

if not exist "logs" mkdir "logs"

python\python.exe -m streamlit run app\app.py ^
  --browser.gatherUsageStats false

echo.
echo The application has stopped.
pause
