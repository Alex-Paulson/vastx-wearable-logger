@echo off
setlocal

title VASTX Wearable Logger

rem Always switch to the folder containing this batch file
cd /d "%~dp0"

echo ==========================================
echo Starting VASTX Wearable Logger
echo ==========================================
echo.
echo Application folder:
echo %CD%
echo.

if not exist "%~dp0python\python.exe" (
  echo ERROR: Embedded Python was not found.
  echo Expected:
  echo %~dp0python\python.exe
  echo.
  pause
  exit /b 1
)

if not exist "%~dp0app\app.py" (
  echo ERROR: The application file was not found.
  echo Expected:
  echo %~dp0app\app.py
  echo.
  pause
  exit /b 1
)

if not exist "%~dp0packages\streamlit" (
  echo ERROR: Streamlit was not found in the portable packages folder.
  echo Expected:
  echo %~dp0packages\streamlit
  echo.
  pause
  exit /b 1
)

if not exist "%~dp0logs" (
  mkdir "%~dp0logs"
)

echo Embedded Python and application files found.
echo Starting Streamlit...
echo.

start "" powershell -NoProfile -WindowStyle Hidden -Command ^
  "Start-Sleep -Seconds 5; Start-Process 'http://127.0.0.1:8501'"

"%~dp0python\python.exe" -m streamlit run "%~dp0app\app.py" ^
  --global.developmentMode false ^
  --server.address 127.0.0.1 ^
  --server.port 8501 ^
  --browser.gatherUsageStats false

echo.
echo The application has stopped.
pause

endlocal