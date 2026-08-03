@echo off
setlocal
title VASTX Wearable Logger

cd /d "%~dp0"

if /i "%~1"=="--wait-for-server" goto wait_for_server

echo ==========================================
echo Starting VASTX Wearable Logger
echo ==========================================
echo.

if not exist "logs" mkdir "logs"

"%~dp0python\python.exe" -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8501/_stcore/health', timeout=1).read()" >nul 2>&1
if not errorlevel 1 (
  start "" "http://127.0.0.1:8501"
  exit /b
)

start "" /b cmd /d /c call "%~f0" --wait-for-server

"%~dp0python\python.exe" -m streamlit run "%~dp0app\app.py" ^
  --global.developmentMode false ^
  --server.address 127.0.0.1 ^
  --server.port 8501 ^
  --server.headless true ^
  --browser.gatherUsageStats false

echo.
echo The application has stopped.
pause
exit /b

:wait_for_server
set "VASTX_URL=http://127.0.0.1:8501"
set /a VASTX_ATTEMPTS=0

:check_server
"%~dp0python\python.exe" -c "import urllib.request; urllib.request.urlopen('%VASTX_URL%/_stcore/health', timeout=1).read()" >nul 2>&1
if not errorlevel 1 goto open_browser

set /a VASTX_ATTEMPTS+=1
if %VASTX_ATTEMPTS% geq 120 exit /b 1
timeout /t 1 /nobreak >nul
goto check_server

:open_browser
start "" "%VASTX_URL%"
exit /b
